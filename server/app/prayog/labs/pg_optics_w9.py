"""Prayogshala lab pack: the M.Sc. optics, lasers and spectroscopy bench (wave 9).

ONE studio rig, `app/static/prayog/exp/po9-optics-bench.js`, serves every set-up here: an optical breadboard with a
source, the element under test, a reading instrument and one or two controls. Each lab is "set the control, read the
instrument, record": the settings a careful student records are the kernel's own `plan`, the table is reduced by the
kernel's own `calc`, and the check runs that whole path against the textbook value (within 1 %).

Set-ups of `syllabus/physics/pg.json`:
    po9-fp-hyperfine      Fabry-Perot etalon: satellite splitting, etalon spacing, finesse (Hg 546.1 nm, Na D)
    po9-zeeman            Zeeman effect: e/m, Bohr magneton, g of the upper level (Fabry-Perot / Lummer-Gehrcke; Hg / Cd)
    po9-ellipse           elliptically polarised light (quarter-wave plate + analyser, Babinet; mica plate / QWP)
    po9-biref             birefringence of a plate (Babinet, rotating analyser; mica / quartz)
    po9-photoelastic      photoelastic fringes (disc, beam; plane and circular polariscopes)
    po9-kerr              Kerr effect in nitrobenzene
    po9-pockels           Pockels effect in KDP and lithium niobate
    po9-eo-modulation     electro-optic modulation of a laser beam (sine signal, audio band)
    po9-faraday           Faraday effect (sodium lamp, tungsten lamp + filters; flint, dense flint)
    po9-magneto-optic     magneto-optic modulation with a flint rod in a solenoid
    po9-laser-2d          laser diffraction by 2-D objects (mesh, cross grating, circular, square apertures)
    po9-laser-slits       laser interference and diffraction (single slit, double slit, grating)
    po9-cdev              constant deviation spectrometer (Hg, Na, Ne)
    po9-rowland           concave grating in a Rowland mounting (Hg lamp, iron arc)
    po9-alo-bands         vibrational analysis of the AlO band spectrum (SIMULATED spectrogram)
    po9-band-liquid       band spectrum of a liquid (KMnO4, didymium)
    po9-uranyl            fluorescence of uranyl nitrate hexahydrate
    po9-solar             Fraunhofer lines in sunlight (SIMULATED DATA)
    po9-film-thickness    film thickness at a step (multiple-beam fringes, FECO)
    po9-film-strain       residual stress of a film by Newton's rings and Stoney's equation
    po9-photometry        luminous intensity, inverse square law and irradiance of lamps
    po9-acousto-optic     acousto-optics (Raman-Nath in water, Bragg in a crystal)
    po9-aerosol           aerosol spectrometer: number concentration and median size (SIMULATED DATA)
    po9-ellipsometry      optical constants of thin films by ellipsometry (null, rotating analyser; SiO2 on Si, metal)
Physics: the `pg_optics_w9` kernel pack (never catalog.py / kernels.py). English only.
"""
from __future__ import annotations

import math

from ..catalog import B, col, inst, knob, lab

DEG = math.pi / 180
RIG = "po9-optics-bench"
GRP = "Physics · Optics and Spectroscopy"
LVL = "M.Sc. / PG"
MEM = "from memory - verify"

SIM = {"title": "Hoola Prayogshala kernel",
       "note": "readings come from the simulation code; checked against the textbook formula in Hoola's tests"}
DU = {"title": "University of Delhi M.Sc. Physics 2025-26 (A.C. 24.07.2025 Appendix-09): PH-DSE5164 / 5118 / 5218 labs"}
IITK = {"title": "IIT Kanpur Department of Physics, MSc Lab PHY 461/462 list of experiments"}
CUK = {"title": "Central University of Kerala M.Sc. Physics (2020), PHY5304 Experimental Physics III"}
SGGU = {"title": "Shri Govind Guru University M.Sc. Physics (2023), MSC1P209 laboratory"}
NIST = {"title": "NIST Atomic Spectra Database, lines in air: Hg I 404.6565, 435.8335, 546.0750, 576.9610, 579.0670 nm; "
                 "Na I 588.9950, 589.5924 nm", "note": MEM}
NIST2 = {"title": "NIST Atomic Spectra Database, lines in air: Cd I 643.8470 nm; Ne I 585.2488, 640.2248 nm; "
                  "Fe I 438.3545, 440.4750, 441.5122 nm", "note": MEM}
CODATA = {"title": "CODATA 2018: e/m_e = 1.75882001076e11 C/kg; h = 6.62607015e-34 J s (exact); c exact"}
BW = {"title": "M. Born and E. Wolf, Principles of Optics: multiple-beam interference, polarisation, Fraunhofer "
               "diffraction"}
HENE = {"title": "He-Ne laser red line 632.8 nm (in air)"}
YARIV = {"title": "A. Yariv and P. Yeh, Photonics (Oxford): electro-optic and acousto-optic tables (KDP r63 = 10.6 pm/V, "
                  "n_o = 1.51; LiNbO3 r33 = 30.8 pm/V, n_e = 2.20)", "note": MEM}
KL = {"title": "Kaye and Laby, Tables of Physical and Chemical Constants: Kerr constant of nitrobenzene ~2.4e-12 m/V^2 "
               "(589 nm); Verdet constants of flint glasses", "note": MEM}
HH = {"title": "K. P. Huber and G. Herzberg, Constants of Diatomic Molecules (1979): AlO X 2Sigma+ we = 979.23, "
               "wexe = 6.97 cm-1; B 2Sigma+ Te = 20688.95, we = 870.05, wexe = 3.52 cm-1", "note": MEM}
MEMS = "from memory - verify"


def _bodies(*parts) -> list[dict]:
    """A plain block model for the fallback page; the studio rig draws the real apparatus."""
    out = [B("bench", "box", name="Optical breadboard", size=[1.2, 0.02, 0.5], pos=[0, -0.01, 0], color="#2b2f36", cut=False)]
    n = len(parts)
    for i, (name, info) in enumerate(parts):
        x = -0.45 + 0.9 * i / max(1, n - 1)
        out.append(B(f"part{i}", "box", name=name, info=info, size=[0.07, 0.09, 0.07], pos=[x, 0.045, 0],
                     color="#8a929c" if i % 2 else "#3a4048"))
    return out


def _mk(*, id, title, chapter, aim, kernel, params, knobs, insts, cols, steps, theory, safety, questions, sources,
        parts, rows_min, hint) -> dict:
    return lab(
        id=id, rig=RIG, title=title, group=GRP, level=LVL, topic=chapter, chapter=chapter, aim=aim,
        kernel=kernel, params=params, autorun=True, camera={"pos": [0.0, 0.5, 0.9], "look": [0.0, 0.05, 0.0]},
        floor=-0.2, bodies=_bodies(*parts), knobs=knobs, instruments=insts,
        table={"columns": cols, "calc": kernel, "rows_min": rows_min, "hint": hint},
        steps=steps, theory=theory, safety=safety, questions=questions, sources=sources + [SIM],
        check={"params": {}, "reading": "result", "textbook": kernel},
    )


def _q(q, options, why):
    return {"q": q, "options": options, "answer": 0, "why": why}


LASER_SAFE = ("Laser safety: keep the beam horizontal at bench height, never at eye level. Never look into the beam "
              "or at a mirror-like reflection of it, and take off watches and rings.")
LAMP_SAFE = ("Discharge lamps run hot and some give ultraviolet light: never look at the bare arc, do not touch the "
             "housing, and do not switch a hot lamp off and on again.")
HV_SAFE = ("HIGH VOLTAGE: the cell runs at several kilovolts. Set the supply to zero and switch it off before touching "
           "any lead, keep one hand away from the bench while the supply is on, and never bridge the terminals.")
MAG_SAFE = ("The electromagnet draws several amperes: raise and lower the current slowly, keep watches, cards and "
            "phones away from the pole gap, and never open the coil circuit while current flows.")


# ====================================================================================== Fabry-Perot hyperfine
def fp_hyperfine() -> dict:
    return _mk(
        id="po9-fp-hyperfine", title="Fabry-Perot etalon: hyperfine satellite of the mercury green line",
        chapter="Interferometry and fine structure",
        aim="Form the ring pattern of a Fabry-Perot etalon in the focal plane of a lens, measure the ring "
            "distances with a micrometer eyepiece, and find the wavenumber spacing of a faint satellite from the "
            "main line (or the etalon spacing, or the finesse).",
        kernel="po9_fp", params={"lam": 5.460750e-7, "ds": 10.0, "w2": 0.6, "t": 0.01, "f": 0.3, "R": 0.9},
        knobs=[knob("x", "Cross-wire from the ring centre", "x", 0, 40, 0.001, 4, "mm", 0.001, digits=3),
               knob("ds", "The satellite (its spacing is hidden)", "ds", 0.0, 40.0, 0.0001, 0.1, "cm⁻¹", 100.0,
                    hidden=True),
               knob("t", "The etalon (its spacing is hidden)", "t", 0.05, 20, 0.001, 10, "mm", 0.001, hidden=True),
               knob("R", "Plate coatings (their reflectance is hidden)", "R", 0.5, 0.99, 0.001, 0.9, hidden=True)],
        insts=[inst("I", "readout", "Light at the cross-wire", "I", k=100, unit="%", lc=0.1, digits=1),
               inst("c", "readout", "Component the cross-wire is on (0 main, 1 second)", "c", lc=1, digits=0),
               inst("n", "readout", "Ring number from the centre", "n", lc=1, digits=0)],
        cols=[col("x", "Ring distance from the centre", "knob:x", "mm", 0.001, digits=3),
              col("c", "Component", "inst:c", digits=0),
              col("n", "Ring number", "inst:n", digits=0)],
        steps=["Light the etalon with the lamp through a ground glass and a filter for the line.",
               "Set the etalon plates parallel: the rings must not open or close as you move your eye.",
               "Focus the rings with the lens on the cross-wire of the micrometer eyepiece and centre them.",
               "Set the cross-wire on each ring in turn and read its distance from the centre.",
               "Name each ring: main line or the second component, and its number counted from the centre.",
               "Work out cos(theta) = f / sqrt(f squared + x squared) for each ring and reduce the table."],
        theory="Light that passes a Fabry-Perot etalon of spacing t at an angle theta has gone back and forth many "
               "times; the beams add in step when 2 t sigma cos(theta) = m, a whole number (sigma = 1 / lambda, the "
               "wavenumber). A lens of focal length f turns each angle into a ring of radius x = f tan(theta), so the "
               "pattern is a set of sharp rings. Successive rings of one line differ by 1 in m, so cos(theta) steps "
               "by 1 / (2 t sigma): that gives the spacing t. A second component of wavenumber sigma + d sigma makes "
               "its own rings; in the same order m, sigma1 cos(theta1) = sigma2 cos(theta2), so "
               "d sigma = sigma (cos theta1 / cos theta2 - 1). For small angles this is the textbook "
               "d sigma = (difference of D squared) / (2 t times the step of D squared). The sharpness of a ring "
               "is the finesse: the spacing of two orders over the full width of one at half height, "
               "pi sqrt(R) / (1 - R) for plates of reflectance R.",
        safety=LAMP_SAFE + " The etalon plates are coated on their inner faces: never touch them.",
        questions=[_q("Why does a thicker etalon resolve a closer pair of lines?",
                      ["Its orders are closer in wavenumber, 1 / (2t)", "It lets more light through",
                       "Its rings are larger"], "The free spectral range 1 / (2t) shrinks and each ring gets narrower."),
                   _q("Two components overlap when their spacing exceeds",
                      ["the free spectral range 1 / (2t)", "the finesse", "the ring radius"],
                      "Beyond 1 / (2t) the orders of one line fall between those of the other.")],
        sources=[DU, BW, NIST,
                 {"title": "Mercury 546.1 nm satellite: its spacing in this lab is illustrative of the hyperfine and "
                           "isotope structure of the line, not a quoted component", "note": MEMS}],
        parts=[("Mercury lamp, filter and ground glass", "A broad source of the green line."),
               ("Fabry-Perot etalon", "Two plates a fixed distance apart, coated on their inner faces."),
               ("Lens and micrometer eyepiece", "Form the rings and measure their distances from the centre.")],
        rows_min=4, hint="Record the rings in the order of the procedure, naming each one.")


