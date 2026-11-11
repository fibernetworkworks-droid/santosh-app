"""Lab pack `ug_modern_w8`: the B.Sc. MODERN / ATOMIC PHYSICS and MICROWAVE set-ups of `syllabus/physics/ug.json`
that were still unbuilt (DU LOCF 2019 C-IX Elements of Modern Physics Lab, C-XI Quantum Mechanics Lab, C-XIII
Electromagnetic Theory Lab; UGCF 2022). The physics is in `packs/ug_modern_w8.py` (and its JavaScript twin). Three
studio rigs draw the benches:

  rig `w8-electron-bench`   vacuum tubes and electron beams: a directly heated diode (work function), a mercury tube
                            (ionisation potential), Thomson's crossed fields, the magnetron, helical focusing and the
                            bar-magnet method (e/m)
  rig `w8-atomic-bench`     Millikan's oil drops, the normal Zeeman effect through a Fabry-Perot etalon, Planck's
                            constant from a hot tungsten filament
  rig `w8-microwave-bench`  the 3 cm microwave optics bench: reflection, prism refraction, polarisation, double slit

Every lab's `check` compares one reading the kernel finds on its own simulated apparatus with the textbook relation.
Values not taken from a table here are marked "from memory - verify" or "illustrative" in the lab that uses them.
"""
from __future__ import annotations

from ..catalog import B, SIM, board, inst, knob, lab

GROUP = "Physics · Modern Physics"
LEVEL = "B.Sc."
CH_AT = "Modern and atomic physics"
CH_MW = "Electromagnetic waves and microwaves"
EB = "w8-electron-bench"
AB = "w8-atomic-bench"
MB = "w8-microwave-bench"

DU = {"title": "University of Delhi B.Sc. (Hons.) Physics practical lists (LOCF 2019 C-IX Elements of Modern Physics "
               "Lab, C-XI Quantum Mechanics Lab, C-XIII Electromagnetic Theory Lab; UGCF 2022)"}
CODATA = {"title": "CODATA 2018 recommended values (NIST): e = 1.602176634e-19 C, m_e = 9.1093837015e-31 kg, "
                   "h = 6.62607015e-34 J s, k = 1.380649e-23 J/K, mu0 = 1.25663706212e-6 N/A^2, c = 299792458 m/s"}
IP = {"title": "Indu Prakash and Ramakrishna, A Text Book of Practical Physics, Vol. II (e/m by Thomson's method, "
               "magnetron, bar magnet; Millikan; work function)", "note": "cited from memory, not fetched - verify"}
MELI = {"title": "A. C. Melissinos and J. Napolitano, Experiments in Modern Physics, 2nd ed. (Millikan, Zeeman effect "
                 "with a Fabry-Perot etalon, thermionic emission)", "note": "cited from memory, not fetched - verify"}
ILLUS = {"title": "Illustrative laboratory values", "note": "Tube dimensions, coil constants, calibrations and meter "
         "ranges in this lab are chosen to be typical of a teaching laboratory; they are not properties of a named device."}
SAFE_HT = ("The high-tension supply can give a shock: make every connection with the supply switched off and its "
           "knob at zero, and never touch the tube's terminals while it is on.")


def _q(q, opts, ans, why):
    return {"q": q, "options": opts, "answer": ans, "why": why}


def _bodies(name: str, info: str) -> list[dict]:
    return [board(1.2, 0.6),
            B("main", "box", name=name, info=info, size=[0.36, 0.12, 0.2], pos=[-0.2, 0.06, -0.15], color="#4a4f57"),
            B("unit", "box", name="Supply and meters", info="The supplies and the meters of the experiment.",
              size=[0.34, 0.1, 0.2], pos=[0.25, 0.05, -0.1], color="#2b2f36")]


def _mk(id, rig, title, aim, kernel, params, knobs, insts, theory, steps, questions, sources, check, chapter,
        safety, name, info, tour):
    return lab(id=id, rig=rig, title=title, group=GROUP, level=LEVEL, topic=chapter, chapter=chapter, aim=aim,
               kernel=kernel, params=params, autorun=True, camera={"pos": [0.0, 0.75, 0.95], "look": [0, 0.05, -0.1]},
               floor=-0.03, bodies=_bodies(name, info), knobs=knobs, instruments=insts, steps=steps, theory=theory,
               safety=safety, tour=tour, questions=questions, sources=sources, check=check)


