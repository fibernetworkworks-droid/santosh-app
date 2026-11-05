"""Prayogshala lab pack: M.Sc. OPTICS, INTERFEROMETRY AND SPECTROSCOPY - fifteen M.Sc. practicals on two real benches.

    msc-interferometer   a Michelson interferometer with a micrometer-driven mirror (wavelength of a laser by fringe
                         counting, the sodium D doublet by the beats in fringe visibility, the index of a plate by the
                         white-light fringes) and a Mach-Zehnder / Jamin interferometer with an evacuable gas cell
                         (refractive index of a gas by counting fringes while the pressure rises).
    msc-spectrograph     a scanning monochromator with a detector and a sample compartment: I2 vibronic bands, the
                         rotation-vibration band of HCl and CO, Raman lines, fluorescence, a Tauc plot, a cooled
                         semiconductor, a luminescence decay on an oscilloscope, a thermoluminescence glow curve and
                         Beer's law for a dye.

Every reading comes from this area's own kernels (`packs/msc_optics.py`); every lab carries a check, the kernel's
reading against the textbook formula, within 1 %. Where the real instrument is one no student may open (an FTIR's
interferometer, a Raman spectrometer's laser) the lab text says so and the student works the controls a student works.
"""
from __future__ import annotations

from ..catalog import B, col, inst, knob, lab

GRP = "Physics · Optics and Spectroscopy"
LVL = "M.Sc."
SIM = {"title": "Hoola Prayogshala kernel",
       "note": "readings come from the simulation code; checked against the textbook formula in Hoola's tests"}
MSC = {"title": "Practical syllabi of IIT Kanpur PHY 461/462, University of Delhi M.Sc. Physics PH-DSE5118 / PH-DSE5164 / "
                "PH-DSE5218 and SGGU M.Sc. MSC1P109"}
HECUR = {"title": "He-Ne laser line 632.8 nm (NIST Atomic Spectra Database: Ne I 632.8165 nm in air)"}
NA = {"title": "NIST Atomic Spectra Database: sodium D1 589.592 nm and D2 588.995 nm"}
EDLEN = {"title": "Edlen, Metrologia 2 (1966) 71: refractive index of standard air at 632.8 nm, n - 1 = 2.7651e-4 "
                  "(15 C, 101.325 kPa)"}
HERZ = {"title": "NIST Chemistry WebBook, constants of diatomic molecules (Huber and Herzberg)"}


def _bench() -> list[dict]:
    return [B("bench", "box", name="Optical table", size=[1.0, 0.02, 0.6], pos=[0, -0.02, 0], color="wood", cut=False),
            B("unit", "box", name="Instrument", size=[0.3, 0.12, 0.2], pos=[0, 0.06, 0], color="#2b2f36")]


def _q(q, options, answer, why):
    return {"q": q, "options": options, "answer": answer, "why": why}


def _spec(id, title, kernel, params, aim, theory, steps, questions, sources, check, calc, columns, truth,
          result_k=1.0, result_unit="", digits=3, safety="", topic="Spectroscopy", camera=None):
    return lab(
        id=id, rig="msc-spectrograph", title=title, group=GRP, level=LVL, topic=topic, chapter=topic,
        aim=aim, kernel=kernel, params=params, autorun=True,
        camera=camera or {"pos": [0.0, 0.5, 0.9], "look": [0.0, 0.05, 0.0]}, floor=-0.2,
        bodies=_bench(),
        table={"columns": columns, "calc": calc, "rows_min": 3, **({"truth": truth} if truth else {}),
               "result_k": result_k, "result_unit": result_unit, "result_digits": digits,
               "hint": "Scan, put the cursor on each line or point, and record it."},
        steps=steps, theory=theory, safety=safety, questions=questions, sources=sources, check=check)


# ====================================================================================== interferometers
def michelson_wavelength() -> dict:
    return lab(
        id="michelson-wavelength", rig="msc-interferometer",
        title="Michelson interferometer: wavelength of a laser by fringe counting", group=GRP, level=LVL,
        topic="Interferometry", chapter="Interferometry",
        aim="Turn the micrometer that moves one mirror of a Michelson interferometer, count the circular fringes "
            "that pass the centre, and find the wavelength of the laser from lambda = 2 d / N.",
        kernel="msc_michelson", params={"src": 0.0, "lam": 6.328e-7}, autorun=True,
        camera={"pos": [0.0, 0.5, 0.9], "look": [0.0, 0.05, 0.0]}, floor=-0.2, bodies=_bench(),
        knobs=[knob("x", "Mirror micrometer reading", "x", 0.5, 3.0, 0.001, 1.0, "mm", 1e-3)],
        instruments=[inst("cen", "readout", "Light at the centre of the fringes", "inten", digits=2)],
        table={"columns": [col("d", "Mirror travel d", "manual", "mm", 1e-3, digits=4),
                           col("N", "Fringes counted N", "manual", "", digits=0)],
               "calc": "msc_c_mich_lam", "rows_min": 3, "truth": "p.lam", "result_k": 1e9, "result_unit": "nm",
               "result_digits": 1, "hint": "Zero the counter, turn the micrometer by a measured distance, count."},
        steps=["Switch the laser on and adjust the mirror screws until the circular fringes are centred on the screen.",
               "Turn the micrometer until a bright fringe sits at the centre and note the reading.",
               "Turn it by a measured distance d (0.1 to 0.3 mm) while counting the fringes that collapse into the centre.",
               "Write d and N in the table. Repeat for three different distances.",
               "Work out lambda = 2 d / N for each and take the mean."],
        theory="Moving one mirror by d changes the path of its beam by 2d, because the light goes to the mirror and "
               "back. Every time the path changes by one wavelength a bright fringe replaces the one before it at the "
               "centre, so N fringes pass when 2d = N lambda. At 0.2 mm a visible laser gives over 600 fringes, so a "
               "count that is wrong by one is wrong by less than 0.2 %. Keep turning the micrometer the same way: "
               "the screw has backlash, and turning back loses a few fringes.",
        safety="The beam of a He-Ne laser can damage an eye. Never look into the beam or at a mirror that reflects "
               "it; keep the beam below eye level on the table.",
        questions=[_q("The mirror moves 0.1 mm and 316 fringes pass. The wavelength is about",
                      ["633 nm", "316 nm", "1266 nm"], 0, "lambda = 2 d / N = 0.2 mm / 316 = 633 nm."),
                   _q("Why is the micrometer always turned the same way during a count?",
                      ["The screw has backlash", "The laser would switch off", "Fringes only form one way"], 0,
                      "Reversing takes up the slack first, so some of the turn moves nothing.")],
        sources=[MSC, HECUR, SIM],
        check={"params": {"lam": 6.328e-7}, "reading": "lam", "textbook": "msc_mich_lam"},
    )