# ====================================================================================== Zeeman effect
def zeeman() -> dict:
    return _mk(
        id="po9-zeeman", title="Zeeman effect of the mercury green line: e/m with a Fabry-Perot etalon",
        chapter="Atomic spectroscopy",
        aim="Put a mercury lamp between the poles of an electromagnet, resolve the Zeeman pattern of the 546.1 nm "
            "line with a Fabry-Perot etalon, measure the outermost sigma components and find the specific charge "
            "of the electron.",
        kernel="po9_zeeman", params={"lam": 5.460750e-7, "B": 0.5, "gu": 2.0, "gl": 1.5, "ju": 1.0, "jl": 2.0},
        knobs=[knob("x", "Cross-wire from the pattern centre", "x", 0, 40, 0.001, 4, "mm", 0.001, digits=3),
               knob("em", "The electron (its e/m is hidden)", "em", 100, 300, 0.000001, 175.882001076, "× 10⁹ C/kg",
                    1e9, hidden=True)],
        insts=[inst("I", "readout", "Light at the cross-wire", "I", k=100, unit="%", lc=0.1, digits=1),
               inst("c", "readout", "Component, counted from the long-wavelength side", "c", lc=1, digits=0),
               inst("n", "readout", "Order number", "n", lc=1, digits=0)],
        cols=[col("x", "Distance from the centre", "knob:x", "mm", 0.001, digits=3),
              col("c", "Component", "inst:c", digits=0),
              col("n", "Order", "inst:n", digits=0)],
        steps=["Switch the magnet on at zero current, then raise it until the gaussmeter in the gap reads the field "
               "of the procedure. Never break the coil circuit with current flowing.",
               "Look across the field (transverse) or along it through the hollow pole (longitudinal).",
               "Form the pattern of the analyser in the focal plane of the telescope and centre it.",
               "Set the cross-wire on the outermost component on each side of one order and read it; repeat in "
               "the next order.",
               "Work out the wavenumber spread of the pattern and divide it by its spread in Lorentz units."],
        theory="In a magnetic field B a level of total angular momentum J splits into 2J + 1 sublevels M, shifted by "
               "M g mu_B B, with g the Lande factor. A line between two levels breaks into components shifted by "
               "(M_u g_u - M_l g_l) times the Lorentz unit e B / (4 pi m c) in wavenumber; Delta M = 0 gives pi "
               "components and Delta M = +-1 sigma components. Looking across the field shows both; looking along it "
               "shows only the sigma components, circularly polarised. The mercury green line runs 7s 3S1 (g = 2) to "
               "6p 3P2 (g = 3/2): nine components at 0, +-1/2 (pi) and +-1, +-3/2, +-2 (sigma) Lorentz units. The "
               "cadmium red line runs 1D2 to 1P1 with g = 1 for both, the normal triplet at 0, +-1. Measuring the "
               "spread between the outer sigma components in the same order of the etalon, "
               "d sigma = sigma (cos theta_1 / cos theta_2 - 1), and dividing by the spread in Lorentz units gives "
               "e/m; times h c / B it gives the Bohr magneton. A Lummer-Gehrcke plate does the same job with "
               "fringes near grazing emergence, 2 t sigma sqrt(n squared - cos squared alpha) = m.",
        safety=MAG_SAFE + " " + LAMP_SAFE,
        questions=[_q("Looking along the field you see",
                      ["only the sigma components", "only the pi components", "no splitting"],
                      "Light of Delta M = 0 cannot travel along the field."),
                   _q("The cadmium red line shows the normal Zeeman effect because",
                      ["both levels are singlets with g = 1", "cadmium has no spin", "the field is weak"],
                      "With S = 0 every component falls on 0 or +-1 Lorentz unit.")],
        sources=[IITK, DU, CUK, CODATA, NIST, NIST2,
                 {"title": "Lande g factors from the LS-coupling formula (3S1: 2, 3P2: 3/2, 1D2 and 1P1: 1)"}],
        parts=[("Mercury lamp in the pole gap", "The source, in the field of the electromagnet."),
               ("Electromagnet with gaussmeter", "Gives the field B, read in the gap."),
               ("Fabry-Perot etalon, telescope and micrometer eyepiece", "Resolve the pattern and measure it.")],
        rows_min=4, hint="Record the outer components of two orders.")


# ====================================================================================== elliptical polarisation
def ellipse() -> dict:
    return _mk(
        id="po9-ellipse", title="Elliptically polarised light: ellipticity with a quarter-wave plate and analyser",
        chapter="Polarisation",
        aim="Make elliptically polarised light with a mica plate between a polariser and an analyser, find the "
            "azimuth of its major axis with the analyser, turn it into plane light with a quarter-wave plate set "
            "on that axis, and get the ellipticity from the analyser's null.",
        kernel="po9_ellipse", params={"del": 1.2, "phi": 30 * DEG, "lam": 5.893e-7, "beta": 0.004, "x0": 0.005},
        knobs=[knob("stage", "In the beam (0 the plate only, 1 with the quarter-wave plate)", "stage", 0, 1, 1, 0),
               knob("A", "Analyser", "A", 0, 360, 0.01, 0, "°", DEG, digits=2),
               knob("x", "Compensator micrometer", "x", 0, 25, 0.001, 5, "mm", 0.001, digits=3),
               knob("del", "The plate (its retardation is hidden)", "del", 0.0, 6.2, 0.0001, 1.2, "rad",
                    hidden=True)],
        insts=[inst("I", "readout", "Photocell reading", "I", k=100, unit="%", lc=0.01, digits=2)],
        cols=[col("stage", "In the beam", "knob:stage", digits=0),
              col("A", "Analyser", "knob:A", "°", DEG, digits=2),
              col("x", "Compensator", "knob:x", "mm", 0.001, digits=3),
              col("I", "Photocell", "inst:I", "%", 0.01, digits=2)],
        steps=["Cross the polariser and analyser with nothing between them.",
               "Put the plate in its rotating mount with its axis at 30 degrees to the polariser.",
               "Read the light with the analyser at 0, 45, 90 and 135 degrees: the azimuth of the ellipse is "
               "half the angle whose tangent is (I45 - I135) / (I0 - I90).",
               "Put the quarter-wave plate in with its axis along that azimuth: the light leaves plane polarised.",
               "Turn the analyser to the null and read it. The ellipticity angle is null - 90 degrees - azimuth."],
        theory="A plate of retardation delta with its axis at phi to plane-polarised light sends out two "
               "components out of step by delta: in general an ellipse. Its Stokes parameters give the azimuth of "
               "the major axis, tan 2alpha = S2 / S1, and the ellipticity angle chi, sin 2chi = S3 / S0 = "
               "sin 2phi sin delta; the axis ratio is b / a = tan chi. The analyser alone measures S1 and S2 "
               "(intensities at 0, 45, 90 and 135 degrees). A quarter-wave plate whose axis lies along the major "
               "axis puts the two axis components back in step, so the light becomes plane at alpha + chi: the "
               "analyser's null is then at 90 degrees beyond it. With a Babinet compensator whose axes lie along the "
               "plate's, the dark fringe moves by the fraction delta / (2 pi) of a fringe, and the analyser that "
               "makes it black gives psi = phi; then sin 2chi = sin 2psi sin delta.",
        safety=LAMP_SAFE + " Mica and wave plates are thin: hold them by the mount, never by the face.",
        questions=[_q("A quarter-wave plate along the major axis makes the light",
                      ["plane polarised", "circular", "unpolarised"],
                      "It brings the two axis components back into phase."),
                   _q("Which plate setting gives circular light from a quarter-wave plate?",
                      ["Its axis at 45 degrees to the polariser", "Its axis along the polariser", "Any setting"],
                      "Equal components a quarter wave apart make a circle.")],
        sources=[DU, BW, {"title": "Mica sheet: retardation of this sheet is hidden; muscovite birefringence ~0.004",
                          "note": MEMS}],
        parts=[("Sodium lamp and polariser", "Plane-polarised yellow light."),
               ("Mica plate and quarter-wave plate", "Make the ellipse, then turn it back into plane light."),
               ("Analyser and photocell (or Babinet compensator)", "Read the light.")],
        rows_min=5, hint="Record the four analyser readings, then the null with the quarter-wave plate in.")


# ====================================================================================== birefringence
def biref() -> dict:
    return _mk(
        id="po9-biref", title="Birefringence of a quartz plate with a Babinet compensator",
        chapter="Polarisation",
        aim="Calibrate a Babinet compensator between crossed polarisers, put a thin quartz plate in front of it, "
            "and find the plate's birefringence from the shift of the dark fringe (or by a rotating analyser).",
        kernel="po9_biref", params={"t": 3.0e-5, "lam": 5.893e-7, "beta": 0.004, "x0": 0.005},
        knobs=[knob("stage", "In the beam (0 compensator only, 1 with the plate)", "stage", 0, 1, 1, 0),
               knob("x", "Compensator micrometer", "x", 0, 25, 0.001, 5, "mm", 0.001, digits=3),
               knob("A", "Analyser", "A", 0, 360, 0.01, 0, "°", DEG, digits=2),
               knob("dn", "The crystal (its birefringence is hidden)", "dn", 0.0005, 0.05, 0.000001, 0.0091,
                    hidden=True)],
        insts=[inst("I", "readout", "Light at the cross-wire", "I", k=100, unit="%", lc=0.01, digits=2)],
        cols=[col("stage", "In the beam", "knob:stage", digits=0),
              col("x", "Compensator", "knob:x", "mm", 0.001, digits=3),
              col("A", "Analyser", "knob:A", "°", DEG, digits=2),
              col("I", "Light", "inst:I", "%", 0.01, digits=2)],
        steps=["Cross the polariser and analyser, the compensator between them with its axes at 45 degrees.",
               "Set the cross-wire on one dark fringe and then on the next: their distance is the fringe width.",
               "Put the plate in front of the compensator with its axes along the compensator's.",
               "Find the dark fringe again: its shift as a fraction of the fringe width is delta / (2 pi).",
               "Birefringence = delta lambda / (2 pi t), t the plate's thickness from a screw gauge."],
        theory="In a uniaxial crystal cut parallel to its optic axis the ordinary and extraordinary waves travel at "
               "different speeds, so a plate of thickness t puts them out of step by delta = 2 pi dn t / lambda, "
               "dn = n_e - n_o. A Babinet compensator is two quartz wedges with crossed axes; along it the phase "
               "difference changes linearly, so between crossed polarisers it shows straight dark fringes one "
               "fringe width beta apart. A plate in front adds delta and shifts every fringe by beta delta / (2 pi). "
               "Without a compensator, the plate at 45 degrees between a polariser and an analyser passes "
               "I(theta) = cos^2 theta - cos 2theta sin^2(delta / 2): crossed it gives sin^2(delta / 2), parallel "
               "cos^2(delta / 2), so delta = 2 asin sqrt(I_crossed / (I_crossed + I_parallel)) for a plate thinner "
               "than a half wave.",
        safety=LAMP_SAFE + " Thin crystal plates are fragile: hold them by the mount.",
        questions=[_q("The retardation of a plate grows with",
                      ["its thickness and its birefringence", "the brightness of the lamp", "the angle of the analyser"],
                      "delta = 2 pi dn t / lambda."),
                   _q("A half-wave plate between crossed polarisers at 45 degrees gives",
                      ["full transmission", "darkness", "half the light"], "sin^2(pi / 2) = 1.")],
        sources=[DU, BW, {"title": "Quartz at 589 nm: n_o = 1.5443, n_e = 1.5534 (dn = 0.0091); muscovite mica dn ~0.0042",
                          "note": MEMS}],
        parts=[("Sodium lamp and polariser", "Plane-polarised yellow light."),
               ("Babinet compensator with micrometer", "Two quartz wedges with crossed axes."),
               ("Crystal plate and analyser", "The plate under test, then the analyser and the eyepiece.")],
        rows_min=3, hint="Record two dark fringes without the plate and the shifted fringe with it.")