# ============================================================================================ electron bench
def diode_work_function() -> dict:
    return _mk(
        "w8-diode-work-function", EB, "Work function of a tungsten filament (vacuum diode)",
        "Heat the filament of a directly heated vacuum diode to several temperatures, read the saturation anode "
        "current at each, and find the work function of tungsten from the Richardson-Dushman plot.",
        "w8_diode", {"If": 2.0, "Va": 0.0},
        [knob("If", "Filament current", "If", 1.8, 2.6, 0.01, 2.0, "A"),
         knob("Va", "Anode voltage", "Va", 0, 150, 1, 0, "V"),
         knob("phi", "Filament metal (its work function is hidden)", "phi", 3.0, 6.0, 0.01, 4.55, "eV", hidden=True)],
        [inst("Ia", "readout", "Anode current", "Ia", k=1e6, unit="µA", lc=0.01, digits=2),
         inst("T", "readout", "Filament temperature (pyrometer)", "T", unit="K", lc=1, digits=0)],
        "A hot metal boils electrons off its surface. Only electrons with more than the work function phi of energy "
        "escape, so the saturation current follows the Richardson-Dushman law Is = A S T^2 exp(-e phi / k T). A plot "
        "of ln(Is / T^2) against 1/T is a straight line of slope -e phi / k. Below saturation the current is limited by "
        "the space charge of the electrons near the filament and rises as Va^1.5 (Child's law); the anode voltage must "
        "be high enough that every emitted electron is collected. Here the filament temperature is read on an optical "
        "pyrometer, whose calibration against the heating current is illustrative. The Schottky lowering of the "
        "barrier by the anode field is small and is not modelled.",
        ["Connect the filament supply through its ammeter, and the anode supply through a microammeter.",
         "Set the filament current to 2.4 A and raise the anode voltage in steps: the current rises and then saturates.",
         "Hold the anode voltage at 150 V, well into saturation.",
         "For six filament currents from 2.0 to 2.5 A read the filament temperature and the saturation current.",
         "Plot ln(Is / T^2) against 1/T: the slope is -e phi / k."],
        [_q("The anode current stops rising with the anode voltage because", ["Every emitted electron is already "
            "collected", "The filament cools", "The tube is gassy"], 0, "That is the saturation current: emission, not the field, limits it."),
         _q("The slope of ln(Is/T^2) against 1/T is", ["-e phi / k", "+k / e phi", "-phi"], 0, "From Is = A S T^2 exp(-e phi / kT).")],
        [DU, MELI, CODATA, {"title": "CRC Handbook of Chemistry and Physics, 'Electron work function of the elements': "
                            "tungsten, polycrystalline, about 4.55 eV", "note": "from memory - verify"}, ILLUS, SIM],
        {"params": {"If": 2.2, "Va": 150.0}, "reading": "phi", "textbook": "w8_phi"}, CH_AT, SAFE_HT,
        "Directly heated vacuum diode", "A tungsten filament on the axis of a cylindrical nickel anode in an evacuated glass bulb.",
        [{"say": "The diode on its valve base on the left, the supplies and meters on the right, the pyrometer aimed at the filament."}])