def michelson_sodium_doublet() -> dict:
    return lab(
        id="michelson-sodium-doublet", rig="msc-interferometer",
        title="Michelson interferometer: separation of the sodium D lines", group=GRP, level=LVL,
        topic="Interferometry", chapter="Interferometry",
        aim="With a sodium lamp, find the mirror positions where the fringes almost vanish, and work out the "
            "separation of the two D lines from the distance between successive disappearances.",
        kernel="msc_michelson", params={"src": 1.0, "lam": 5.88995e-7, "lam2": 5.89592e-7}, autorun=True,
        camera={"pos": [0.0, 0.5, 0.9], "look": [0.0, 0.05, 0.0]}, floor=-0.2, bodies=_bench(),
        knobs=[knob("x", "Mirror micrometer reading", "x", 0.5, 3.0, 0.001, 1.0, "mm", 1e-3)],
        instruments=[inst("vis", "readout", "Fringe contrast", "vis", digits=2)],
        table={"columns": [col("k", "Disappearance number", "manual", "", digits=0),
                           col("x", "Micrometer reading", "manual", "mm", 1e-3, digits=4)],
               "calc": "msc_c_mich_dline", "rows_min": 3, "result_k": 1e9,
               "result_unit": "nm", "result_digits": 3,
               "hint": "Find at least three places where the fringes fade out."},
        steps=["Replace the laser by the sodium lamp and a ground-glass diffuser; find the circular fringes.",
               "Turn the micrometer slowly in one direction and watch the contrast rise and fall.",
               "Stop at each place where the fringes fade almost to nothing and write down the reading.",
               "Find at least three such places in a row.",
               "The mean distance between successive disappearances is Dx; then the separation is lambda_mean squared "
               "divided by 2 Dx."],
        theory="Sodium light is two lines, D2 at 588.995 nm and D1 at 589.592 nm. Each line makes its own fringes. At "
               "zero path difference the two sets coincide; as the path difference grows they slip against each other "
               "and where a bright fringe of one falls on a dark fringe of the other the fringes fade. This happens "
               "each time the path difference changes by lambda1 lambda2 / (lambda2 - lambda1), that is every "
               "lambda_mean squared / (2 Dlambda) of mirror travel (about 0.29 mm for sodium). Measuring that "
               "distance gives the separation, which is far smaller than the spectrometer could easily show.",
        safety="Sodium lamps run hot and the choke is at mains voltage; let the lamp cool before moving it.",
        questions=[_q("Successive disappearances of the sodium fringes are 0.29 mm apart. The line separation is about",
                      ["0.6 nm", "6 nm", "0.06 nm"], 0, "Dlambda = (589.3 nm)^2 / (2 x 0.29 mm) = 0.60 nm."),
                   _q("A closer pair of lines would make the disappearances come",
                      ["further apart", "closer together", "at the same places"], 0,
                      "Dx is proportional to 1 / Dlambda.")],
        sources=[MSC, NA, SIM],
        check={"params": {}, "reading": "dlam", "textbook": "msc_mich_dline"},
    )