# ====================================================================================== photoelasticity
def photoelastic() -> dict:
    return _mk(
        id="po9-photoelastic", title="Photoelasticity: stress-optic coefficient of an epoxy disc",
        chapter="Polarisation and stress",
        aim="Load an epoxy disc across a diameter in a circular polariscope, count the dark fringes that pass its "
            "centre as the load rises, and find the stress-optic coefficient from the fringe order per newton.",
        kernel="po9_photoel", params={"D": 0.05, "hb": 0.012, "a": 0.03, "lam": 5.461e-7, "shape": 0.0, "pol": 1.0},
        knobs=[knob("x", "Load on the model", "x", 0, 2000, 0.01, 0, "N", digits=2),
               knob("C", "The model's material (its stress-optic coefficient is hidden)", "C", 1, 300, 0.01, 55,
                    "Brewster", 1e-12, hidden=True)],
        insts=[inst("I", "readout", "Light at the watched point", "I", k=100, unit="%", lc=0.1, digits=1),
               inst("n", "readout", "Dark fringes counted past the point", "n", lc=1, digits=0)],
        cols=[col("x", "Load", "knob:x", "N", digits=2),
              col("n", "Fringe order", "inst:n", digits=0)],
        steps=["Set up the polariscope with monochromatic green light: crossed polariser and analyser (and two "
               "quarter-wave plates for the circular polariscope).",
               "Put the unloaded model in the frame: the field is dark.",
               "Raise the load slowly; every time a dark fringe passes the watched point, stop and read the load.",
               "Plot the load against the fringe order: the slope gives the fringe order per newton.",
               "C = (fringe order per newton) times pi D lambda / 8 for the disc."],
        theory="A stressed transparent plastic becomes birefringent: along the principal stress directions the "
               "indices differ by C (sigma1 - sigma2), C the stress-optic coefficient (1 brewster = 1e-12 m^2/N). "
               "Through a thickness h this gives a fringe order N = C h (sigma1 - sigma2) / lambda. In a dark-field "
               "polariscope the light at a point is sin^2(pi N) (a plane polariscope adds the isoclinic factor "
               "sin^2 2alpha, which is 1 with the axes at 45 degrees to the load). At the centre of a disc of "
               "diameter D under a diametral load F, sigma1 - sigma2 = 8 F / (pi D h), so N = 8 C F / (pi D lambda), "
               "free of the thickness. In a beam of depth h_b in four-point bending, loads F/2 at a from each support, "
               "the outer fibre carries sigma = 3 F a / (h h_b^2), so N = 3 C F a / (h_b^2 lambda).",
        safety="Load the model slowly and stay within the frame's rating: an overloaded plastic model can crack and "
               "fly out of the frame. Wear safety glasses.",
        questions=[_q("Why is the disc's fringe order free of its thickness?",
                      ["Stress falls as 1/h while the path grows as h", "The disc is thin", "The light is green"],
                      "N = C h (sigma1 - sigma2) / lambda and sigma ~ F / h."),
                   _q("The circular polariscope removes",
                      ["the isoclinic fringes", "the isochromatic fringes", "the stress"],
                      "With quarter-wave plates the light no longer depends on the stress directions.")],
        sources=[DU, {"title": "J. W. Dally and W. F. Riley, Experimental Stress Analysis: the disc and beam "
                               "calibrations of photoelastic materials", "note": MEMS},
                 {"title": "Epoxy (Araldite) C ~55 brewster, polycarbonate C ~78 brewster at 546 nm",
                  "note": MEMS}],
        parts=[("Mercury lamp with green filter", "Monochromatic light, 546.1 nm."),
               ("Polariscope with loading frame", "Polariser, quarter-wave plates, the model, analyser."),
               ("Load cell", "Reads the load on the model.")],
        rows_min=4, hint="Record the load at zero and each time a dark fringe passes the watched point.")


# ====================================================================================== Kerr effect
def kerr() -> dict:
    return _mk(
        id="po9-kerr", title="Electro-optic Kerr effect in nitrobenzene: the Kerr constant",
        chapter="Electro-optics",
        aim="Put a nitrobenzene Kerr cell at 45 degrees between crossed polarisers, raise the voltage on its "
            "plates, read the light through the analyser, and find the Kerr constant from the half-wave voltage.",
        kernel="po9_eo", params={"kind": 0.0, "l": 0.05, "d": 0.005, "lam": 6.328e-7},
        knobs=[knob("x", "Voltage on the plates", "x", 0, 15000, 0.1, 0, "V", digits=1),
               knob("K", "The liquid (its Kerr constant is hidden)", "K", 0.1, 10, 0.0001, 2.4, "× 10⁻¹² m/V²",
                    1e-12, hidden=True)],
        insts=[inst("P", "readout", "Light through the analyser", "P", k=1e6, unit="µW", lc=0.001, digits=3)],
        cols=[col("x", "Voltage", "knob:x", "V", digits=1),
              col("P", "Light", "inst:P", "µW", 1e-6, digits=3)],
        steps=["Cross the polariser and analyser with the cell between them, its field at 45 degrees.",
               "With no voltage the field is dark.",
               "Raise the voltage in steps and read the light; the light rises to a maximum at the half-wave voltage.",
               "From each reading below the maximum, Gamma = 2 asin sqrt(P / P_max) and V_pi = V sqrt(pi / Gamma).",
               "K = d^2 / (2 l V_pi^2)."],
        theory="An electric field E aligns the polar molecules of a liquid, which becomes birefringent with "
               "dn = lambda K E^2 (K the Kerr constant). Over a path l between plates d apart (E = V / d) the "
               "light's two components fall out of step by Gamma = 2 pi K l (V / d)^2. Between crossed polarisers "
               "with the field at 45 degrees the cell passes P = P0 sin^2(Gamma / 2): dark at zero, a maximum at the "
               "half-wave voltage V_pi = d / sqrt(2 K l). Nitrobenzene has one of the largest Kerr constants of any "
               "liquid, which is why it fills Kerr shutters.",
        safety=HV_SAFE + " Nitrobenzene is toxic through the skin and its vapour: the cell stays sealed; wear gloves.",
        questions=[_q("Doubling the voltage multiplies the retardation of a Kerr cell by",
                      ["4", "2", "8"], "Gamma grows as V squared."),
                   _q("The cell gives no light with zero voltage because",
                      ["the liquid is isotropic without a field", "the polarisers are parallel", "the laser is off"],
                      "Without a field nothing turns the plane of polarisation.")],
        sources=[IITK, CUK, KL, HENE],
        parts=[("He-Ne laser and polariser", "Plane-polarised red light."),
               ("Kerr cell with nitrobenzene", "Two plates d apart in a sealed glass cell, fed from a high-voltage supply."),
               ("Analyser and photodetector", "Read the light through the crossed analyser.")],
        rows_min=5, hint="Record the light at each voltage up to and just past the maximum.")


def pockels() -> dict:
    return _mk(
        id="po9-pockels", title="Pockels effect: half-wave voltage of a KDP crystal",
        chapter="Electro-optics",
        aim="Put a longitudinal KDP Pockels cell at 45 degrees between crossed polarisers, raise the voltage, and "
            "find its half-wave voltage (and its electro-optic coefficient).",
        kernel="po9_eo", params={"kind": 1.0, "n": 1.51, "lam": 6.328e-7, "mode": 1.0},
        knobs=[knob("x", "Voltage on the crystal", "x", 0, 15000, 0.1, 0, "V", digits=1),
               knob("r", "The crystal (its electro-optic coefficient is hidden)", "r", 1, 100, 0.0001, 10.6, "pm/V",
                    1e-12, hidden=True)],
        insts=[inst("P", "readout", "Light through the analyser", "P", k=1e6, unit="µW", lc=0.001, digits=3)],
        cols=[col("x", "Voltage", "knob:x", "V", digits=1),
              col("P", "Light", "inst:P", "µW", 1e-6, digits=3)],
        steps=["Cross the polariser and analyser with the crystal between them, its induced axes at 45 degrees.",
               "Raise the voltage in steps and read the light up to and past the maximum.",
               "From each reading below the maximum Gamma = 2 asin sqrt(P / P_max) and V_pi = pi V / Gamma.",
               "Longitudinal cell: r = lambda / (2 n^3 V_pi); transverse cell: r = lambda d / (2 n^3 L V_pi)."],
        theory="In a crystal without a centre of symmetry an electric field changes the index linearly: "
               "dn = n^3 r E / 2, r the electro-optic coefficient. In a longitudinal KDP cell (field along the beam) "
               "the induced axes are at 45 degrees and the retardation is Gamma = 2 pi n^3 r63 V / lambda, the same "
               "for any crystal length. In a transverse lithium niobate cell of length L with electrodes d apart, "
               "Gamma = 2 pi n_e^3 r33 V L / (lambda d), so a long thin crystal switches at tens of volts. Between "
               "crossed polarisers the cell passes P0 sin^2(Gamma / 2); the half-wave voltage V_pi is where it "
               "first reaches its maximum.",
        safety=HV_SAFE + " KDP is soluble in water and fragile: keep it sealed and dry.",
        questions=[_q("The retardation of a Pockels cell grows with the voltage",
                      ["linearly", "as its square", "not at all"], "Pockels is first order in E; Kerr is second order."),
                   _q("A transverse cell has a low half-wave voltage because",
                      ["the field acts over a long length L across a small gap d", "its index is low",
                       "it is longitudinal"], "V_pi = lambda d / (2 n^3 r L).")],
        sources=[DU, YARIV, HENE],
        parts=[("He-Ne laser and polariser", "Plane-polarised red light."),
               ("Pockels cell", "The electro-optic crystal between electrodes, fed from a variable supply."),
               ("Analyser and photodetector", "Read the light through the crossed analyser.")],
        rows_min=5, hint="Record the light at each voltage up to and just past the maximum.")