def mercury_ionisation() -> dict:
    return _mk(
        "w8-mercury-ionisation", EB, "Ionisation potential of mercury",
        "Raise the accelerating voltage of electrons in a mercury-vapour tube, record the positive-ion current on a "
        "negative collector, and find the ionisation potential by extrapolating the straight part of the curve.",
        "w8_ion", {"V": 0.0},
        [knob("V", "Accelerating voltage", "V", 0, 20, 0.1, 0, "V"),
         knob("Ui", "Gas in the tube (its ionisation potential is hidden)", "Ui", 5, 16, 0.0001, 10.4375, "V", hidden=True)],
        [inst("I", "readout", "Ion collector current", "I", k=1e9, unit="nA", lc=0.01, digits=2)],
        "Electrons from a hot cathode are accelerated through V to a grid; beyond it a collector held a few volts "
        "negative repels every electron and gathers only positive ions (Lenard's method). No ions form until e V "
        "exceeds the ionisation energy of the mercury atom. Just above that threshold the chance of ionisation, and so "
        "the ion current, grows in proportion to the excess energy, so the curve is a straight line that extrapolates "
        "back to the ionisation potential. The spread of the electrons' thermal energies rounds the knee, which is why "
        "the straight part is used and not the first sign of current. The contact potential between the electrodes "
        "shifts a real curve by about a volt; in this tube it is taken as zero and the lab says so.",
        ["Warm the tube until the mercury vapour is at its working pressure.",
         "Keep the collector a few volts negative of the grid so that only ions reach it.",
         "Raise the accelerating voltage from 6 V to 19 V in steps of 0.5 V and read the ion current each time.",
         "Plot the ion current against the voltage.",
         "Extend the straight part of the curve down to zero current: that voltage is the ionisation potential."],
        [_q("Why is the collector kept negative?", ["So that only positive ions reach it", "To heat the cathode", "To stop ionisation"], 0,
            "Electrons are repelled; the current measured is the ion current."),
         _q("Why extrapolate the straight part instead of reading the first current?", ["The thermal energy spread rounds the knee",
            "The meter is slow", "The vapour pressure changes"], 0, "The onset is blurred by about kT; the straight line is not.")],
        [DU, IP, CODATA, {"title": "NIST Atomic Spectra Database, ionisation energies: Hg I 10.4375 eV",
                          "note": "from memory - verify"}, ILLUS, SIM],
        {"params": {"V": 15.0}, "reading": "Vi", "textbook": "w8_ui"}, CH_AT,
        SAFE_HT + " The tube contains mercury: if it breaks, do not touch the drops and call the teacher.",
        "Mercury-vapour tube with an ion collector", "Cathode, grid and a separate negative ion collector in mercury vapour.",
        [{"say": "The mercury tube on the left, the control unit with the electrometer on the right."}])


def em_thomson() -> dict:
    return _mk(
        "w8-em-thomson", EB, "e/m of the electron by Thomson's method (crossed fields)",
        "Deflect the beam of a cathode-ray tube with an electric field, bring the spot back to the centre with a "
        "magnetic field from Helmholtz coils, and find e/m from the two fields and the accelerating voltage.",
        "w8_thomson", {"Va": 1500.0, "Vp": 0.0, "Ic": 0.0},
        [knob("Vp", "Deflecting plate voltage", "Vp", 0, 200, 1, 0, "V"),
         knob("Ic", "Coil current", "Ic", 0, 1, 0.001, 0, "A"),
         knob("em", "Electron e/m (hidden)", "em", 100, 250, 0.01, 175.88, "x 1e9 C/kg", k=1e9, hidden=True)],
        [inst("y", "readout", "Spot deflection", "y", k=1000, unit="mm", lc=0.5, digits=1)],
        "Electrons accelerated through Va leave the gun with speed v, where m v^2 / 2 = e Va. Between plates a "
        "distance d apart at a voltage Vp the electric force e E (E = Vp/d) pushes the beam sideways; a magnetic field B "
        "across the same region pushes it the other way with the force e v B. When the spot is back at the centre the "
        "forces balance, v = E / B, and so e/m = v^2 / (2 Va) = E^2 / (2 Va B^2). The field of the Helmholtz coils is "
        "B = k I with the coil constant k from their turns and radius. In this tube the magnetic field is taken to act "
        "over the plate region only (an idealisation of a real tube's fringing fields).",
        ["Switch on the tube at 1500 V and centre the spot on the screen.",
         "Apply a voltage to the deflecting plates and read the deflection of the spot.",
         "Pass a current through the Helmholtz coils and adjust it until the spot is back at the centre; approach the "
         "centre from both sides and take the mean current.",
         "Repeat for three plate voltages.",
         "Work out e/m = E^2 / (2 Va B^2) for each and take the mean."],
        [_q("At the balance the speed of the electrons is", ["E / B", "B / E", "E B"], 0, "e E = e v B."),
         _q("Doubling the plate voltage needs a coil current that is", ["Twice as large", "Four times", "The same"], 0, "B = E / v and v is fixed by Va.")],
        [DU, IP, CODATA, {"title": "Coil constant 4.2 mT/A and tube dimensions (plates 20 mm long, 4 mm apart, screen 150 mm "
                          "beyond)", "note": "illustrative"}, SIM],
        {"params": {"Vp": 150.0}, "reading": "em", "textbook": "w8_em"}, CH_AT, SAFE_HT,
        "Cathode-ray tube with Helmholtz coils", "An electron gun, deflecting plates and a screen with a millimetre graticule, between a pair of Helmholtz coils.",
        [{"say": "The cathode-ray tube between its Helmholtz coils, with the high-tension and coil supplies beside it."}])