def michelson_plate_index() -> dict:
    return lab(
        id="michelson-plate-index", rig="msc-interferometer",
        title="Michelson interferometer: refractive index of a thin plate", group=GRP,
        level=LVL, topic="Interferometry", chapter="Interferometry",
        aim="Find the mirror position where the white-light fringes are sharpest, put a plate of known thickness in "
            "one arm, refind them, and get the refractive index of the plate from the shift.",
        kernel="msc_michelson", params={"src": 2.0, "np": 1.5168, "tp": 1.0e-3}, autorun=True,
        camera={"pos": [0.0, 0.5, 0.9], "look": [0.0, 0.05, 0.0]}, floor=-0.2, bodies=_bench(),
        knobs=[knob("x", "Mirror micrometer reading", "x", 0.5, 3.0, 0.001, 1.0, "mm", 1e-3)],
        instruments=[inst("vis", "readout", "Fringe contrast", "vis", digits=2)],
        table={"columns": [col("k", "Plate (0 = out, 1 = in)", "manual", "", digits=0),
                           col("x", "Micrometer reading of the sharpest fringes", "manual", "mm", 1e-3, digits=4)],
               "calc": "msc_c_mich_n", "rows_min": 2, "truth": "p.np", "result_digits": 4,
               "hint": "Find the sharpest white-light fringes without and with the plate."},
        steps=["Use the white lamp. Turn the micrometer slowly until coloured fringes appear and are sharpest.",
               "Read the micrometer: this is the position with equal optical paths.",
               "Put the plate in the fixed arm, square to the beam. The fringes disappear.",
               "Turn the micrometer until the coloured fringes come back, sharpest again, and read it.",
               "The shift s = (n - 1) t, so n = 1 + s / t. The thickness t is printed on the plate holder."],
        theory="White light has a coherence length of only about a micrometre, so fringes are seen only when the two "
               "optical paths are equal to within that. A plate of thickness t and index n in one arm adds (n - 1) t "
               "to the path of the light that crosses it, twice if the light passes it going and coming back, so the "
               "movable mirror must move by (n - 1) t to restore equal paths. The shift of the sharpest fringes then "
               "gives n. Said plainly: white-light fringes follow the group delay, so in a real plate the method "
               "returns the group index, a little higher than the ordinary index. This simulated glass has no "
               "dispersion, so the two are the same.",
        safety="Hold the plate by its edges: a fingerprint on the face adds path and scatters light.",
        questions=[_q("The sharpest fringes move 0.52 mm when a 1.00 mm plate is put in. Its index is",
                      ["1.52", "0.52", "2.04"], 0, "n = 1 + 0.52 / 1.00 = 1.52."),
                   _q("Why white light and not a laser for this measurement?",
                      ["Only white light has one position of sharpest fringes", "Lasers cannot pass through glass",
                       "White light is brighter"], 0, "A laser gives fringes at every path difference, so there is "
                                                      "no single position to mark.")],
        sources=[MSC, {"title": "SCHOTT N-BK7 datasheet: nd = 1.5168; fused silica: Malitson, J. Opt. Soc. Am. 55 "
                                "(1965) 1205, n = 1.4585 at 589 nm"}, SIM],
        check={"params": {}, "reading": "n", "textbook": "msc_mich_n"},
    )


def _gas(id, title, aim, steps, theory, L, arch, extra_q):
    return lab(
        id=id, rig="msc-interferometer", title=title, group=GRP, level=LVL, topic="Interferometry",
        chapter="Interferometry", aim=aim, kernel="msc_gascell",
        params={"lam": 6.328e-7, "L": L, "dn1": 2.7651e-4, "arms": 1.0, "arch": arch}, autorun=True,
        camera={"pos": [0.0, 0.5, 0.9], "look": [0.0, 0.05, 0.0]}, floor=-0.2, bodies=_bench(),
        knobs=[knob("P", "Gas pressure in the cell", "P", 0.0, 1.0, 0.01, 0.0, "atm")],
        instruments=[inst("cen", "readout", "Light at the centre of the fringes", "inten", digits=2)],
        table={"columns": [col("P", "Pressure raised to", "manual", "atm", digits=2),
                           col("N", "Fringes counted", "manual", "", digits=1)],
               "calc": "msc_c_gas_dn1", "rows_min": 3, "truth": "p.dn1", "result_digits": 7,
               "hint": "Start from vacuum and count the fringes while the gas is let in."},
        steps=steps, theory=theory,
        safety="Use a cell rated for vacuum, behind a guard. The laser beam must stay below eye level.",
        questions=[_q("The cell is 0.30 m long. How many fringes pass for n - 1 = 2.77e-4 at 632.8 nm?",
                      ["131", "262", "66"], 0, "N = (n - 1) L / lambda = 2.77e-4 x 0.30 / 632.8e-9 = 131."),
                   extra_q],
        sources=[MSC, EDLEN, HECUR, SIM],
        check={"params": {}, "reading": "dn1", "textbook": "msc_gas_dn1"},
    )


def jamin_air_index() -> dict:
    return _gas(
        "jamin-air-index", "Jamin's interferometer: refractive index of air",
        "Evacuate a tube in one path of a Jamin interferometer, let air in, count the fringes that cross the "
        "field, and find the refractive index of air from n - 1 = N lambda / L.",
        ["Switch the laser on and set the two Jamin plates until the fringes are straight and sharp.",
         "Pump the tube down and close the valve. The fringe pattern settles.",
         "Open the valve slowly and count the fringes that cross a mark in the field while air returns to 1 atm.",
         "Count the whole fringes and estimate the last fraction from where the pattern stops.",
         "Repeat three times. Work out n - 1 = N lambda / L."],
        "The Jamin interferometer uses two thick parallel glass plates, so the two beams run side by side and a "
        "tube can be put in one of them. Filling the tube raises the refractive index from 1 to n, and the "
        "optical path through a length L by (n - 1) L. One fringe passes each time that grows by one wavelength, "
        "so N = (n - 1) L / lambda, and n - 1 = N lambda / L. Air is nearly proportional to its pressure, so the "
        "fringes pass at an even rate as the air returns. The value of n - 1 for air in the lab depends on the "
        "temperature; the figure used here is for standard air at 15 C.",
        0.30, 1.0, _q("If the room is warmer than standard, the fringe count for 1 atm will",
                      ["fall a little", "rise a little", "stay the same"], 0,
                      "Warmer air is less dense, so n - 1 at 1 atm is smaller."))