def eo_modulation() -> dict:
    return _mk(
        id="po9-eo-modulation", title="Electro-optic modulation of a laser beam: depth against signal amplitude",
        chapter="Electro-optics",
        aim="Bias a lithium niobate modulator at a quarter wave, drive it with a sine signal of rising amplitude, "
            "measure the modulation depth of the received light, and find the half-wave voltage (or, with the "
            "audio band swept, the bandwidth of the link).",
        kernel="po9_eo", params={"kind": 2.0, "n": 2.2, "d": 0.001, "L": 0.02, "lam": 6.328e-7, "mode": 2.0,
                                 "fc": 2.0e4, "f0": 1.0e3},
        knobs=[knob("x", "Signal amplitude", "x", 0, 50, 0.001, 0, "V", digits=3),
               knob("A", "Signal frequency", "A", 0, 200, 0.01, 1, "kHz", 1000.0, digits=2),
               knob("r", "The crystal (its electro-optic coefficient is hidden)", "r", 1, 100, 0.0001, 30.8, "pm/V",
                    1e-12, hidden=True),
               knob("fc", "The link (its bandwidth is hidden)", "fc", 0.5, 200, 0.001, 20, "kHz", 1000.0,
                    hidden=True)],
        insts=[inst("m", "readout", "Modulation depth of the received light", "m", k=100, unit="%", lc=0.0001,
                    digits=4)],
        cols=[col("x", "Amplitude", "knob:x", "V", digits=3),
              col("A", "Frequency", "knob:A", "kHz", 1000.0, digits=2),
              col("P", "Mean light", "manual", "mW", 1e-3, digits=3),
              col("m", "Depth", "inst:m", "%", 0.01, digits=4)],
        steps=["Bias the modulator at a quarter wave with a quarter-wave plate: the mean light is half the maximum.",
               "Feed the sine signal from the generator and watch the received light on the oscilloscope.",
               "Depth = (peak - trough) / (peak + trough) of the received signal.",
               "Raise the amplitude in steps (sine signal), or sweep the frequency at a fixed amplitude (audio).",
               "Depth = sin(pi V_m / V_pi): the slope of asin(depth) against V_m is pi / V_pi."],
        theory="Biased at a quarter wave, a Pockels modulator's transmission is P = (P0 / 2)(1 + sin(pi v / V_pi)) "
               "for a drive v, so a signal of amplitude V_m modulates the light by m = sin(pi V_m / V_pi), linear for "
               "small signals. This is how the cell writes a sine wave or an audio programme onto the laser beam. "
               "The driver and the crystal's capacitance pass a signal of frequency f in the ratio "
               "H = 1 / sqrt(1 + (f / f_c)^2), so the depth falls by 1 / sqrt 2 at the bandwidth f_c.",
        safety=LASER_SAFE + " Keep the drive below the generator's limit; the modulator's electrodes are close together.",
        questions=[_q("Why is the modulator biased at a quarter wave?",
                      ["The transmission is steepest and most linear there", "It is darkest there",
                       "It needs no voltage there"], "The sine has its largest slope at the half-transmission point."),
                   _q("At the bandwidth f_c the depth is", ["70.7 % of its low-frequency value", "half", "zero"],
                      "H = 1 / sqrt 2 at f = f_c.")],
        sources=[DU, YARIV,
                 {"title": "Link bandwidth: the driver and modulator here are illustrative, not a named part",
                  "note": "unsourced / illustrative"}],
        parts=[("He-Ne laser and polariser", "The carrier beam."),
               ("Lithium niobate modulator, quarter-wave plate and signal generator", "Write the signal onto the light."),
               ("Analyser, photodiode and oscilloscope", "Receive the light and show its modulation.")],
        rows_min=5, hint="Record the depth at each amplitude (or frequency) of the procedure.")


# ====================================================================================== Faraday effect
def faraday() -> dict:
    return _mk(
        id="po9-faraday", title="Faraday effect: Verdet constant of flint glass with a sodium lamp",
        chapter="Magneto-optics",
        aim="Send plane-polarised sodium light along a flint glass rod in the gap of an electromagnet, find the "
            "analyser's null at several fields, and get the Verdet constant from the rotation per tesla.",
        kernel="po9_faraday", params={"l": 0.1, "kB": 0.05, "lam": 5.893e-7, "l0": 4.5e-7, "l1": 5.5e-7, "l2": 6.5e-7},
        knobs=[knob("stage", "Filter (0 blue 450, 1 green 550, 2 red 650 nm)", "stage", 0, 2, 1, 0),
               knob("A", "Magnet current", "A", 0, 5, 0.001, 0, "A", digits=3),
               knob("x", "Analyser", "x", 0, 360, 0.001, 90, "°", DEG, digits=3),
               knob("V", "The glass (its Verdet constant is hidden)", "V", 1, 100, 0.001, 9.22, "rad/(T m)",
                    hidden=True)],
        insts=[inst("B", "readout", "Gaussmeter", "B", k=1000, unit="mT", lc=0.1, digits=1),
               inst("P", "readout", "Light through the analyser", "P", k=100, unit="%", lc=0.01, digits=2),
               inst("m", "readout", "Modulation depth", "m", k=100, unit="%", lc=0.001, digits=3)],
        cols=[col("stage", "Filter", "knob:stage", digits=0),
              col("A", "Current", "knob:A", "A", digits=3),
              col("B", "Field", "inst:B", "mT", 0.001, digits=1),
              col("x", "Analyser at null", "knob:x", "°", DEG, digits=3),
              col("m", "Depth", "inst:m", "%", 0.01, digits=3)],
        steps=["Cross the analyser with the polariser with no current: note the null.",
               "Raise the current in steps; at each step read the gaussmeter and turn the analyser back to the null.",
               "Plot the analyser reading against the field: the slope over the rod's length is the Verdet constant.",
               "With the tungsten lamp, repeat with each filter in turn to see how V depends on the wavelength."],
        theory="A magnetic field along the direction of the light turns its plane of polarisation by "
               "rho = V B l, l the length of glass in the field and V the Verdet constant, which belongs to the "
               "material and the wavelength. Unlike optical activity, the turn does not undo itself on reflection: "
               "it follows the field, not the light. Becquerel's relation V = (e / 2 m c) lambda dn / dlambda with a "
               "Cauchy index n = A + B / lambda^2 makes V fall roughly as 1 / lambda^2, which the filters test: "
               "ln V against ln lambda has slope -2 in this model.",
        safety=MAG_SAFE + " The tungsten lamp housing gets hot.",
        questions=[_q("Sending the light back through the rod after a mirror",
                      ["doubles the rotation", "cancels the rotation", "leaves it unchanged"],
                      "The Faraday turn follows the field, so the return trip adds to it."),
                   _q("Blue light is turned more than red because",
                      ["dn / dlambda is larger at short wavelengths", "it is brighter", "the field is stronger"],
                      "V ~ lambda dn / dlambda ~ 1 / lambda^2.")],
        sources=[IITK, KL, {"title": "Verdet constants at 589 nm: flint glass ~0.0317 and dense flint ~0.088 arcmin/(G cm) "
                                     "(9.2 and 25.6 rad/(T m))", "note": MEMS}],
        parts=[("Sodium lamp (or tungsten lamp and filters) and polariser", "Plane-polarised light."),
               ("Flint glass rod in the electromagnet", "Its length l is in the field, read by a gaussmeter."),
               ("Analyser and photocell", "Find the null at each field.")],
        rows_min=5, hint="Record the field and the null at each current.")


def magneto_optic() -> dict:
    return _mk(
        id="po9-magneto-optic", title="Magneto-optic modulation of a laser beam with a flint rod in a solenoid",
        chapter="Magneto-optics",
        aim="Drive a solenoid round a flint glass rod with an alternating current, set the analyser at 45 degrees, "
            "and measure how the depth of modulation of the laser light grows with the coil current.",
        kernel="po9_faraday", params={"l": 0.1, "kB": 0.012, "lam": 6.328e-7, "mode": 2.0},
        knobs=[knob("A", "Coil current amplitude", "A", 0, 5, 0.001, 0, "A", digits=3),
               knob("V", "The glass (its Verdet constant is hidden)", "V", 1, 100, 0.001, 9.22, "rad/(T m)",
                    hidden=True)],
        insts=[inst("B", "readout", "Peak field from the coil calibration", "B", k=1000, unit="mT", lc=0.01, digits=2),
               inst("m", "readout", "Modulation depth", "m", k=100, unit="%", lc=0.001, digits=3)],
        cols=[col("A", "Current amplitude", "knob:A", "A", digits=3),
              col("B", "Peak field", "inst:B", "mT", 0.001, digits=2),
              col("m", "Depth", "inst:m", "%", 0.01, digits=3)],
        steps=["Set the analyser at 45 degrees to the polariser: half the light gets through.",
               "Feed an alternating current to the solenoid and watch the photodiode signal on the oscilloscope.",
               "Depth = (peak - trough) / (peak + trough).",
               "Raise the current amplitude in steps and record the depth.",
               "asin(depth) / 2 is the peak rotation V B l: its slope against B over l is V."],
        theory="With the analyser at 45 degrees the transmitted light is P = (P0 / 2)(1 + sin 2rho), so a rotation "
               "rho = V B l that swings with the coil current writes the current's waveform onto the beam with depth "
               "m = sin(2 V B l). The field of a long solenoid is B = mu0 N I / L, given here by the coil's "
               "calibration in tesla per ampere. This is a magneto-optic modulator: no moving part, the light is "
               "switched by a current.",
        safety=LASER_SAFE + " The solenoid warms up at high current: switch it off between readings.",
        questions=[_q("Why is the analyser at 45 degrees?",
                      ["The transmission changes fastest with rotation there", "It is dark there", "To protect the laser"],
                      "d/drho of cos^2(45 deg - rho) is largest at rho = 0."),
                   _q("For small currents the depth grows", ["linearly with the current", "as its square", "not at all"],
                      "m = sin 2VBl ~ 2VBl.")],
        sources=[DU, KL, HENE],
        parts=[("He-Ne laser and polariser", "The carrier beam."),
               ("Flint glass rod in a solenoid", "Driven by an alternating current."),
               ("Analyser at 45 degrees and photodiode", "Read the modulated light on an oscilloscope.")],
        rows_min=4, hint="Record the depth at each current amplitude.")


# ====================================================================================== laser diffraction
def laser_2d() -> dict:
    return _mk(
        id="po9-laser-2d", title="Diffraction of He-Ne laser light by a wire mesh: the mesh spacing",
        chapter="Diffraction",
        aim="Shine a He-Ne laser through a two-dimensional object, measure the positions of the spots (or the dark "
            "rings and bands) on a distant screen, and find the lattice spacing or the size of the aperture.",
        kernel="po9_fraun", params={"lam": 6.328e-7, "L": 1.0, "a": 1.5e-4, "d": 2.54e-4, "N": 20.0, "mode": 0.0},
        knobs=[knob("x", "Screen cursor from the central spot", "x", 0, 200, 0.001, 0, "mm", 0.001, digits=3),
               knob("d", "The object (its spacing is hidden)", "d", 0.5, 2000, 0.0001, 254, "µm", 1e-6, hidden=True),
               knob("a", "The object (its opening is hidden)", "a", 0.5, 2000, 0.0001, 150, "µm", 1e-6, hidden=True)],
        insts=[inst("I", "readout", "Light at the cursor", "I", k=100, unit="%", lc=0.01, digits=2),
               inst("m", "readout", "Order counted from the centre", "m", lc=1, digits=0)],
        cols=[col("x", "Distance on the screen", "knob:x", "mm", 0.001, digits=3),
              col("m", "Order", "inst:m", digits=0),
              col("I", "Light", "inst:I", "%", 0.01, digits=2)],
        steps=["Set the object square to the beam and the screen a measured distance L behind it.",
               "Centre the cursor on the central spot.",
               "Move the cursor along one row of spots (or across the dark rings) and read each one's distance.",
               "sin(theta) = sin(atan(x / L)); a lattice gives d sin(theta) = m lambda, a circle "
               "a sin(theta) = (zero of J1) lambda / pi, a square a sin(theta) = m lambda."],
        theory="Far from the object (Fraunhofer) the pattern is the Fourier transform of its transmission. A wire mesh "
               "or a cross grating repeats in two directions, so its pattern is a two-dimensional lattice of spots: "
               "along each axis d sin(theta) = m lambda, d the pitch, under a sinc^2 envelope set by the opening. A "
               "circular aperture of diameter a gives the Airy pattern (2 J1(v) / v)^2 with v = pi a sin(theta) / "
               "lambda: dark rings where J1 vanishes, v = 3.8317, 7.0156. A square aperture of side a gives a cross "
               "of sinc^2 bands, dark at a sin(theta) = m lambda.",
        safety=LASER_SAFE,
        questions=[_q("A finer mesh spreads its spots", ["further apart", "closer together", "not at all"],
                      "sin(theta) = m lambda / d."),
                   _q("The first dark ring of a circular aperture is at", ["1.22 lambda / a", "lambda / a", "lambda / 2a"],
                      "3.8317 / pi = 1.2197.")],
        sources=[IITK, BW, HENE],
        parts=[("He-Ne laser", "632.8 nm."),
               ("Object holder", "Wire mesh, cross grating or an aperture."),
               ("Screen with a millimetre scale and cursor", "At a distance L.")],
        rows_min=2, hint="Record the positions of the spots (or dark rings / bands) and their orders.")