def em_magnetron() -> dict:
    return _mk(
        "w8-em-magnetron", EB, "e/m of the electron by the magnetron method",
        "Increase the axial magnetic field of a solenoid around a cylindrical diode until the anode current is cut "
        "off, and find e/m from the critical field.",
        "w8_mag", {"Va": 6.0, "Is": 0.0},
        [knob("Va", "Anode voltage", "Va", 2, 12, 0.5, 6, "V"),
         knob("Is", "Solenoid current", "Is", 0, 1, 0.01, 0, "A"),
         knob("em", "Electron e/m (hidden)", "em", 100, 250, 0.01, 175.88, "x 1e9 C/kg", k=1e9, hidden=True)],
        [inst("Ia", "readout", "Anode current", "Ia", k=1000, unit="mA", lc=0.001, digits=3)],
        "In a cylindrical diode the electrons go radially from the filament to the anode. An axial magnetic field bends "
        "their paths; at the critical field Bc the paths just graze the anode and curl back, and the anode current "
        "falls to nearly zero. For an anode of radius a and a filament of radius b, e/m = 8 Va / (Bc^2 a^2 (1 - "
        "b^2/a^2)^2). Electrons leave the filament with a spread of speeds, so the cut-off is not sharp: the critical "
        "field is taken where the current has fallen to half its zero-field value. The solenoid is long, so B = mu0 n I "
        "inside it.",
        ["Mount the diode on the axis of the solenoid and switch the filament on.",
         "Set the anode voltage to 6 V and read the anode current with no current in the solenoid.",
         "Raise the solenoid current in steps of 0.02 A and read the anode current each time.",
         "Plot the anode current against the field and find the field where the current is half its first value.",
         "Repeat at 9 V; work out e/m for each run and take the mean."],
        [_q("At the critical field the electrons", ["Just graze the anode and return", "Stop at the filament", "Go faster"], 0,
            "Their circular paths have a diameter equal to the gap."),
         _q("If the anode voltage is doubled the critical field", ["Rises by root 2", "Doubles", "Halves"], 0, "Bc is proportional to the square root of Va.")],
        [DU, IP, CODATA, {"title": "Anode radius 4 mm, filament radius 0.1 mm, solenoid 10,000 turns per metre",
                          "note": "illustrative"}, SIM],
        {"params": {"Va": 6.0}, "reading": "em", "textbook": "w8_em"}, CH_AT, SAFE_HT,
        "Cylindrical diode in a solenoid", "A diode valve on the axis of a long solenoid; the filament and anode are coaxial.",
        [{"say": "The diode stands inside the solenoid on the left; its supplies and meters are on the right."}])