def mach_zehnder() -> dict:
    return _gas(
        "mach-zehnder", "Mach-Zehnder interferometer: refractive index of air against pressure",
        "Count the fringes in a Mach-Zehnder interferometer while air is let into an evacuated cell in one arm, "
        "at several pressures, and find n - 1 from the slope of fringes against pressure.",
        ["Switch the laser on and adjust the second beam-splitter until the fringes are broad and steady.",
         "Pump the cell down to vacuum and close the valve.",
         "Let air in until the pressure gauge reads 0.2 atm, counting fringes; record P and N.",
         "Carry on to 0.4, 0.6, 0.8 and 1.0 atm, counting from vacuum each time.",
         "Plot N against P: a straight line through the origin whose slope gives n - 1 = slope x lambda / L."],
        "A Mach-Zehnder interferometer splits the laser beam, sends the halves round two sides of a rectangle and "
        "recombines them. A gas cell of length L in one arm delays that beam by (n - 1) L, so N = (n - 1) L / "
        "lambda fringes pass as the cell fills. Because n - 1 is nearly proportional to the pressure for a gas "
        "(the Gladstone-Dale relation) the graph of N against P is a straight line, which shows the law as well "
        "as giving the number. Each beam goes through the cell once, so the cell must be twice as long as in a "
        "Michelson to give the same count.",
        0.10, 0.0, _q("The graph of fringes against pressure is a straight line through the origin because",
                      ["n - 1 is proportional to the gas density", "the laser is steady", "the cell is rigid"], 0,
                      "At fixed temperature the density, and so n - 1, is proportional to the pressure."))


# ====================================================================================== spectra
def iodine_absorption() -> dict:
    return _spec(
        "iodine-absorption", "Iodine vapour: vibronic absorption bands and anharmonicity", "msc_iodine", {},
        "Record the visible absorption bands of iodine vapour, number them from the red end, and find the "
        "anharmonicity constant of the excited state from how the band spacing falls.",
        "Iodine vapour absorbs in the green and yellow, taking the molecule from the X ground state to the B excited "
        "state. Because the upper state is a Morse-like well, its vibrational levels get closer together: "
        "G(v) = we(v + 1/2) - wexe(v + 1/2)^2, and the spacing between successive bands falls by 2 wexe each step. "
        "A Birge-Sponer plot of the spacing against v is a straight line whose slope is -2 wexe; where the line "
        "reaches zero spacing the molecule dissociates. Only the v''=0 progression is modelled here. A real "
        "spectrum also has hot bands from v''=1 and fine rotational structure, and the Birge-Sponer extrapolation "
        "overestimates the dissociation energy because the real curve bends.",
        ["Warm the cell a little so there is vapour in the beam and put it in the sample compartment.",
         "Scan from 500 to 620 nm and watch the bands appear, closer together towards the blue.",
         "Number the bands from the red end, put the cursor on each band head and record its wavelength.",
         "Convert each to wavenumber and find the spacing between neighbours.",
         "Plot the spacing against the band number: the slope is -2 wexe."],
        [_q("The band spacing gets smaller towards the blue because",
            ["the upper-state levels get closer as the well is anharmonic", "the lamp is weaker there",
             "the cell absorbs more"], 0, "An anharmonic well has levels that converge towards dissociation."),
         _q("The slope of the spacing-against-v line is", ["-2 wexe", "we", "+wexe"], 0,
            "G(v+1) - G(v) = we - 2 wexe (v + 1).")],
        [HERZ, {"title": "I2 B 3Pi(0u+) state: Te = 15769.01, we = 125.69, wexe = 0.764 cm-1; X state: we = 214.50, "
                         "wexe = 0.607 cm-1"}, SIM],
        {"params": {}, "reading": "wx1", "textbook": "msc_iod_wx"}, "msc_c_iod_wx",
        [col("k", "Band number", "manual", "", digits=0), col("x", "Wavelength of band head", "manual", "nm", digits=2)],
        "p.wx1", result_unit="cm-1", digits=3, safety="Iodine vapour is toxic: keep the cell sealed and warm it only gently.",
        topic="Molecular spectroscopy")


_HCL = {}