def laser_slits() -> dict:
    return _mk(
        id="po9-laser-slits", title="Laser diffraction at a single slit: the slit width",
        chapter="Diffraction",
        aim="Shine a laser through a single slit, a double slit or a grating, measure the minima or maxima on a "
            "screen, and find the slit width, the slit separation or the laser's wavelength.",
        kernel="po9_fraun", params={"lam": 6.328e-7, "L": 1.0, "a": 1.0e-4, "d": 5.0e-4, "N": 20.0, "mode": 3.0},
        knobs=[knob("x", "Screen cursor from the central maximum", "x", 0, 200, 0.001, 0, "mm", 0.001, digits=3),
               knob("a", "The slit (its width is hidden)", "a", 0.5, 2000, 0.0001, 100, "µm", 1e-6, hidden=True),
               knob("d", "The slits (their separation is hidden)", "d", 0.5, 2000, 0.0001, 500, "µm", 1e-6,
                    hidden=True),
               knob("lam", "The laser (its wavelength is hidden)", "lam", 400, 800, 0.001, 632.8, "nm", 1e-9,
                    hidden=True)],
        insts=[inst("I", "readout", "Light at the cursor", "I", k=100, unit="%", lc=0.01, digits=2),
               inst("m", "readout", "Order counted from the centre", "m", lc=1, digits=0)],
        cols=[col("x", "Distance on the screen", "knob:x", "mm", 0.001, digits=3),
              col("m", "Order", "inst:m", digits=0),
              col("I", "Light", "inst:I", "%", 0.01, digits=2)],
        steps=["Set the slit square to the beam and the screen a measured distance L behind it.",
               "Centre the cursor on the central maximum.",
               "Move the cursor to each minimum (single slit) or maximum (double slit, grating) and read it.",
               "Single slit: a sin(theta) = m lambda at the minima. Double slit: d sin(theta) = m lambda at the "
               "maxima. Grating: lambda = d sin(theta) / m."],
        theory="A slit of width a gives the Fraunhofer pattern sinc^2(pi a sin(theta) / lambda), dark wherever "
               "a sin(theta) = m lambda. Two slits d apart multiply it by cos^2(pi d sin(theta) / lambda): bright "
               "fringes at d sin(theta) = m lambda under the single-slit envelope (an order is missing where it "
               "falls on an envelope zero). A grating of many lines d apart keeps only the sharp principal maxima, "
               "d sin(theta) = m lambda, so with d known it measures the wavelength.",
        safety=LASER_SAFE,
        questions=[_q("Making the slit narrower makes the central maximum", ["wider", "narrower", "brighter"],
                      "Its half width is lambda / a."),
                   _q("A missing order in the double-slit pattern means", ["a maximum falls on an envelope zero",
                                                                         "the laser flickered", "the slits are wider apart"],
                      "d / a is then a whole number ratio.")],
        sources=[DU, BW, HENE],
        parts=[("Laser", "The light source."),
               ("Slit holder", "Single slit, double slit or grating."),
               ("Screen with a millimetre scale and cursor", "At a distance L.")],
        rows_min=2, hint="Record the positions of the minima (or maxima) and their orders.")


# ====================================================================================== constant deviation spectrometer
def cdev() -> dict:
    return _mk(
        id="po9-cdev", title="Constant deviation spectrometer: the mercury yellow doublet",
        chapter="Atomic spectroscopy",
        aim="Calibrate the wavelength drum of a constant deviation spectrometer on three mercury lines, then "
            "measure lines of the lamp under test and find their separation (or a wavelength).",
        kernel="po9_cdev", params={"l1": 5.769610e-7, "l2": 5.790670e-7, "e0": 8.0e-10, "e1": 0.004, "e2": 1.0e4,
                                   "w": 1.5e-10},
        knobs=[knob("stage", "Lamp (0 mercury calibration lamp, 1 lamp under test)", "stage", 0, 1, 1, 0),
               knob("x", "Wavelength drum", "x", 380, 720, 0.0001, 550, "nm", 1e-9, digits=4),
               knob("l1", "The first line (hidden)", "l1", 380, 720, 0.000001, 576.961, "nm", 1e-9, hidden=True),
               knob("l2", "The second line (hidden)", "l2", 380, 720, 0.000001, 579.067, "nm", 1e-9, hidden=True)],
        insts=[inst("I", "readout", "Line on the cross-wire", "I", k=100, unit="%", lc=0.1, digits=1)],
        cols=[col("stage", "Lamp", "knob:stage", digits=0),
              col("x", "Drum reading", "knob:x", "nm", 1e-9, digits=4)],
        steps=["Light the slit with the mercury lamp; focus the telescope on the slit image.",
               "Turn the drum to set the violet 404.66, blue 435.83 and green 546.07 nm lines on the cross-wire; "
               "read the drum each time.",
               "The drum readings against the true wavelengths give the correction curve.",
               "Put the lamp under test in front of the slit and set each of its lines on the cross-wire.",
               "Correct the readings with the curve: the difference of the two corrected readings is the separation."],
        theory="In a constant deviation spectrometer a Pellin-Broca prism turns on a table; for each angle one "
               "wavelength passes through it at minimum deviation and leaves at exactly 90 degrees into the fixed "
               "telescope. The drum that turns the prism is engraved in wavelength, but no engraving is perfect: it "
               "reads lambda + e(lambda). Three known lines fit the correction (a quadratic through three points), "
               "and every other reading is then corrected on the same curve. The yellow mercury doublet (576.96 and "
               "579.07 nm), the sodium D lines (589.00 and 589.59 nm, the fine structure of 3p) and the neon lines "
               "are resolved and measured this way.",
        safety=LAMP_SAFE,
        questions=[_q("Why calibrate the drum on known lines?",
                      ["The engraved scale has its own error", "The lamp drifts", "The prism is not glass"],
                      "Every reading is corrected on the curve the known lines give."),
                   _q("The sodium D lines are two because", ["the 3p level is split by spin-orbit coupling",
                                                             "sodium has two isotopes", "the prism doubles them"],
                      "3p 2P1/2 and 2P3/2 differ by 17.2 cm-1.")],
        sources=[DU, CUK, NIST, NIST2,
                 {"title": "Drum error: the instrument's correction curve here is illustrative", "note": "unsourced / illustrative"}],
        parts=[("Mercury lamp (calibration) and the lamp under test", "Light the slit in turn."),
               ("Pellin-Broca prism on its table", "Turned by the wavelength drum."),
               ("Fixed telescope at 90 degrees", "The line on the cross-wire is the one the drum names.")],
        rows_min=5, hint="Record the three mercury lines, then the lines of the lamp under test.")


# ====================================================================================== Rowland concave grating
def rowland() -> dict:
    return _mk(
        id="po9-rowland", title="Concave grating in a Rowland mounting: plate factor from mercury lines",
        chapter="Atomic spectroscopy",
        aim="Read the positions of standard lines on a plate taken with a concave grating in a Rowland mounting, "
            "and find the plate factor (dispersion), an unknown wavelength, or the resolving power.",
        kernel="po9_rowland", params={"R": 1.0, "d": 1.0 / 600000.0, "al": 10 * DEG, "m": 1.0, "N": 5000.0,
                                      "la": 5.460750e-7, "lb": 5.769610e-7},
        knobs=[knob("x", "Comparator reading along the plate", "x", 50, 300, 0.0001, 150, "mm", 0.001, digits=4),
               knob("lu", "The unknown line (hidden)", "lu", 380, 720, 0.000001, 579.067, "nm", 1e-9, hidden=True),
               knob("N", "The grating (its lit lines are hidden)", "N", 100, 100000, 1, 5000, hidden=True)],
        insts=[inst("I", "readout", "Blackening under the cross-wire", "I", k=100, unit="%", lc=0.1, digits=1)],
        cols=[col("x", "Comparator reading", "knob:x", "mm", 0.001, digits=4),
              col("I", "Blackening", "inst:I", "%", 0.01, digits=1)],
        steps=["Lay the plate on the comparator, emulsion up, with the lines across the cross-wire.",
               "Set the cross-wire on each standard line and read the comparator.",
               "Plate factor = difference of wavelengths / difference of positions (nm per mm).",
               "Set on the unknown line and interpolate its wavelength from the two standards.",
               "For the resolving power, set on the two half-blackening edges of a line: R = lambda / (FWHM / 0.886)."],
        theory="A concave grating focuses its own spectrum: with the slit on the Rowland circle (diameter equal to "
               "the grating's radius of curvature R) every wavelength focuses on that circle, so a curved plate "
               "along it records the whole spectrum with no lens. A line leaves at beta with "
               "d (sin alpha + sin beta) = m lambda and lands at the arc length s = R beta, so the plate factor is "
               "d cos(beta) / (m R). Between two close standards the wavelength is linear in s. Each line has the "
               "grating's own profile, sinc^2 of pi (lambda - lambda_i) m N / lambda_i: its first zero lambda / (m N) "
               "is the Rayleigh limit, and its full width at half height is 0.886 of it.",
        safety=LAMP_SAFE + " An iron arc gives strong ultraviolet: never view it unshielded.",
        questions=[_q("A Rowland mounting needs no lens because", ["the concave grating focuses its own spectrum",
                                                                    "the plate is curved", "the slit is narrow"],
                      "Slit, grating and focus all lie on the Rowland circle."),
                   _q("The resolving power of a grating is", ["m N", "d / lambda", "R / d"],
                      "The order times the number of lines lit.")],
        sources=[IITK, NIST, NIST2, {"title": "Grating: 600 lines per mm, R = 1 m, 10 degrees incidence (illustrative instrument)",
                              "note": "unsourced / illustrative"}],
        parts=[("Spectrogram on a comparator", "A plate taken in the Rowland mounting."),
               ("Comparator with micrometer and cross-wire", "Reads positions along the plate."),
               ("Standard lines", "Mercury lamp or iron arc lines of known wavelength.")],
        rows_min=2, hint="Record the standard lines first, then the line under study.")