def em_focusing() -> dict:
    return _mk(
        "w8-em-focusing", EB, "e/m of the electron by magnetic focusing",
        "Draw a short line on the screen of a cathode-ray tube inside a long solenoid, raise the solenoid current "
        "until the line shrinks to a point, and find e/m from the focusing field.",
        "w8_focus", {"meth": 0.0, "Va": 800.0, "Ic": 0.0},
        [knob("Va", "Accelerating voltage", "Va", 400, 1200, 10, 800, "V"),
         knob("Ic", "Solenoid current", "Ic", 0, 1, 0.001, 0, "A"),
         knob("em", "Electron e/m (hidden)", "em", 100, 250, 0.01, 175.88, "x 1e9 C/kg", k=1e9, hidden=True)],
        [inst("ell", "readout", "Length of the line on the screen", "ell_mm", unit="mm", lc=0.5, digits=1)],
        "A small alternating voltage on the X plates gives each electron a small sideways speed, so the beam draws a "
        "line on the screen. In an axial field B every electron moves on a helix and makes one turn in the time "
        "T = 2 pi m / (e B), whatever its sideways speed. When this time equals the time L / v to reach the screen, all "
        "the electrons come back to the axis together and the line shrinks to a point (the first focus). With "
        "v = sqrt(2 e Va / m) this gives e/m = 8 pi^2 Va / (B^2 L^2). Between the focuses the line turns and shrinks: "
        "its length follows sin(theta/2) / (theta/2), theta being the angle turned on the way.",
        ["Place the tube on the axis of the solenoid and switch on at 800 V.",
         "Put a small AC voltage on the X plates so that a short line appears on the screen.",
         "Raise the solenoid current slowly: the line turns and shrinks.",
         "Note the current at which the line becomes a point (the first focus).",
         "Repeat at 600 V and 1000 V and work out e/m = 8 pi^2 Va / (B^2 L^2) for each."],
        [_q("At the first focus the electrons have made", ["One full turn of the helix", "Half a turn", "No turn"], 0,
            "They all return to the axis after one turn."),
         _q("The time for one turn depends on", ["B only (and e/m)", "The sideways speed", "The plate voltage"], 0,
            "T = 2 pi m / (e B).")],
        [DU, IP, CODATA, {"title": "Solenoid 10,000 turns per metre, plates-to-screen distance 130 mm",
                          "note": "illustrative"}, SIM],
        {"params": {"meth": 0.0}, "reading": "em", "textbook": "w8_em"}, CH_AT, SAFE_HT,
        "Cathode-ray tube in a long solenoid", "A small cathode-ray tube on the axis of a long solenoid.",
        [{"say": "The cathode-ray tube lies inside the solenoid; the supplies are on the right."}])


# ============================================================================================ atomic bench
def millikan() -> dict:
    return _mk(
        "w8-millikan", AB, "Millikan's oil-drop experiment: the charge of the electron",
        "Time charged oil drops falling freely between two plates, then hold each one still with the field "
        "(balancing) or time its rise in the field (rise and fall), and find the smallest charge they all share.",
        "w8_oil", {"meth": 0.0, "drop": 0.0, "V": 0.0},
        [knob("V", "Plate voltage", "V", 0, 600, 0.5, 0, "V"),
         knob("drop", "Drop in view", "drop", 0, 4, 1, 0),
         knob("e", "Elementary charge (hidden)", "e", 1.0, 2.2, 0.000001, 1.602177, "x 1e-19 C", k=1e-19, hidden=True)],
        [inst("vel", "readout", "Drop velocity (up)", "vel", k=1e6, unit="µm/s", lc=0.1, digits=1)],
        "A tiny oil drop falling through air soon reaches the steady speed vg at which Stokes' drag 6 pi eta a vg "
        "balances its weight (4/3) pi a^3 rho g, so its radius is a = sqrt(9 eta vg / (2 rho g)). With a voltage V on "
        "plates a distance d apart a charged drop feels q V / d upward. Balancing method: adjust V until the drop "
        "hangs still; then q = (4/3) pi a^3 rho g d / V. Rise-and-fall method: at a fixed V time the rise as well; then "
        "q = 6 pi eta a (vg + vr) d / V. The charges of many drops are all whole multiples of one charge e. A real drop "
        "this small needs the Cunningham slip correction to Stokes' law (a few per cent); it is not modelled here.",
        ["Spray oil into the chamber and pick a drop that falls slowly in the camera view.",
         "With the plates shorted, time the drop over 1.0 mm of the graticule.",
         "Switch the field on and adjust the voltage until the drop hangs still; read the balancing voltage.",
         "Repeat for all five drops and work out the charge on each.",
         "Divide every charge by the smallest one, round to whole numbers, and find e as the mean charge per unit."],
        [_q("Why do the drops reach a steady speed?", ["The drag grows with speed until it equals the weight", "The plates attract them", "Oil is light"], 0,
            "Stokes' drag is proportional to speed."),
         _q("All the charges are found to be", ["Whole multiples of one charge", "Equal", "Random"], 0, "That is the quantisation of charge.")],
        [DU, MELI, CODATA, {"title": "Air viscosity 1.81e-5 Pa s near 20 C", "note": "from memory - verify (CRC Handbook)"},
         {"title": "Oil density 886 kg/m3, plate gap 5.0 mm, timing distance 1.0 mm", "note": "illustrative"}, SIM],
        {"params": {"drop": 0.0}, "reading": "e19", "textbook": "w8_e19"}, CH_AT,
        "The plates are at up to 600 V: switch the supply off before opening the chamber. The lamp gets hot.",
        "Millikan chamber with a camera", "Two circular brass plates 5 mm apart in a perspex housing, lit from the side and viewed by a camera with a graticule.",
        [{"say": "The Millikan chamber with its atomiser and lamp, the camera monitor, and the plate supply."}])