def hcl_rovibrational() -> dict:
    return _spec(
        "hcl-rovibrational", "Rotation-vibration spectrum of HCl: rotational constant and bond length", "msc_rovib",
        _HCL,
        "Record the fundamental infrared band of HCl gas, read the R and P branch lines, and find the rotational "
        "constant B and the bond length by combination differences.",
        "In the fundamental band of a diatomic gas the molecule changes its vibration and its rotation together. "
        "Lines with J going up by one form the R branch and lines with J going down the P branch, with a gap at the "
        "band origin where J cannot stay the same. The difference R(J-1) - P(J+1) = 4 B0 (J + 1/2) depends only on the "
        "lower vibrational state, so a plot of it against J + 1/2 is a straight line of slope 4 B0 whatever the "
        "vibrational stretching does to the upper state. B0 = h / (8 pi^2 c mu r^2) then gives r. Each line is a "
        "doublet because chlorine is 75.8 % 35Cl and 24.2 % 37Cl; the heavier molecule has the smaller B and lines "
        "shifted a little to lower wavenumber. The FTIR is a closed instrument: the student loads the gas cell and "
        "runs the scan, but does not open or adjust the interferometer inside.",
        ["Load the HCl gas cell (KBr windows) in the beam and run the background scan with the cell empty.",
         "Scan the sample from 2600 to 3120 cm-1.",
         "Number the stronger line of each doublet outwards from the gap: R(0) R(1) ... on the high side, P(1) P(2) ... on the low side.",
         "Record the wavenumbers; pair R(J-1) with P(J+1) for J = 1 to 5.",
         "Plot R(J-1) - P(J+1) against J + 1/2: the slope is 4 B0."],
        [_q("Why are the HCl lines doublets?", ["There are two chlorine isotopes", "The molecule has two bonds",
                                                "The detector splits them"], 0,
            "35Cl and 37Cl give different reduced masses, hence different B."),
         _q("The line spacing in the spectrum is about", ["2 B", "B", "4 B"], 0,
            "Neighbouring lines are separated by about 2B.")],
        [HERZ, {"title": "H35Cl: we = 2990.946, wexe = 52.8186, Be = 10.59341, alpha_e = 0.30718 cm-1 (NIST Chemistry "
                         "WebBook); isotope masses from AME2020; 35Cl : 37Cl = 75.76 : 24.24"}, SIM],
        {"params": {}, "reading": "B0", "textbook": "msc_rv_b0"}, "msc_c_rot_b",
        [col("k", "Line (R = +J+1, P = -J)", "manual", "", digits=0),
         col("x", "Wavenumber", "manual", "cm-1", digits=2)], None, result_unit="cm-1", digits=3,
        safety="HCl gas is corrosive: the cell is sealed and filled in a fume cupboard by the technician.",
        topic="Molecular spectroscopy")


_CO = {"we": 2169.81358, "wx": 13.28831, "Be": 1.93128, "ae": 0.0175, "m1": 12.0, "m2": 15.99491462, "m3": 0.0,
       "w2": 0.0, "T": 300.0, "fwhm": 0.5, "Jmax": 40.0, "lo": 2000.0, "hi": 2250.0}


def ir_vibrational() -> dict:
    return _spec(
        "ir-vibrational", "Infrared fundamental band of carbon monoxide: force constant", "msc_rovib", _CO,
        "Record the fundamental vibration band of CO gas, find its centre, and work out the force constant of the "
        "C-O bond from nu = (1 / 2 pi c) sqrt(k / mu).",
        "A diatomic molecule vibrating about its equilibrium separation behaves almost as a spring: "
        "nu = (1 / 2 pi c) sqrt(k / mu), with mu the reduced mass. The infrared absorption is the jump from v = 0 to 1; "
        "the band centre sits in the gap between the R(0) and P(1) lines, because a line at the centre itself is "
        "forbidden. So k = 4 pi^2 c^2 nu^2 mu. Said plainly: the centre of the 0 -> 1 band is we - 2 wexe, not the "
        "harmonic we, so the k found from it is about 1 % low for CO (the bond is slightly anharmonic). Only 12C16O is "
        "modelled; 13CO is 1 % of the gas and its lines are not drawn. The FTIR's interferometer is not opened by the "
        "student.",
        ["Fill the cell with CO (technician only) and run the background scan.",
         "Scan 2000 to 2250 cm-1: two branches with a gap in the middle.",
         "Record the two lines either side of the gap: R(0) on the high side and P(1) on the low side.",
         "The band centre is their midpoint.",
         "Work out k = 4 pi^2 c^2 nu^2 mu with mu = 6.856 amu."],
        [_q("The band centre lies in the gap between R(0) and P(1) because", ["Delta J = 0 is forbidden",
                                                                              "CO is not polar", "the gas is cold"], 0,
            "A vibrational jump needs the rotation to change by one unit."),
         _q("If the wavenumber doubled, k would", ["quadruple", "double", "stay the same"], 0,
            "k is proportional to nu squared.")],
        [HERZ, {"title": "12C16O: we = 2169.81358, wexe = 13.28831, Be = 1.93128, alpha_e = 0.0175 cm-1 (NIST Chemistry "
                         "WebBook)"}, SIM],
        {"params": {}, "reading": "kf", "textbook": "msc_rv_kf"}, "msc_c_force",
        [col("k", "Line (R(0) = 1, P(1) = -1)", "manual", "", digits=0),
         col("x", "Wavenumber", "manual", "cm-1", digits=2)], None, result_unit="N/m", digits=1,
        safety="Carbon monoxide is poisonous: the cell is sealed and filled by the technician in a fume cupboard.",
        topic="Molecular spectroscopy")