# ====================================================================================== AlO band spectrum
def alo_bands() -> dict:
    return _mk(
        id="po9-alo-bands", title="Vibrational analysis of the AlO band spectrum: anharmonicity of the ground state",
        chapter="Molecular spectroscopy",
        aim="Read the heads of the blue-green AlO bands on a spectrogram, arrange them in a Deslandres table, and "
            "find the vibrational constants of the molecule. SIMULATED DATA: the spectrogram is drawn by Hoola from "
            "published constants.",
        kernel="po9_band", params={"Te": 2068895.0, "we1": 87005.0, "wx1": 352.0, "we0": 97923.0},
        knobs=[knob("x", "Comparator (calibrated in wavelength)", "x", 440, 540, 0.0001, 484, "nm", 1e-9, digits=4),
               knob("wx0", "The molecule (its ground-state anharmonicity is hidden)", "wx0", 1, 30, 0.0001, 6.97,
                    "cm⁻¹", 100.0, hidden=True)],
        insts=[inst("I", "readout", "Blackening under the cross-wire", "I", k=100, unit="%", lc=0.1, digits=1)],
        cols=[col("x", "Head wavelength", "knob:x", "nm", 1e-9, digits=4),
              col("I", "Blackening", "inst:I", "%", 0.01, digits=1)],
        steps=["Lay the spectrogram on the comparator; the iron arc lines beside it calibrate the scale in wavelength.",
               "Find the sharp edge (the head) of each band; the bands fade towards the red.",
               "Read the heads of the (2,0), (1,0), (0,0), (0,1) and (0,2) bands.",
               "Wavenumbers: nu = 1 / lambda. Differences along a row give Delta G(v + 1/2) of the lower state.",
               "omega_e x_e = (Delta G(1/2) - Delta G(3/2)) / 2; omega_e = Delta G(1/2) + 2 omega_e x_e."],
        theory="A diatomic molecule vibrates like an anharmonic oscillator: G(v) = omega_e (v + 1/2) - omega_e x_e "
               "(v + 1/2)^2. An electronic band system is a grid of bands (v', v'') at "
               "nu = T_e + G'(v') - G''(v''). In a Deslandres table rows share v'' and columns share v'; the "
               "difference between neighbouring bands in a column is a vibrational quantum of the lower state, "
               "Delta G''(v + 1/2) = omega_e'' - 2 omega_e''x_e'' (v + 1), and in a row one of the upper state. Two "
               "successive differences give omega_e and omega_e x_e. The heads are taken here as the band origins "
               "(the small rotational shift of a head is left out), and the wavelengths are used as vacuum values.",
        safety="Handle the photographic plate by its edges; the emulsion scratches easily.",
        questions=[_q("Successive vibrational quanta get smaller because", ["the vibration is anharmonic",
                                                                             "the plate shrinks", "the bands fade"],
                      "Delta G(v + 1/2) falls by 2 omega_e x_e per step."),
                   _q("Columns of a Deslandres table share", ["the upper-state v'", "the lower-state v''", "nothing"],
                      "Differences down a column are lower-state quanta.")],
        sources=[SGGU, HH, {"title": "G. Herzberg, Spectra of Diatomic Molecules: the Deslandres table"}],
        parts=[("AlO spectrogram (simulated)", "The blue-green bands of AlO with an iron arc comparison spectrum."),
               ("Comparator", "Calibrated in wavelength from the iron lines."),
               ("Deslandres table", "The band heads arranged by v' and v''.")],
        rows_min=5, hint="Record the five heads named in the procedure.")


# ====================================================================================== scanned spectra
def band_liquid() -> dict:
    return _mk(
        id="po9-band-liquid", title="Band spectrum of a liquid: the absorption bands of potassium permanganate",
        chapter="Molecular spectroscopy",
        aim="Pass white light through a dilute potassium permanganate solution into a spectrometer, scan across "
            "an absorption band, and locate its centre from readings either side of the minimum.",
        kernel="po9_spec", params={"kind": 0.0, "c1": 5.07e-7, "c2": 5.26e-7, "c3": 5.46e-7, "c4": 5.66e-7,
                                   "w": 6.0e-9, "a": 1.0, "tb": 2.0, "gs": 1.0e-9},
        knobs=[knob("x", "Wavelength drum", "x", 380, 800, 0.0001, 520, "nm", 1e-9, digits=4),
               knob("c2", "The band (its centre is hidden)", "c2", 380, 800, 0.0001, 526, "nm", 1e-9, hidden=True)],
        insts=[inst("S", "readout", "Light through the solution", "S", k=100, unit="%", lc=0.001, digits=3)],
        cols=[col("x", "Wavelength", "knob:x", "nm", 1e-9, digits=4),
              col("S", "Transmission", "inst:S", "%", 0.01, digits=3)],
        steps=["Take the white-light spectrum without the cell, then put the cell of solution in the beam.",
               "Scan the drum through the band: the light dips to a minimum.",
               "Read the transmission at the drum setting nearest the minimum and half a band width either side.",
               "The vertex of the parabola through ln(-ln T) at the three settings is the band centre."],
        theory="A coloured solution absorbs in bands. The permanganate ion's broad green absorption is a progression of "
               "vibronic bands, each nearly Gaussian, so the transmission is T = exp(-a sum exp(-((lambda - c) / w)^2)). "
               "For one band, ln(-ln T) is exactly a parabola in lambda, so three readings about the minimum fix its "
               "centre c. Didymium (neodymium and praseodymium) gives much narrower bands from f-f transitions, used "
               "to calibrate spectrometers.",
        safety="Potassium permanganate stains skin and clothes and is an oxidiser: keep the cell closed.",
        questions=[_q("Why does permanganate look purple?", ["It absorbs green light", "It emits purple light",
                                                              "It scatters blue"],
                      "The complement of the absorbed green is purple."),
                   _q("Didymium bands are narrow because", ["they are f-f transitions shielded from the solvent",
                                                             "the solution is dilute", "the lamp is bright"],
                      "The 4f electrons sit inside the ion.")],
        sources=[DU, {"title": "Absorption bands: KMnO4 ~507, 526, 546, 566 nm; didymium (Nd, Pr) ~444, 482, 521, 575 nm",
                      "note": MEMS}],
        parts=[("White lamp and the cell of solution", "The absorber."),
               ("Spectrometer with a wavelength drum", "Scans the spectrum."),
               ("Photocell", "Reads the transmitted light.")],
        rows_min=3, hint="Record three readings about the minimum of the band.")


def uranyl() -> dict:
    return _mk(
        id="po9-uranyl", title="Fluorescence of uranyl nitrate hexahydrate: the vibronic spacing",
        chapter="Molecular spectroscopy",
        aim="Excite uranyl nitrate crystals with violet light, scan the green fluorescence through a monochromator, "
            "locate its vibronic peaks and find their mean spacing in wavenumber.",
        kernel="po9_spec", params={"kind": 1.0, "c1": 4.88e-7, "c2": 5.09e-7, "c3": 5.33e-7, "c4": 5.59e-7,
                                   "c5": 5.87e-7, "w": 4.0e-9, "mode": 1.0, "gs": 1.0e-9},
        knobs=[knob("x", "Monochromator drum", "x", 380, 800, 0.0001, 520, "nm", 1e-9, digits=4),
               knob("c5", "The last band (its peak is hidden)", "c5", 380, 800, 0.0001, 587, "nm", 1e-9, hidden=True)],
        insts=[inst("S", "readout", "Fluorescence", "S", k=100, unit="%", lc=0.001, digits=3)],
        cols=[col("x", "Wavelength", "knob:x", "nm", 1e-9, digits=4),
              col("S", "Fluorescence", "inst:S", "%", 0.01, digits=3)],
        steps=["Light the crystals with a mercury lamp through a violet filter; look at the fluorescence at right "
               "angles through a yellow-green-passing filter.",
               "Scan the monochromator across the emission: a row of peaks appears.",
               "At each peak read the fluorescence at the nearest setting and half a band width either side.",
               "The vertex of the parabola through ln(I) gives each peak; convert to wavenumbers.",
               "Mean spacing = (first - last wavenumber) / (number of peaks - 1)."],
        theory="The uranyl ion O=U=O fluoresces from its lowest excited electronic state into the vibrational ladder "
               "of the ground state. Each peak is one more quantum of the symmetric O=U=O stretch left behind, so "
               "the peaks are nearly equally spaced in wavenumber (about 850 cm-1). Each peak is close to Gaussian, "
               "so ln I is a parabola about it and three readings fix its centre.",
        safety="Uranyl nitrate is radioactive and toxic: keep it in its sealed container and wash your hands after "
               "the practical. The mercury lamp gives ultraviolet: use the filter.",
        questions=[_q("The fluorescence peaks are spaced by", ["a ground-state vibrational quantum",
                                                               "an excited-state quantum", "the spectrometer"],
                      "The emission ends on successive vibrational levels of the ground state."),
                   _q("Fluorescence lies at longer wavelength than the exciting light because",
                      ["energy is lost to vibration first", "the crystal is green", "of the filter"],
                      "The Stokes shift.")],
        sources=[IITK, {"title": "Uranyl nitrate hexahydrate fluorescence peaks ~488, 509, 533, 559, 587 nm",
                        "note": MEMS}],
        parts=[("Mercury lamp and violet filter", "Excite the crystals."),
               ("Uranyl nitrate crystals", "The fluorescing sample."),
               ("Monochromator and photomultiplier", "Scan and read the emission.")],
        rows_min=6, hint="Record three readings about each peak.")


def solar() -> dict:
    return _mk(
        id="po9-solar", title="Fraunhofer lines in sunlight: the sodium D2 line",
        chapter="Atomic spectroscopy",
        aim="Scan the spectrum of sunlight with a calibrated spectrometer, locate a dark Fraunhofer line from "
            "readings about its minimum, and identify the element. SIMULATED DATA: the solar spectrum is drawn by "
            "Hoola from a 5772 K continuum and laboratory line wavelengths.",
        kernel="po9_spec", params={"kind": 2.0, "c1": 5.889950e-7, "c2": 5.895924e-7, "c3": 0.0, "c4": 0.0,
                                   "w": 6.0e-11, "a": 0.7, "tb": 1.0, "gs": 1.0e-11, "Ts": 5772.0, "mode": 2.0},
        knobs=[knob("x", "Wavelength drum", "x", 380, 800, 0.0001, 589, "nm", 1e-9, digits=4),
               knob("c1", "The line (its wavelength is hidden)", "c1", 380, 800, 0.000001, 588.995, "nm", 1e-9,
                    hidden=True)],
        insts=[inst("S", "readout", "Sunlight at the exit slit", "S", k=100, unit="%", lc=0.001, digits=3)],
        cols=[col("x", "Wavelength", "knob:x", "nm", 1e-9, digits=4),
              col("S", "Light", "inst:S", "%", 0.01, digits=3)],
        steps=["Feed sunlight from the heliostat mirror onto the slit (never look at the Sun).",
               "Scan the drum: dark lines cross the bright spectrum.",
               "At the line, read the light at the nearest setting and half a line width either side.",
               "The vertex of the parabola through the three readings is the line's wavelength.",
               "Compare with laboratory wavelengths to name the element."],
        theory="The Sun's photosphere sends out a near-continuous spectrum; cooler gas above it absorbs at the "
               "wavelengths of its atoms' transitions, leaving the dark Fraunhofer lines: Na D at 589.0 and 589.6 nm, "
               "H alpha 656.3 and H beta 486.1 nm, the Mg b triplet near 517-518 nm, Ca II H and K at 396.8 and "
               "393.4 nm. Matching a measured line with laboratory wavelengths identifies the element - which is how "
               "the Sun's composition was first read. Close to its minimum a narrow line is a parabola.",
        safety="NEVER look at the Sun, directly or through any optics. The heliostat feeds the slit; keep your eyes "
               "away from the beam.",
        questions=[_q("Fraunhofer lines are dark because", ["cooler gas above the photosphere absorbs",
                                                             "the Sun has gaps", "the spectrometer blocks them"],
                      "Absorption by atoms in the solar atmosphere."),
                   _q("The two D lines belong to", ["sodium", "hydrogen", "calcium"], "3s - 3p of sodium.")],
        sources=[SGGU, NIST, {"title": "Fraunhofer lines: Na D2 588.995, D1 589.592, H alpha 656.281, H beta 486.133, "
                                       "Mg b1 518.362, Ca II K 393.366 nm", "note": MEMS},
                 {"title": "Solar effective temperature 5772 K (IAU 2015 nominal value)", "note": MEMS}],
        parts=[("Heliostat and slit", "Bring sunlight into the spectrometer."),
               ("Grating spectrometer with a wavelength drum", "Scans the solar spectrum."),
               ("Photocell", "Reads the light at the exit slit.")],
        rows_min=3, hint="Record three readings about the minimum of the line.")