def zeeman() -> dict:
    return _mk(
        "w8-zeeman", AB, "Normal Zeeman effect: e/m from the cadmium red line",
        "Put a cadmium lamp between the poles of an electromagnet, watch each Fabry-Perot ring split into two, and "
        "find e/m from the splitting at several fields.",
        "w8_zeeman", {"B": 0.0},
        [knob("B", "Magnetic field", "B", 0, 1, 0.001, 0, "T"),
         knob("em", "Electron e/m (hidden)", "em", 100, 250, 0.01, 175.88, "x 1e9 C/kg", k=1e9, hidden=True)],
        [inst("D2p", "readout", "Diameter, second ring, outer component", "D2p", k=1000, unit="mm", lc=0.01, digits=2)],
        "In a magnetic field B the upper level of the cadmium 643.8 nm line (a singlet, so the normal Zeeman effect) "
        "splits into three, and the line splits into a triplet. Seen across the field with a polaroid that removes the "
        "middle component, each line is replaced by two, shifted in wavenumber by d_sigma = e B / (4 pi m c). The "
        "shifts are far too small for a prism, so a Fabry-Perot etalon of spacing t is used: its rings of diameter D "
        "satisfy D^2 changes by a fixed step from one order to the next, and d_sigma = (Da^2 - Db^2) / (4 t (D(p+1)^2 "
        "- D(p)^2)) for the two components a and b of one order. Then e/m = 4 pi c d_sigma / B.",
        ["Switch the cadmium lamp on between the pole pieces and focus the etalon rings in the telescope.",
         "Put the polaroid in so that only the two shifted components remain.",
         "Set the magnet current so that the gaussmeter reads about 0.5 T.",
         "Measure the diameters of both components of the second and third rings with the micrometer eyepiece.",
         "Repeat at 0.65 T and 0.8 T and work out e/m at each field."],
        [_q("The normal Zeeman effect is seen in the cadmium red line because", ["It is a singlet line (spin zero)", "Cadmium is magnetic", "It is red"], 0,
            "With no spin the splitting is the classical one, e B / (4 pi m)."),
         _q("Doubling the field makes the splitting", ["Twice as large", "Four times", "The same"], 0, "d_sigma is proportional to B.")],
        [DU, MELI, CODATA, {"title": "NIST Atomic Spectra Database: Cd I 643.847 nm (1D2 - 1P1)", "note": "from memory - verify"},
         {"title": "Etalon spacing 3.0 mm, telescope focal length 300 mm", "note": "illustrative"}, SIM],
        {"params": {"B": 0.6}, "reading": "em", "textbook": "w8_em"}, CH_AT,
        "The pole pieces pull hard on steel tools: keep them away. The lamp gets hot; let it cool before touching it.",
        "Electromagnet, cadmium lamp and Fabry-Perot etalon", "A cadmium lamp between the pole pieces of an electromagnet, a lens, a Fabry-Perot etalon, a polaroid and a telescope.",
        [{"say": "The electromagnet with the cadmium lamp, the etalon and the telescope; the gaussmeter probe sits in the gap."}])