def laser_raman() -> dict:
    return _spec(
        "laser-raman", "Laser Raman spectrum of a liquid: Raman shift and temperature", "msc_raman", {},
        "Excite a liquid with a green laser, record the Stokes lines, find the Raman shift of the strongest line, "
        "and estimate the temperature from the ratio of the anti-Stokes to Stokes line.",
        "In Raman scattering a small part of the light loses (Stokes) or gains (anti-Stokes) one quantum of a molecular "
        "vibration, so the scattered light is shifted from the laser line by the vibrational wavenumber, whatever "
        "the laser. The shift is the same on both sides, but the anti-Stokes line needs a molecule that is already "
        "vibrating, so it is weaker by a Boltzmann factor: I_AS / I_S = ((nu0 + s) / (nu0 - s))^4 exp(-hc s / kT). The "
        "ratio gives the temperature of the liquid. The relative heights of the weaker lines are illustrative; the "
        "shifts are the literature values. The detector is taken as equally sensitive at all wavelengths, which a real "
        "one is not. The laser and spectrometer are closed instruments: the student works the sample holder and the "
        "scan, never the laser.",
        ["Put the cuvette of liquid in the holder; the laser stays off until the shutter interlock is closed.",
         "Scan the shift from the anti-Stokes side across the laser line to the Stokes side.",
         "Put the cursor on the strongest Stokes line and record its shift and height.",
         "Do the same for the anti-Stokes line of the same vibration.",
         "The temperature follows from the ratio of the two heights."],
        [_q("A Raman shift is measured from", ["the laser line", "zero wavelength", "the strongest line"], 0,
            "Shift = wavenumber of laser minus wavenumber of scattered light."),
         _q("The anti-Stokes line is weaker because", ["few molecules are already vibrating",
                                                       "the laser is absorbed", "the filter blocks it"], 0,
            "It comes only from molecules in an excited vibrational level.")],
        [{"title": "Carbon tetrachloride Raman lines at 218, 314 and 459 cm-1; benzene 606, 992 and 1178 cm-1 "
                   "(Socrates, Infrared and Raman Characteristic Group Frequencies; ASTM E1840)"}, SIM],
        {"params": {}, "reading": "s1", "textbook": "msc_ram_s1"}, "msc_c_raman_s",
        [col("k", "Line (Stokes strongest = 1, anti-Stokes = -1)", "manual", "", digits=0),
         col("x", "Raman shift", "manual", "cm-1", digits=1)], "p.s1", result_unit="cm-1", digits=1,
        safety="The 532 nm laser is class 3B: the sample compartment is interlocked and the beam is never exposed.",
        topic="Molecular spectroscopy")


def fluorescence_spectra() -> dict:
    return _spec(
        "fluorescence-spectra", "Absorption and fluorescence spectra: the Stokes shift", "msc_fluor", {},
        "Record the absorption band and the fluorescence band of a fluorophore and find the Stokes shift between "
        "their peaks in wavenumber.",
        "A molecule absorbs a photon, loses some energy as heat in its surroundings, then emits at a longer wavelength. "
        "The gap between the absorption peak and the emission peak, measured in wavenumber (1 / wavelength) so that "
        "it is proportional to energy, is the Stokes shift. It is a property of the molecule in its solvent, not of "
        "the instrument. The peak positions used here are typical literature values and move with solvent, pH and "
        "temperature.",
        ["Put the cell with the solution in the spectrofluorimeter's holder.",
         "Choose Absorption and scan; put the cursor on the peak and record it.",
         "Choose Emission and scan with the excitation fixed near the absorption peak; record the emission peak.",
         "Convert both to wavenumber: 10^7 / wavelength in nm.",
         "The difference is the Stokes shift."],
        [_q("Emission is at a longer wavelength than absorption because", ["some energy is lost as heat first",
                                                                           "the lamp is red", "light slows in solution"],
            0, "The excited molecule relaxes before it emits."),
         _q("Why quote the Stokes shift in wavenumber?", ["It is proportional to energy", "It is a bigger number",
                                                         "The monochromator reads it"], 0,
            "Equal wavenumber differences are equal energy differences; nanometres are not.")],
        [{"title": "Quinine sulfate in dilute acid: absorption near 347 nm, emission near 450 nm (NIST SRM 936a)"},
         SIM],
        {"params": {}, "reading": "stokes", "textbook": "msc_fl_stokes"}, "msc_c_stokes",
        [col("k", "Band (1 = absorption, 2 = emission)", "manual", "", digits=0),
         col("x", "Peak wavelength", "manual", "nm", digits=1)], None, result_unit="cm-1", digits=0,
        safety="Quinine solutions are for the instrument only, not for drinking; wear gloves and use the UV-safe cell.",
        topic="Luminescence")