# ====================================================================================== film thickness
def film_thickness() -> dict:
    return _mk(
        id="po9-film-thickness", title="Thickness of an evaporated film by multiple-beam fringes at a step",
        chapter="Thin films",
        aim="Over-coat a film step with silver, face it with a silvered flat, and find the film's thickness from the "
            "shift of the multiple-beam fringes across the step (or from fringes of equal chromatic order).",
        kernel="po9_film", params={"lam": 5.461e-7, "s": 4.0e-4, "F": 60.0, "T0": 2.0e-6},
        knobs=[knob("stage", "Microscope on (0 the bare glass, 1 the film)", "stage", 0, 1, 1, 0),
               knob("x", "Microscope across the fringes", "x", 0, 5, 0.0001, 0.4, "mm", 0.001, digits=4),
               knob("A", "Spectrometer wavelength", "A", 400, 700, 0.0001, 550, "nm", 1e-9, digits=4),
               knob("t", "The film (its thickness is hidden)", "t", 1, 1000, 0.001, 120, "nm", 1e-9, hidden=True)],
        insts=[inst("I", "readout", "Light at the cross-wire", "I", k=100, unit="%", lc=0.1, digits=1)],
        cols=[col("stage", "Region", "knob:stage", digits=0),
              col("x", "Microscope", "knob:x", "mm", 0.001, digits=4),
              col("A", "Wavelength", "knob:A", "nm", 1e-9, digits=4)],
        steps=["Silver the film and the bare glass together, and lay a silvered flat on top with a slight wedge.",
               "Light it with mercury green light: sharp fringes run across the step.",
               "Read two fringes on the bare glass: their distance is the fringe spacing s.",
               "Read the same fringe on the film: its shift as a fraction of s is 2t / lambda.",
               "t = (lambda / 2)(shift / s). With white light and a spectrometer (FECO): t = m (lambda_m - lambda'_m) / 2."],
        theory="Two highly reflecting surfaces close together give sharp multiple-beam fringes wherever 2 G = "
               "m lambda, G the gap. With a small wedge the gap grows by lambda / 2 per fringe spacing s. The film "
               "raises its surface by t, so on the film the gap is t smaller and each fringe shifts by "
               "(2t / lambda) s. In white light seen through a spectrometer the bright bands sit at "
               "lambda_m = 2G / m; their order follows from two neighbours, m = lambda_(m+1) / (lambda_m - "
               "lambda_(m+1)), and the step shifts band m to 2(G - t) / m, so t = m (lambda_m - lambda'_m) / 2. "
               "These are Tolansky's methods, good to a few nanometres.",
        safety=LAMP_SAFE + " Lay the optical flat on gently: a grain of dust between the surfaces ruins the fringes.",
        questions=[_q("Why silver both surfaces?", ["High reflectance makes the fringes sharp", "To protect the film",
                                                     "To conduct heat"],
                      "Multiple-beam fringes narrow as the reflectance rises."),
                   _q("A fringe shift of half the spacing means a step of", ["lambda / 4", "lambda / 2", "lambda"],
                      "t = (lambda / 2)(1/2).")],
        sources=[DU, {"title": "S. Tolansky, Multiple-Beam Interferometry of Surfaces and Films (1948)", "note": MEMS},
                 NIST],
        parts=[("Film step under a silvered flat", "The sample, over-coated with silver."),
               ("Mercury lamp (or white lamp and spectrometer)", "The light."),
               ("Travelling microscope", "Reads the fringe positions.")],
        rows_min=3, hint="Record two fringes on the bare glass and the shifted one on the film.")


def film_strain() -> dict:
    return _mk(
        id="po9-film-strain", title="Residual stress of a film from the curvature of a glass slide",
        chapter="Thin films",
        aim="Measure the radius of curvature of a glass slide before and after coating with Newton's rings against "
            "an optical flat, and get the film's residual stress from Stoney's equation.",
        kernel="po9_stoney", params={"hf": 5.0e-7, "hs": 1.0e-3, "Ms": 9.35e10, "R0": 100.0, "lam": 5.893e-7},
        knobs=[knob("stage", "The slide (0 before coating, 1 after)", "stage", 0, 1, 1, 0),
               knob("x", "Microscope: ring radius", "x", 0, 40, 0.0001, 10, "mm", 0.001, digits=4),
               knob("sig", "The film (its stress is hidden)", "sig", 1, 5000, 0.001, 200, "MPa", 1e6, hidden=True)],
        insts=[inst("I", "readout", "Light at the cross-wire", "I", k=100, unit="%", lc=0.1, digits=1),
               inst("m", "readout", "Dark ring number", "m", lc=1, digits=0)],
        cols=[col("stage", "Slide", "knob:stage", digits=0),
              col("x", "Ring radius", "knob:x", "mm", 0.001, digits=4),
              col("m", "Ring", "inst:m", digits=0)],
        steps=["Lay the optical flat on the uncoated slide and light it with sodium light from above.",
               "Read the radii of dark rings 2, 4 and 6 with the travelling microscope.",
               "r^2 = m R lambda: the slope of r^2 against m is R lambda.",
               "Repeat after the film is deposited.",
               "Stoney: sigma_f = M_s h_s^2 (1 / R1 - 1 / R0) / (6 h_f)."],
        theory="A film under stress bends its substrate. For a thin film on a much thicker plate, Stoney's equation "
               "links the film stress to the change in curvature: sigma_f = M_s h_s^2 (1 / R1 - 1 / R0) / (6 h_f), "
               "with M_s = E / (1 - nu) the substrate's biaxial modulus and h_s, h_f the thicknesses; the film's own "
               "elastic constants drop out. The curvature is read optically: the slide's curved face against an "
               "optical flat makes Newton's rings, dark where r^2 = m R lambda.",
        safety="Glass slides and silicon wafers break into sharp pieces: handle them with tweezers by the edge.",
        questions=[_q("Stoney's equation does not need", ["the film's elastic modulus", "the substrate thickness",
                                                           "the change in curvature"],
                      "Only the substrate's biaxial modulus enters."),
                   _q("A tensile film on top makes the substrate", ["concave on the film side", "convex on the film side",
                                                                     "flat"],
                      "The film pulls its surface in.")],
        sources=[DU, {"title": "G. G. Stoney, Proc. R. Soc. A 82, 172 (1909); substrate data: soda-lime glass E ~72 GPa, "
                               "nu ~0.23; Si(100) biaxial modulus 180.5 GPa (Brantley 1973)", "note": MEMS}],
        parts=[("Coated slide under an optical flat", "The curved face against the flat makes Newton's rings."),
               ("Sodium lamp and glass plate at 45 degrees", "Light from above."),
               ("Travelling microscope", "Reads the ring radii.")],
        rows_min=6, hint="Record rings 2, 4 and 6 before and after coating.")


# ====================================================================================== photometry
def photometry() -> dict:
    return _mk(
        id="po9-photometry", title="Luminous intensity of an incandescent lamp from the inverse square law",
        chapter="Radiometry and photometry",
        aim="Move a lux meter along a photometer bench away from a lamp, read the illuminance at each distance, and "
            "find the lamp's luminous intensity (or check the inverse square law, or the irradiance).",
        kernel="po9_photom", params={"K": 15.0},
        knobs=[knob("x", "Distance from the lamp", "x", 0.2, 1.2, 0.001, 0.5, "m", digits=3),
               knob("Iv", "The lamp (its luminous intensity is hidden)", "Iv", 1, 1000, 0.01, 65, "cd", hidden=True)],
        insts=[inst("E", "readout", "Lux meter", "E", unit="lx", lc=0.1, digits=1),
               inst("Ee", "readout", "Radiometer", "Ee", k=1000, unit="mW/m²", lc=0.1, digits=1)],
        cols=[col("x", "Distance", "knob:x", "m", digits=3),
              col("E", "Illuminance", "inst:E", "lx", digits=1),
              col("Ee", "Irradiance", "inst:Ee", "mW/m²", 0.001, digits=1)],
        steps=["Darken the room; mount the lamp at the zero of the bench with its filament (or centre) on the axis.",
               "Face the lux meter (and the radiometer) square to the lamp.",
               "Read both at 0.3, 0.4, 0.5, 0.6, 0.8 and 1.0 m.",
               "Plot E against 1 / d^2: the slope is the luminous intensity in candela.",
               "ln E against ln d has slope -2 for a point source."],
        theory="A point source of luminous intensity I (candela, lumens per steradian) lights a surface square to it "
               "at distance d with illuminance E = I / d^2 (lux): the inverse square law, because the same flux "
               "spreads over a sphere of area 4 pi d^2. A radiometer reads the irradiance in watts per square metre; "
               "the two are linked by the luminous efficacy of the lamp's radiation K (lumens per watt), "
               "E_e = E / K. An incandescent lamp sends most of its power out as infrared, so its K is small; a "
               "white LED's is large. The law holds only far from the source compared with its size.",
        safety="The lamp gets hot: touch only the stand. Work in a darkened room with a torch for the readings.",
        questions=[_q("Doubling the distance makes the illuminance", ["a quarter", "a half", "unchanged"],
                      "E = I / d^2."),
                   _q("An incandescent lamp's luminous efficacy is low because", ["most of its radiation is infrared",
                                                                                  "it is dim", "it flickers"],
                      "The eye does not see the infrared.")],
        sources=[DU, {"title": "Luminous efficacy of radiation: incandescent ~15 lm/W, white LED ~300 lm/W, compact "
                               "fluorescent ~330 lm/W; the lamps' intensities are hidden values of these lamps",
                      "note": MEMS}],
        parts=[("Lamp on a photometer bench", "The source under test."),
               ("Lux meter on a sliding carriage", "Reads the illuminance."),
               ("Radiometer (thermopile)", "Reads the irradiance.")],
        rows_min=6, hint="Record both meters at each distance.")