def planck_blackbody() -> dict:
    return _mk(
        "w8-planck-blackbody", AB, "Planck's constant from black-body radiation",
        "Heat a tungsten filament to several temperatures, measure the light it gives through a narrow red filter "
        "with a photodetector, and find Planck's constant from how steeply the signal rises with temperature.",
        "w8_bb", {"T": 2000.0},
        [knob("T", "Filament temperature", "T", 1700, 2700, 1, 2000, "K"),
         knob("h", "Planck's constant (hidden)", "h", 5.0, 8.0, 0.00001, 6.62607, "x 1e-34 J s", k=1e-34, hidden=True)],
        [inst("I", "readout", "Photodetector current", "I", k=1e9, unit="nA", lc=0.01, digits=2)],
        "A hot body radiates at each wavelength lam with Planck's law; through a narrow filter the photodetector "
        "current is proportional to 1 / (exp(h c / (lam k T)) - 1). At 650 nm and 2000 K the exponential is about "
        "e^11, so the 1 can be dropped (Wien's approximation) and ln I = constant - h c / (lam k T). A plot of ln I "
        "against 1/T is a straight line of slope -h c / (lam k), which gives h. The filament temperature is read on a "
        "disappearing-filament pyrometer. A tungsten filament is not a perfect black body; its emissivity changes "
        "only slowly with temperature, and that change is not modelled.",
        ["Place the 650 nm filter and the photodetector in line with the lamp, and shield them from room light.",
         "Set the lamp supply so that the pyrometer reads about 1800 K, and read the detector current.",
         "Raise the temperature in steps of 100 K up to 2600 K, reading the current each time.",
         "Plot ln I against 1/T.",
         "h = - slope x lam k / c."],
        [_q("Why does the signal rise so steeply with temperature?", ["The exponential in Planck's law", "The filament grows",
            "The filter warms up"], 0, "At 650 nm the light is on the steep short-wavelength side of the Planck curve."),
         _q("The slope of ln I against 1/T is", ["-h c / (lam k)", "-lam k / (h c)", "+h c / k"], 0, "From Wien's approximation.")],
        [DU, CODATA, {"title": "Filter centre 650 nm, detector scale factor", "note": "illustrative"}, SIM],
        {"params": {"T": 2000.0}, "reading": "h34", "textbook": "w8_h34"}, CH_AT,
        "The lamp housing gets very hot: handle it by the base only. Never look straight at the hot filament except "
        "through the pyrometer.",
        "Tungsten lamp, filter and photodetector", "A tungsten-filament lamp in a vented housing, an interference filter and a photodetector.",
        [{"say": "The lamp housing, the filter and detector tube, the pyrometer and the nanoammeter."}])


# ============================================================================================ microwave bench
_MW_SRC = {"title": "Gunn oscillator at about 10.5 GHz (wavelength about 2.85 cm) with horn antennas and a crystal "
                    "detector, as in a teaching microwave optics kit", "note": "illustrative"}


def microwave_reflect() -> dict:
    return _mk(
        "w8-microwave-reflect", MB, "Reflection and refraction of microwaves",
        "Check that 3 cm microwaves reflect from a metal plate with the angle of reflection equal to the angle of "
        "incidence, then pass them through a wax prism and find its refractive index from the deviation.",
        "w8_mw", {"part": 0.0, "th": 0.0, "inc": 45.0},
        [knob("th", "Receiver arm angle", "th", 0, 90, 0.5, 0, "deg"),
         knob("inc", "Angle of incidence on the plate", "inc", 20, 70, 5, 45, "deg"),
         knob("n", "Prism material (its refractive index is hidden)", "n", 1.1, 2.0, 0.001, 1.5, "", hidden=True)],
        [inst("I", "readout", "Detector reading", "I", k=100, unit="%", lc=0.1, digits=1)],
        "Microwaves are light of 3 cm wavelength and obey the same laws. A flat metal sheet reflects them, and the "
        "receiver finds the strongest signal when its angle of reflection equals the angle of incidence. A prism of "
        "paraffin wax (apex A) bends them: with the beam entering the first face normally, the angle inside at the "
        "second face is A, and the beam leaves at an angle e with sin e = n sin A. The deviation is d = e - A, so "
        "n = sin(A + d) / sin A. The receiver is swung until the detector reading is largest.",
        ["Set the transmitter and the receiver horn on the arms of the goniometer and switch the oscillator on.",
         "Turn the metal plate to an angle of incidence of 30 degrees and swing the receiver arm to the strongest signal.",
         "Repeat at 45 and 60 degrees: the angle of reflection equals the angle of incidence.",
         "Replace the plate by the wax prism with its first face square to the beam.",
         "Swing the receiver to the strongest signal, read the deviation, and work out n = sin(A + d) / sin A."],
        [_q("A metal sheet reflects microwaves because", ["It is a good conductor", "It is shiny", "It is flat"], 0,
            "The free electrons re-radiate the wave."),
         _q("The deviation of the prism grows if the refractive index", ["Increases", "Decreases", "Stays the same"], 0, "sin e = n sin A.")],
        [DU, _MW_SRC, {"title": "Paraffin wax: relative permittivity about 2.25 at microwave frequencies (n about 1.5)",
                       "note": "from memory - verify"}, SIM],
        {"params": {"part": 1.0}, "reading": "n", "textbook": "w8_n"}, CH_MW,
        "The microwave power is a few milliwatts, but never look into the horn at close range. Keep the oscillator "
        "supply below its rated voltage.",
        "Microwave optics goniometer", "A Gunn transmitter with a horn on a fixed arm and a receiving horn with a crystal detector on a swinging arm over a protractor.",
        [{"say": "The transmitter on the fixed arm, the receiver on the swinging arm, the reflector on the turntable."}])