def solids_absorption() -> dict:
    return _spec(
        "solids-absorption-reflection", "Absorption edge of a thin film: optical gap by a Tauc plot", "msc_tauc", {},
        "Measure the transmission of a thin semiconductor film across its absorption edge and find the optical "
        "band gap from a Tauc plot.",
        "Below the band gap a semiconductor film is transparent; above it, it absorbs. The absorption coefficient "
        "follows alpha = -ln(T) / t. For a direct gap, (alpha h nu)^2 is proportional to (h nu - Eg), so a graph of "
        "(alpha h nu)^2 against h nu is a straight line in the region above the edge, and where it cuts the energy axis "
        "is the gap. The lab ignores reflection and band-tail absorption; a real measurement corrects for reflection "
        "and fits only the straight part. Only the direct-gap form is modelled here; an indirect-gap film such as "
        "silicon needs (alpha h nu)^(1/2).",
        ["Put a clean bare glass slide in the reference beam and a coated slide in the sample beam.",
         "Scan from the visible towards the ultraviolet through the edge and note the transmittance.",
         "Record the wavelength and transmittance at about eight points on the steep part of the edge.",
         "For each, alpha = -ln(T) / t, then (alpha h nu)^2 with h nu = 1239.8 / wavelength in eV.",
         "Plot against h nu and extrapolate the straight line to zero: that is Eg."],
        [_q("For a direct-gap semiconductor the straight line is a plot of", ["(alpha h nu)^2 against h nu",
                                                                              "alpha against wavelength",
                                                                              "T against h nu"], 0,
            "Direct transitions give alpha h nu proportional to (h nu - Eg)^(1/2)."),
         _q("A film twice as thick will", ["have the same Eg", "have double Eg", "have no gap"], 0,
            "The gap is a property of the material, not of its thickness.")],
        [{"title": "Room-temperature direct gaps: CdS 2.42 eV, ZnO 3.37 eV, CdTe about 1.5 eV (Sze and Ng, Physics of "
                   "Semiconductor Devices; Kittel). Tauc, Grigorovici and Vancu, Phys. Status Solidi 15 (1966) 627"},
         SIM],
        {"params": {}, "reading": "Eg", "textbook": "msc_tauc_eg"}, "msc_c_tauc",
        [col("x", "Wavelength", "manual", "nm", digits=1), col("y", "Transmittance T", "manual", "", digits=3)],
        "p.Eg", result_unit="eV", digits=3, topic="Solid-state spectroscopy")


def low_t_optical() -> dict:
    return _spec(
        "low-t-optical-spectra", "Optical spectra at low temperature: the gap of GaAs at 300 K and 77 K", "msc_varshni",
        {}, "Record the band-edge luminescence of a GaAs wafer at room temperature and cooled with liquid nitrogen, "
            "and find how much the gap widens.",
        "The band gap of a semiconductor grows as it is cooled because the lattice contracts and the electrons couple less to "
        "the vibrations. Varshni's law Eg(T) = Eg(0) - alpha T^2 / (T + beta) describes it. The band-edge "
        "luminescence peak is taken here as the gap (at room temperature it lies a little above it, by about kT / 2). "
        "At 77 K the peak is also narrower, because fewer electrons sit high in the band, so it is easier to place the "
        "cursor on it.",
        ["Mount the wafer on the cold finger of the cryostat and scan at room temperature.",
         "Put the cursor on the luminescence peak and record it.",
         "Pour liquid nitrogen into the cryostat (the technician does this) and wait for the temperature to settle at 77 K.",
         "Scan again and record the new peak.",
         "Convert both to energy: 1239.8 / wavelength in eV; the difference is the shift."],
        [_q("On cooling the GaAs luminescence peak moves to", ["shorter wavelength", "longer wavelength", "stays"], 0,
            "The gap rises, so photon energy rises and wavelength falls."),
         _q("The peak is narrower at 77 K because", ["the thermal spread kT is smaller", "the laser is stronger",
                                                    "the wafer is thinner"], 0, "Carriers occupy a narrower range of "
                                                                                "energy.")],
        [{"title": "Varshni, Physica 34 (1967) 149; GaAs parameters Eg(0) = 1.519 eV, alpha = 0.5405 meV/K, beta = 204 K "
                   "(Vurgaftman, Meyer and Ram-Mohan, J. Appl. Phys. 89 (2001) 5815)"}, SIM],
        {"params": {}, "reading": "dE", "textbook": "msc_vs_dE"}, "msc_c_varshni",
        [col("c", "Temperature", "manual", "K", digits=0), col("x", "Peak wavelength", "manual", "nm", digits=1)],
        None, result_unit="eV", digits=4, safety="Liquid nitrogen causes cold burns and displaces air: the technician "
        "handles it, with goggles and gloves.", topic="Solid-state spectroscopy")


def pl_lifetime() -> dict:
    return _spec(
        "pl-lifetime", "Photoluminescence lifetime of ruby", "msc_decay", {"tau": 3.0e-3},
        "Excite a ruby crystal with a short flash, record the decay of its red luminescence on an oscilloscope, "
        "and find the lifetime from a plot of ln V against time.",
        "After a short flash the number of excited Cr3+ ions falls exponentially, V = V0 exp(-t / tau), so ln V against t "
        "is a straight line of slope -1 / tau. Ruby's R-line lifetime is about 3 ms at room temperature, long "
        "because the transition is spin- and parity-forbidden. In a real crystal the decay is exponential only if "
        "the crystal is not too heavily doped; here it is a single exponential.",
        ["Put the crystal in the holder in front of the photodiode and set the flash lamp to single shots.",
         "Fire the flash and freeze the trace on the oscilloscope.",
         "Put the cursor at about eight times along the decay and record time and voltage.",
         "Plot ln V against t.",
         "The lifetime is minus the reciprocal of the slope."],
        [_q("The time for the signal to fall to 1/e of its value is", ["tau", "tau / 2", "2 tau"], 0,
            "That is the definition of the lifetime."),
         _q("The straight line is a plot of", ["ln V against t", "V against t", "V against 1 / t"], 0,
            "ln V = ln V0 - t / tau.")],
        [{"title": "Maiman, Nature 187 (1960) 493: ruby fluorescence lifetime about 3 ms; Koechner, Solid-State Laser "
                   "Engineering (Nd:YAG 230 us)"}, SIM],
        {"params": {}, "reading": "tau", "textbook": "msc_dec_tau"}, "msc_c_decay",
        [col("x", "Time", "manual", "ms", digits=2), col("y", "Signal V", "manual", "V", digits=3)], "p.tau",
        result_k=1e3, result_unit="ms", digits=3, safety="Flash lamps run at high voltage: the lamp housing stays closed.",
        topic="Luminescence")