# ====================================================================================== acousto-optics
def acousto_optic() -> dict:
    return _mk(
        id="po9-acousto-optic", title="Acousto-optics: speed of ultrasound in water from Raman-Nath diffraction",
        chapter="Acousto-optics",
        aim="Send a laser beam through a water cell carrying a standing ultrasonic wave, measure the positions of the "
            "diffracted orders on a screen, and find the speed of sound (or, in a Bragg cell, the speed and the "
            "drive needed for full efficiency).",
        kernel="po9_ao", params={"f": 1.0e7, "lam": 6.328e-7, "L": 1.0, "nu": 1.5, "P100": 1.0, "ws": 3.0e-4},
        knobs=[knob("x", "Screen cursor from the zero order", "x", 0, 50, 0.001, 0, "mm", 0.001, digits=3),
               knob("A", "Drive power", "A", 0, 10, 0.0001, 0, "W", digits=4),
               knob("v", "The medium (its speed of sound is hidden)", "v", 100, 10000, 0.01, 1497, "m/s", hidden=True),
               knob("P100", "The cell (its full-efficiency drive is hidden)", "P100", 0.05, 10, 0.0001, 1, "W",
                    hidden=True)],
        insts=[inst("I", "readout", "Light at the cursor", "I", k=100, unit="%", lc=0.01, digits=2),
               inst("m", "readout", "Order counted from the centre", "m", lc=1, digits=0),
               inst("eta", "readout", "First order / total", "eta", k=100, unit="%", lc=0.001, digits=3)],
        cols=[col("x", "Distance on the screen", "knob:x", "mm", 0.001, digits=3),
              col("A", "Drive", "knob:A", "W", digits=4),
              col("m", "Order", "inst:m", digits=0),
              col("eta", "Efficiency", "inst:eta", "%", 0.01, digits=3)],
        steps=["Switch on the RF driver at the quartz transducer's frequency; set the cell square to the beam.",
               "A row of spots appears on the screen: the diffracted orders.",
               "Read the distance of each order from the zero order.",
               "sin(theta_m) = m lambda f / v: v = m lambda f / sin(theta_m).",
               "In a Bragg cell, turn it to the Bragg angle (one strong first order) and read its deflection 2 theta_B."],
        theory="An ultrasonic wave of frequency f makes a moving grating of period Lambda = v / f in the medium's "
               "index. In a thin cell (Raman-Nath regime) light is diffracted into many orders at "
               "sin(theta_m) = m lambda / Lambda = m lambda f / v, with intensities J_m^2 of the phase depth. In a "
               "thick cell (Bragg regime) only one order survives, at incidence theta_B with sin theta_B = "
               "lambda f / (2 v); the beam is deflected by 2 theta_B, and the fraction moved into it rises as "
               "eta = sin^2((pi / 2) sqrt(P / P100)) with the drive power P. Acousto-optic cells deflect, shift and "
               "modulate laser beams.",
        safety=LASER_SAFE + " Never run the RF driver into a dry transducer; keep water away from the driver.",
        questions=[_q("Raising the sound frequency makes the orders", ["spread wider", "closer", "dimmer only"],
                      "sin theta_m grows with f."),
                   _q("A thick crystal cell gives only one order because", ["of the Bragg condition", "it absorbs",
                                                                             "the laser is weak"],
                      "Only the order that satisfies the Bragg condition adds in step through the thickness.")],
        sources=[DU, YARIV, HENE,
                 {"title": "Speed of sound: water ~1497 m/s at 25 C; TeO2 longitudinal ~4200 m/s", "note": MEMS}],
        parts=[("He-Ne laser", "632.8 nm."),
               ("Ultrasonic cell with its RF driver", "A water cell or an acousto-optic crystal."),
               ("Screen with a scale (and a power meter)", "Reads the orders and their power.")],
        rows_min=2, hint="Record each diffracted order's position (or the efficiency at each drive).")


# ====================================================================================== ellipsometry
def ellipsometry() -> dict:
    return _mk(
        id="po9-ellipsometry", title="Null ellipsometry: thickness of a silicon dioxide film on silicon",
        chapter="Thin films",
        aim="Reflect He-Ne light off an oxidised silicon wafer at three angles of incidence, find the polariser and "
            "analyser settings that put out the light (null ellipsometry, quarter-wave compensator at 45 degrees), and "
            "get the oxide's thickness (or a metal's optical constants) from Psi and Delta.",
        kernel="po9_ellipso", params={"n1": 1.457, "n2": 3.882, "k2": 0.019, "lam": 6.328e-7},
        knobs=[knob("stage", "Angle of incidence (0: 60, 1: 70, 2: 65 degrees)", "stage", 0, 2, 1, 0),
               knob("x", "Polariser", "x", 0, 180, 0.001, 45, "°", DEG, digits=3),
               knob("A", "Analyser", "A", 0, 180, 0.001, 45, "°", DEG, digits=3),
               knob("d", "The film (its thickness is hidden)", "d", 0, 1000, 0.001, 100, "nm", 1e-9, hidden=True),
               knob("n2", "The reflector (its index is hidden)", "n2", 0.01, 6, 0.0001, 3.882, hidden=True),
               knob("k2", "The reflector (its extinction is hidden)", "k2", 0, 10, 0.0001, 0.019, hidden=True)],
        insts=[inst("I", "readout", "Photodetector", "I", k=100, unit="%", lc=0.0001, digits=4)],
        cols=[col("stage", "Angle of incidence", "knob:stage", digits=0),
              col("x", "Polariser", "knob:x", "°", DEG, digits=3),
              col("A", "Analyser", "knob:A", "°", DEG, digits=3),
              col("I", "Detector", "inst:I", "%", 0.01, digits=4)],
        steps=["Set the arms at the first angle of incidence and centre the reflected beam on the detector.",
               "Null ellipsometry: with the compensator at +45 degrees, turn the polariser and the analyser in turn until "
               "the detector reads its least; read both. Psi = analyser, Delta = 270 degrees - 2 x polariser.",
               "Rotating analyser: polariser at 45 degrees, no compensator; read the detector with the analyser at 0, 45, "
               "90 and 135 degrees: tan Psi = sqrt(I0 / I90), cos Delta = (I45 - I135) / (2 sqrt(I0 I90)).",
               "Repeat at the other angles of incidence.",
               "Film: find the thickness whose computed rho matches the measured one. Metal: eps = sin^2 phi "
               "[1 + tan^2 phi ((1 - rho) / (1 + rho))^2], N = n + i k = sqrt(eps)."],
        theory="On reflection the p and s components of light change amplitude and phase differently; ellipsometry "
               "measures the ratio rho = r_p / r_s = tan(Psi) e^(i Delta). For a bare reflector of complex index N "
               "this inverts directly to N = n + i k. A transparent film of index n1 and thickness d adds the "
               "multiply reflected beams (Airy's sum with phase beta = 2 pi d n1 cos(theta1) / lambda), so rho "
               "depends on d and repeats with the period lambda / (2 sqrt(n1^2 - sin^2 phi)); within one period the "
               "measured rho fixes d to a fraction of a nanometre. In null ellipsometry a polariser and a quarter-wave "
               "compensator make elliptical light that the sample turns exactly plane, so the analyser can put it out: "
               "the null settings give Psi and Delta directly. Several angles of incidence check one another.",
        safety=LASER_SAFE + " Handle the wafer with tweezers by its edge; never touch its polished face.",
        questions=[_q("Ellipsometry measures", ["the ratio r_p / r_s, as Psi and Delta", "the reflectance only",
                                                 "the film's colour"], "Both the amplitude ratio and the phase difference."),
                   _q("Why repeat at several angles?", ["Each angle is an independent check of the same film",
                                                         "The laser drifts", "To heat the sample"],
                      "The same d must fit every angle.")],
        sources=[DU, CUK, BW,
                 {"title": "Optical constants at 632.8 nm: Si 3.882 + 0.019i (Aspnes and Studna 1983), SiO2 1.457, "
                           "gold 0.197 + 3.09i", "note": MEMS},
                 {"title": "R. M. A. Azzam and N. M. Bashara, Ellipsometry and Polarized Light: null and rotating-analyser "
                           "ellipsometry", "note": MEMS}],
        parts=[("He-Ne laser, polariser and quarter-wave compensator", "The input arm."),
               ("Sample on the goniometer table", "Oxidised silicon wafer or a metal film."),
               ("Analyser and photodetector", "The output arm, at the same angle.")],
        rows_min=3, hint="Record the null (or the four analyser readings) at each angle of incidence.")


# ====================================================================================== aerosol spectrometer
def aerosol() -> dict:
    return _mk(
        id="po9-aerosol", title="Aerosol spectrometer: number concentration of particles in room air",
        chapter="Light scattering",
        aim="Sample air through an optical particle counter, read the counts in its eight size channels, and find "
            "the number concentration of particles above 0.3 micrometre (or their median diameter). SIMULATED DATA: "
            "the air's size distribution is a lognormal set by Hoola, not a measured room.",
        kernel="po9_aerosol", params={"Q": 4.717e-5, "t": 60.0, "sg": 2.0},
        knobs=[knob("x", "Size channel", "x", 1, 8, 1, 1, digits=0),
               knob("N", "The air (its particle number is hidden)", "N", 1, 10000, 0.001, 150, "cm⁻³", 1e6,
                    hidden=True),
               knob("cmd", "The air (its median size is hidden)", "cmd", 0.01, 10, 0.0001, 0.6, "µm", 1e-6,
                    hidden=True)],
        insts=[inst("C", "readout", "Counts in the channel (one minute)", "C", lc=1, digits=0)],
        cols=[col("x", "Channel", "knob:x", digits=0),
              col("C", "Counts", "inst:C", digits=0)],
        steps=["Fit the zero filter on the inlet and check the counter reads no particles.",
               "Take the filter off and sample the air for one minute at 2.83 litres per minute.",
               "Read the counts in each channel: 0.3-0.5, 0.5-0.7, 0.7-1, 1-2, 2-3, 3-5, 5-10 and above 10 um.",
               "Number concentration = total counts / (flow x time).",
               "Median diameter: where the cumulative count reaches half, interpolated on a log scale of size."],
        theory="An optical particle counter draws air through a laser beam; each particle crossing it scatters a pulse "
               "of light whose height grows with the particle's size, so the counter sorts the particles into size "
               "channels and counts them. The counts over a known volume (flow Q times time t) give the number "
               "concentration; the counts against size give the size distribution, usually close to lognormal, "
               "dN / d ln D with a count median diameter and a geometric standard deviation. Particles smaller than "
               "the first threshold (0.3 um here) are not counted at all, so both answers refer to the particles "
               "the counter can see.",
        safety="Keep the inlet clear of liquids and never run the counter without its inlet filter cap at hand; the "
               "laser inside is enclosed.",
        questions=[_q("A particle counter sizes particles by", ["the light each one scatters", "their weight",
                                                                 "their charge"], "The pulse height grows with size."),
                   _q("Particles below the first threshold are", ["not counted", "counted in channel 1", "doubled"],
                      "The answers refer only to the particles above 0.3 um.")],
        sources=[SGGU, {"title": "Optical particle counter with 0.3-10 um channels at 2.83 L/min (0.1 cfm): an illustrative "
                                 "instrument; the air's lognormal size distribution is SIMULATED", "note": "unsourced / illustrative"},
                 {"title": "W. C. Hinds, Aerosol Technology (Wiley): lognormal size distributions and optical counters",
                  "note": MEMS}],
        parts=[("Optical particle counter", "Draws the air through a laser beam and sorts the particles by size."),
               ("Inlet and zero filter", "Checks that the counter reads zero on clean air."),
               ("Count display", "Shows the counts in each channel.")],
        rows_min=8, hint="Record the counts in all eight channels.")


BUILDERS = (
    fp_hyperfine, zeeman, ellipse, biref, photoelastic, kerr, pockels, eo_modulation, faraday, magneto_optic,
    laser_2d, laser_slits, cdev, rowland, alo_bands, band_liquid, uranyl, solar, film_thickness, film_strain,
    photometry, acousto_optic, ellipsometry, aerosol,
)