def microwave_interference() -> dict:
    return _mk(
        "w8-microwave-interference", MB, "Polarisation and double-slit interference of microwaves",
        "Rotate the receiving horn to show that the microwaves are polarised, then pass them through a double slit, "
        "find the minima of the interference pattern and work out the wavelength.",
        "w8_mw", {"part": 2.0, "th": 0.0, "phi": 0.0, "ds": 0.09},
        [knob("th", "Receiver arm angle", "th", 0, 70, 0.5, 0, "deg"),
         knob("phi", "Receiver horn rotation", "phi", 0, 90, 15, 0, "deg"),
         knob("lam", "Oscillator (its wavelength is hidden)", "lam", 1.5, 4.0, 0.0001, 2.848, "cm", k=0.01, hidden=True)],
        [inst("I", "readout", "Detector reading", "I", k=100, unit="%", lc=0.1, digits=1)],
        "The Gunn oscillator radiates a plane-polarised wave: its electric field lies along the short side of the horn. "
        "The crystal detector responds to the square of the field along its own direction, so when the receiving horn "
        "is turned by phi the reading falls as cos^2 phi (Malus' law) and vanishes at 90 degrees. A double slit of "
        "centre spacing d turns the beam into two coherent sources; the waves cancel where the path difference "
        "d sin(theta) is a half-whole number of wavelengths, so the minima lie at sin(theta) = (m + 1/2) lam / d. The "
        "slope of sin(theta) against (m + 1/2) is lam / d.",
        ["Face the receiver straight at the transmitter and read the detector.",
         "Turn the receiving horn about the beam in steps of 15 degrees up to 90 and read the detector each time.",
         "Put the double slit (centre spacing 9.0 cm) in front of the transmitter, the receiver horn back upright.",
         "Swing the receiver arm out from 0 to 60 degrees and find each minimum of the reading.",
         "Plot sin(theta) of the minima against m + 1/2: the slope times d is the wavelength."],
        [_q("The reading is zero when the receiving horn is turned by", ["90 degrees", "45 degrees", "180 degrees"], 0,
            "cos^2 90 = 0: the field has no component along the detector."),
         _q("The first minimum is where the path difference is", ["Half a wavelength", "One wavelength", "Zero"], 0, "The two waves arrive in opposite phase.")],
        [DU, _MW_SRC, {"title": "Double slit: slits 1.5 cm wide, centres 9.0 cm apart", "note": "illustrative"}, SIM],
        {"params": {"part": 3.0}, "reading": "lam", "textbook": "w8_lam"}, CH_MW,
        "The microwave power is a few milliwatts, but never look into the horn at close range. Keep the oscillator "
        "supply below its rated voltage.",
        "Microwave optics goniometer", "A Gunn transmitter with a horn on a fixed arm and a receiving horn with a crystal detector on a swinging arm over a protractor.",
        [{"say": "The transmitter, the double slit on the turntable and the receiver on the swinging arm."}])


BUILDERS = (diode_work_function, mercury_ionisation, em_thomson, em_magnetron, em_focusing, millikan, zeeman,
            planck_blackbody, microwave_reflect, microwave_interference)