def thermoluminescence() -> dict:
    return _spec(
        "thermoluminescence", "Thermoluminescence: trap depth by the heating-rate method", "msc_glow", {},
        "Heat an irradiated crystal at several steady rates, record the temperature of the glow peak each time, and "
        "find the trap depth from how the peak moves.",
        "Radiation leaves electrons trapped at depth E below the conduction band. Heating frees them at a rate "
        "s exp(-E / kT), and they glow as they recombine. For first-order kinetics the peak temperature obeys "
        "beta E / (k Tm^2) = s exp(-E / k Tm), so ln(Tm^2 / beta) = E / (k Tm) + constant. A graph of ln(Tm^2 / beta) "
        "against 1 / Tm for several heating rates beta is a straight line of slope E / k (Hoogenstraaten's method). "
        "The trap here is a MODEL trap (E = 1.0 eV, s = 1e12 per second), not a measured value for a named crystal. "
        "A real glow curve often has several overlapping peaks and second-order kinetics, and one needs to separate them first.",
        ["Mount the irradiated chip on the heater plate under the photomultiplier.",
         "Choose a heating rate and start the heater; the glow curve is drawn as the plate warms.",
         "Put the cursor on the top of the peak and record the peak temperature.",
         "Repeat for four different heating rates with a freshly irradiated chip each time.",
         "Plot ln(Tm^2 / beta) against 1 / Tm: the slope times k is the trap depth."],
        [_q("When the heating rate is raised the glow peak moves to", ["a higher temperature", "a lower temperature",
                                                                      "does not move"], 0,
            "The traps have less time to empty at each temperature, so the peak is pushed up."),
         _q("A deeper trap gives a glow peak at", ["a higher temperature", "a lower temperature", "the same"], 0,
            "More thermal energy is needed to free the electrons.")],
        [{"title": "Randall and Wilkins, Proc. R. Soc. A 184 (1945) 366; Hoogenstraaten, Philips Res. Rep. 13 (1958) 515; "
                   "McKeever, Thermoluminescence of Solids (1985)"}, SIM],
        {"params": {}, "reading": "E", "textbook": "msc_tl_E"}, "msc_c_glow",
        [col("c", "Heating rate", "manual", "K/s", digits=1), col("x", "Peak temperature", "manual", "K", digits=1)],
        "p.E", result_unit="eV", digits=3, safety="The heater plate reaches 500 K: do not touch it while it is on.",
        topic="Luminescence")


def uv_vis_electronic() -> dict:
    return _spec(
        "uv-vis-electronic", "Electronic absorption spectrum of a dye: Beer-Lambert law and molar absorptivity",
        "msc_beer", {}, "Record the absorption band of rhodamine 6G in ethanol at several concentrations and find the "
                        "molar absorptivity from the slope of absorbance against concentration.",
        "Absorbance A = log10(I0 / I) = epsilon c l (Beer-Lambert law), with c the concentration in mol per litre, l "
        "the path in cm and epsilon the molar absorptivity at that wavelength. At the peak of the band epsilon is "
        "largest, so the measurement is most sensitive there. A graph of A against c at the peak is a straight line "
        "through the origin, slope epsilon l. Beer's law fails at high concentrations (dye molecules stack), so "
        "keep A below about 1. The band is drawn as one Gaussian; the real band has a vibronic shoulder on the blue side.",
        ["Make a stock solution and dilute to six known concentrations; use the 10 mm quartz cell.",
         "Run the baseline with ethanol in both beams.",
         "For each concentration, scan 420 to 640 nm and put the cursor on the peak.",
         "Record the concentration and the absorbance at the peak.",
         "Plot A against c: the slope divided by l is epsilon."],
        [_q("If the concentration doubles, the absorbance at the peak", ["doubles", "halves", "stays"], 0,
            "A is proportional to c."),
         _q("Why measure at the peak and not at the side of the band?", ["It is most sensitive and least affected by "
                                                                          "small wavelength errors", "It is the "
                                                                          "darkest colour", "The lamp is brightest"],
            0, "The curve is flat at the peak, so a small wavelength error changes A very little.")],
        [{"title": "Rhodamine 6G in ethanol: epsilon = 116 000 L/(mol cm) at 529.8 nm (Prahl, omlc.org; PhotochemCAD)"},
         SIM],
        {"params": {}, "reading": "eps", "textbook": "msc_beer_eps"}, "msc_c_beer",
        [col("c", "Concentration", "manual", "mol/L", digits=7), col("y", "Absorbance at the peak", "manual", "",
                                                                      digits=3)],
        "p.eps", result_unit="L/(mol cm)", digits=0, safety="Rhodamine is a toxic dye: wear gloves and dispose of the "
        "solutions as chemical waste.", topic="Molecular spectroscopy")


BUILDERS = (
    michelson_wavelength, michelson_sodium_doublet, michelson_plate_index, jamin_air_index, mach_zehnder,
    iodine_absorption, hcl_rovibrational, ir_vibrational, laser_raman, fluorescence_spectra, solids_absorption,
    low_t_optical, pl_lifetime, thermoluminescence, uv_vis_electronic,
)
