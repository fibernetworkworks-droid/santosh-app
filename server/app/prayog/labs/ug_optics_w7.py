"""Prayogshala lab pack: the B.Sc. / B.Tech applied-optics bench (wave 7).

ONE studio rig, `app/static/prayog/exp/w7-optics-bench.js`, serves every set-up here: an optical breadboard with a
source, the element under test, a detector with its meter and one or two controls. Each lab is "set the control,
read the detector, record": the settings a careful student records are the kernel's own `plan`, the table is reduced
by the kernel's own `calc`, and the check runs that whole path against the textbook value (within 1 %).

Set-ups of `syllabus/physics/ug.json`:
    tir-gaussian-eyepiece              index of a prism (and of a liquid film) from critical emergence
    wollaston-air-film                 index of a liquid from the two cut-offs of an air film
    nodal-slide-lens-combination       focal length and principal point of two lenses
    fresnel-biprism                    wavelength of sodium light; thickness of a mica sheet
    michelson-fringe-counting          wavelength by fringe counting; index of air
    fabry-perot                        wavelength and finesse
    fourier-transform-spectroscopy     pass band of an interference filter (measured, and transformed on a computer)
    lycopodium-particle-size           particle size from the corona
    telescope-resolving-power          Rayleigh's limit with a slit over the objective
    malus-law                          direction of polarisation, the cosine-squared law, extinction ratio
    babinet-compensator                the polarisation ellipse
    fibre-near-field-profile           index-profile exponent from the near field
    fibre-bending-loss                 loss against bend radius
    fibre-splice-loss                  loss at an offset splice
    fibre-mode-field-diameter          mode field diameter from the far field
    laser-thermal-expansion-quartz     expansion of quartz by fringe counting
    solid-state-laser-characteristics  threshold and slope efficiency of a laser diode
Physics: the `ug_optics_w7` kernel pack (never catalog.py / kernels.py). English only.
"""
from __future__ import annotations

import math

from ..catalog import B, col, inst, knob, lab

DEG = math.pi / 180
RIG = "w7-optics-bench"
GRP = "Physics · Wave Optics"
LVL = "B.Sc. / UG"

SIM = {"title": "Hoola Prayogshala kernel",
       "note": "readings come from the simulation code; checked against the textbook formula in Hoola's tests"}
DU4 = {"title": "University of Delhi LOCF 2019 B.Sc. (Hons.) Physics: Waves and Optics Lab (C-IV)"}
DU13 = {"title": "University of Delhi LOCF 2019 B.Sc. (Hons.) Physics: Electromagnetic Theory Lab (C-XIII)"}
DUSEC = {"title": "University of Delhi LOCF 2019 B.Sc. (Hons.) Physics: SEC Applied Optics Lab"}
IP = {"title": "Indu Prakash and Ram Krishna, A Text Book of Practical Physics (optics section)"}
AICTE = {"title": "AICTE Model Curriculum for Undergraduate Degree Courses in Engineering 2018: engineering physics laboratory"}
NA_D = {"title": "NIST Atomic Spectra Database: sodium D lines 588.995 nm and 589.592 nm (mean 589.3 nm)"}
HENE = {"title": "He-Ne laser red line 632.8 nm (in air)"}
BK7 = {"title": "SCHOTT N-BK7 data sheet: nd = 1.51680"}
BW = {"title": "M. Born and E. Wolf, Principles of Optics: Fresnel's formulae, multiple-beam interference, the "
               "polarisation ellipse, Fraunhofer diffraction at a circular aperture"}
GT = {"title": "A. Ghatak and K. Thyagarajan, Introduction to Fiber Optics (Cambridge): near field, bend and splice "
               "loss, Gaussian approximation of the fundamental mode", "note": "cited from memory - verify the section"}
KEISER = {"title": "G. Keiser, Optical Fiber Communications: Gloge's bend-loss mode count; lateral-offset coupling of "
                   "step-index multimode fibres", "note": "formulae written from memory - verify against the text"}
MEM = "from memory - verify"


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
              "or at a mirror-like reflection of it, take off watches and rings, and switch the laser off before "
              "leaning over the bench.")
LAMP_SAFE = ("A sodium lamp runs hot and takes some minutes to reach full brightness: do not touch the housing and "
             "do not switch it off and on again while it is hot. Handle prisms, plates and lenses by their edges.")
FIBRE_SAFE = ("Never look into the end of a lit fibre: 850 nm and 1310 nm light is invisible and still reaches the "
              "retina. Fibre off-cuts are glass needles; put them in the sharps tin, never on the bench.")


# ====================================================================================== geometrical optics
def tir_gaussian_eyepiece() -> dict:
    return _mk(
        id="tir-gaussian-eyepiece", title="Refractive index by total internal reflection (Gaussian eyepiece)",
        chapter="Geometrical optics and the spectrometer",
        aim="Light a prism at grazing incidence, find the edge of the bright field with the telescope, set the "
            "telescope normal to the face with the Gaussian eyepiece, and get the refractive index from the angle "
            "between the two readings.",
        kernel="w7_tir", params={"x0": 35 * DEG, "x": 35 * DEG},
        knobs=[knob("x", "Telescope reading", "x", 0, 90, 1 / 60, 35, "°", DEG, digits=3),
               knob("n", "This prism (its index is hidden)", "n", 1.3, 1.9, 0.0001, 1.5168, hidden=True),
               knob("nl", "Liquid film on the face (its index is hidden)", "nl", 1.0, 1.7, 0.0001, 1.0, hidden=True)],
        insts=[inst("bright", "readout", "Bright part of the field of view", "bright", k=100, unit="%", lc=1, digits=0),
               inst("refl", "readout", "Reflected cross-wire, away from the cross-wire", "refl", k=60 / DEG, unit="′",
                    lc=1, digits=0)],
        cols=[col("x", "Telescope reading", "knob:x", "°", DEG, digits=3),
              col("refl", "Reflected cross-wire off by", "inst:refl", "′", DEG / 60, digits=0)],
        steps=["Level the spectrometer and focus the telescope for parallel light.",
               "Stand the prism on the table and light one face at grazing incidence with the sodium lamp behind a "
               "ground-glass screen.",
               "Turn the telescope to the other face: the field is bright on one side and dark on the other.",
               "Set the cross-wire on the edge between bright and dark and read the vernier.",
               "Switch on the Gaussian eyepiece and turn the telescope until the reflected image of the cross-wire "
               "falls back on the cross-wire: the telescope is now along the normal to the face. Read the vernier.",
               "The difference of the two readings is the angle of emergence e of the critical ray."],
        theory="The last ray that can enter the prism grazes the first face, so inside the glass it makes the "
               "critical angle with the normal. It meets the second face at A minus that angle and leaves at an "
               "angle e. Rays at smaller incidence all leave on one side of it, so the telescope sees a sharp edge "
               "between a bright and a dark field. Working Snell's law through both faces gives "
               "n squared = 1 + ((sin e + cos A) / sin A) squared. With a film of liquid held on the first face by "
               "a ground-glass plate the grazing ray travels in the liquid, and the same geometry gives the index "
               "of the liquid, n_l = sin A sqrt(n squared - sin squared e) - cos A sin e; e is then negative if the "
               "edge lies on the far side of the normal. The Gaussian eyepiece lights the cross-wire from the side, "
               "so the face itself acts as a mirror and shows when the telescope is square to it.",
        safety=LAMP_SAFE,
        questions=[_q("Why is the field of view half bright and half dark?",
                      ["No ray can enter the prism beyond grazing incidence", "The lamp is too weak",
                       "The telescope is out of focus"], "The grazing ray is the limiting ray; nothing emerges beyond it."),
                   _q("What does the Gaussian eyepiece find?",
                      ["The normal to the prism face", "The angle of the prism", "The wavelength"],
                      "The cross-wire's reflection returns on itself only along the normal.")],
        sources=[DU13, IP, BK7],
        parts=[("Sodium lamp and ground glass", "A broad source, so light reaches the face at every angle up to grazing."),
               ("Prism on the spectrometer table", "Its refractive index is what you have to find."),
               ("Telescope with a Gaussian eyepiece", "Finds the edge of the bright field and the normal to the face.")],
        rows_min=2, hint="Record the telescope reading at the edge of the bright field and again along the normal.")


def wollaston_air_film() -> dict:
    return _mk(
        id="wollaston-air-film", title="Refractive index of a liquid: Wollaston's air film",
        chapter="Geometrical optics and the spectrometer",
        aim="Turn an air film sealed between two glass plates inside a cell of liquid, find the two positions where "
            "the transmitted light is cut off, and get the refractive index of the liquid from the angle between them.",
        kernel="w7_wollaston", params={"x0": 90 * DEG, "x": 90 * DEG},
        knobs=[knob("x", "Turntable reading", "x", 0, 180, 1 / 60, 90, "°", DEG, digits=3),
               knob("n", "The liquid (its index is hidden)", "n", 1.2, 1.7, 0.0001, 1.333, hidden=True)],
        insts=[inst("T", "readout", "Light through the film", "T", k=100, unit="%", lc=0.1, digits=1)],
        cols=[col("x", "Turntable reading at cut-off", "knob:x", "°", DEG, digits=3),
              col("T", "Light through the film", "inst:T", "%", 0.01, digits=1)],
        steps=["Fill the cell with the liquid and stand the air-film plate in it on the turntable.",
               "Send a parallel beam of sodium light through the cell and look at it through the telescope.",
               "Turn the plate one way until the field goes suddenly dark; read the turntable.",
               "Turn it back through the bright position and on until the field goes dark again; read the turntable.",
               "Half the angle between the two readings is the critical angle of the liquid against air."],
        theory="The air film has parallel faces, and so have the glass plates that hold it, so the glass drops out: "
               "what matters is the angle the light makes with the film, measured in the liquid. As the plate is "
               "turned that angle grows until it reaches the critical angle C for liquid against air, "
               "sin C = 1 / n, and the light is totally reflected at the film. The same happens when the plate is "
               "turned the other way, so the two cut-off positions are 2C apart and n = 1 / sin(C). Before cut-off "
               "the film passes most of the light; Fresnel's formulae give the fraction, which falls steeply just "
               "before the critical angle.",
        safety=LAMP_SAFE + " Kerosene is flammable: keep it away from the hot lamp housing and wipe up spills.",
        questions=[_q("Why does the glass of the plates not matter?",
                      ["Its faces are parallel, so it only shifts the ray sideways", "It is very thin",
                       "It has the same index as the liquid"], "n sin(angle) is carried unchanged through parallel layers."),
                   _q("The two cut-off positions are 97.2 degrees apart. The index is",
                      ["1.333", "1.500", "1.250"], "C = 48.6 degrees and 1 / sin(48.6 degrees) = 1.333.")],
        sources=[DU13, IP],
        parts=[("Sodium lamp and collimator", "Gives a parallel beam of yellow light."),
               ("Glass cell of liquid with the air-film plate", "The plate turns with the divided table."),
               ("Telescope", "Shows the field going dark at each cut-off.")],
        rows_min=2, hint="Record the turntable reading at each of the two cut-off positions.")


def nodal_slide() -> dict:
    return _mk(
        id="nodal-slide-lens-combination", title="Focal length of a lens combination with a nodal slide",
        chapter="Geometrical optics and the spectrometer",
        aim="Mount two convex lenses a fixed distance apart on a nodal slide, find the position of the axis for "
            "which turning the slide does not move the image, and read off the equivalent focal length and the "
            "position of the principal point.",
        kernel="w7_nodal", params={},
        knobs=[knob("stage", "Which way round the lens pair faces (0 as set, 1 turned end for end)", "stage", 0, 1, 1, 0),
               knob("x", "Axis in front of the rear lens", "x", 0, 60, 0.5, 20, "mm", 0.001, digits=1),
               knob("f1", "Front lens (its focal length is hidden)", "f1", 5, 50, 0.01, 15, "cm", 0.01, hidden=True),
               knob("f2", "Rear lens (its focal length is hidden)", "f2", 5, 50, 0.01, 20, "cm", 0.01, hidden=True)],
        insts=[inst("shift", "readout", "Image shift when the slide is turned", "shift", k=1000, unit="mm", lc=0.1, digits=1),
               inst("D", "readout", "Axis to screen with the image in focus", "D", k=100, unit="cm", lc=0.1, digits=1)],
        cols=[col("stage", "Way round", "knob:stage", digits=0),
              col("x", "Axis in front of the rear lens", "knob:x", "mm", 0.001, digits=1),
              col("shift", "Image shift", "inst:shift", "mm", 0.001, digits=1),
              col("D", "Axis to screen", "inst:D", "cm", 0.01, digits=1)],
        steps=["Send parallel light from the collimator through the lens pair and focus the image of the cross-slit "
               "on the screen.",
               "Turn the nodal slide a few degrees each way about its vertical axis and watch the image.",
               "Slide the lens pair along the carriage and refocus, until turning the slide no longer moves the image.",
               "The axis now passes through the second nodal point. Read the axis-to-screen distance: it is the "
               "equivalent focal length. Read where the axis stands relative to the rear lens.",
               "Turn the lens pair end for end and repeat for the other nodal point."],
        theory="Two thin lenses of focal lengths f1 and f2 a distance d apart act as one thick lens of focal length "
               "F = f1 f2 / (f1 + f2 - d), measured not from either lens but from the principal points. In air the "
               "nodal points coincide with the principal points, and a ray aimed at the first nodal point leaves "
               "from the second parallel to itself. So if the system is turned about a vertical axis through its "
               "second nodal point, the image of a distant object does not move; about any other axis it swings "
               "sideways. The nodal slide lets you move the lens pair over the axis until the image stays still. "
               "The image is then exactly F from the axis, and the second principal point lies F d / f1 in front "
               "of the rear lens.",
        safety="Handle the lenses by their rims. Clamp the carriage before turning the slide so the lens pair "
               "cannot slip off the bench.",
        questions=[_q("About which point must the lens system be turned for the image to stay still?",
                      ["The second nodal point", "The centre of the rear lens", "The focal point"],
                      "A ray through the nodal points keeps its direction, so the image of a distant object stays put."),
                   _q("Two lenses of 15 cm and 20 cm are 5 cm apart. The equivalent focal length is",
                      ["10 cm", "35 cm", "8.6 cm"], "15 x 20 / (15 + 20 - 5) = 10 cm.")],
        sources=[IP],
        parts=[("Collimator with a cross-slit", "Gives parallel light, as from a distant object."),
               ("Two lenses on the nodal slide", "The carriage slides the lens pair over a vertical axis."),
               ("Screen", "The image is focused on it.")],
        rows_min=2, hint="Record the reading at which turning the slide does not move the image, for both ways round.")


# ====================================================================================== interference
def fresnel_biprism() -> dict:
    return _mk(
        id="fresnel-biprism", title="Fresnel's biprism: wavelength of sodium light",
        chapter="Interference",
        aim="Measure the width of the biprism fringes with a micrometer eyepiece, find the separation of the two "
            "virtual slits by the two-position lens method, and work out the wavelength of sodium light.",
        kernel="w7_biprism", params={},
        knobs=[knob("stage", "On the bench (0 fringes, 1 and 2 lens positions, 3 mica in)", "stage", 0, 3, 1, 0),
               knob("x", "Cross-wire of the micrometer eyepiece", "x", -10, 10, 0.01, 0, "mm", 0.001, digits=2),
               knob("lam", "The lamp (its wavelength is hidden)", "lam", 400, 700, 0.1, 589.3, "nm", 1e-9, hidden=True),
               knob("t", "Mica sheet (its thickness is hidden)", "t", 1, 50, 0.01, 12, "µm", 1e-6, hidden=True)],
        insts=[inst("N", "readout", "Fringes counted from the centre", "N", lc=1, digits=0),
               inst("I", "readout", "Brightness on the cross-wire", "I", k=100, unit="%", lc=1, digits=0)],
        cols=[col("stage", "On the bench", "knob:stage", digits=0),
              col("x", "Cross-wire", "knob:x", "mm", 0.001, digits=2),
              col("N", "Fringe number", "inst:N", digits=0)],
        steps=["Put the slit, the biprism and the micrometer eyepiece on the bench at the same height and make the "
               "slit narrow and parallel to the biprism's edge.",
               "Turn the biprism in its own plane until the fringes are sharp.",
               "Run the cross-wire from the 10th bright fringe on one side to the 10th on the other and read the "
               "micrometer at each: the fringe width is the travel divided by 20.",
               "Put the convex lens between the biprism and the eyepiece. At one position it gives a magnified "
               "image of the two virtual slits; measure their separation d1.",
               "Move the lens to its other position (a diminished image) and measure d2. The real separation is "
               "the square root of d1 d2.",
               "Wavelength = fringe width x d / D, with D the slit-to-eyepiece distance."],
        theory="The biprism bends the light from one slit into two overlapping beams that seem to come from two "
               "virtual slits a small distance d apart. Being images of the same slit they are coherent, and on a "
               "plane a distance D away they give straight fringes of width beta = lambda D / d. The separation d "
               "cannot be measured directly. A convex lens placed between the biprism and the eyepiece forms a real "
               "image of the two slits at two conjugate positions; the image separations d1 and d2 are d times "
               "v / u and d times u / v, so d = sqrt(d1 d2) whatever the lens. A thin transparent sheet of index mu "
               "and thickness t over one beam adds a path (mu - 1) t and moves the whole pattern by "
               "S = (mu - 1) t D / d, that is by (mu - 1) t / lambda fringes; with white light the central fringe "
               "shows where it has gone.",
        safety=LAMP_SAFE,
        questions=[_q("Why are the two virtual slits coherent?",
                      ["They are images of one slit", "They are close together", "Sodium light is yellow"],
                      "Both beams come from the same source slit, so their phases stay locked."),
                   _q("Why is d found from sqrt(d1 d2)?",
                      ["The two magnifications are reciprocals of each other", "To average out errors",
                       "Because the lens is thin"], "At the conjugate positions u and v swap, so the product d1 d2 = d squared.")],
        sources=[DU4, IP, NA_D],
        parts=[("Sodium lamp and slit", "A narrow vertical slit lit by the sodium lamp."),
               ("Biprism", "Splits the light into two overlapping coherent beams."),
               ("Convex lens", "Used at its two conjugate positions to measure the slit separation."),
               ("Micrometer eyepiece", "A cross-wire moved across the fringes by a micrometer screw.")],
        rows_min=3, hint="Record the cross-wire on the 10th fringe each side, then on each slit image at both lens positions.")


def michelson_fringe_counting() -> dict:
    return _mk(
        id="michelson-fringe-counting", title="Michelson interferometer: wavelength by fringe counting",
        chapter="Interference",
        aim="Move one mirror of a Michelson interferometer with its micrometer, count the fringes that cross the "
            "detector, and find the wavelength of the light from the count and the travel.",
        kernel="w7_fringes", params={},
        knobs=[knob("x", "The control (mirror travel in m, pressure in Pa or temperature in °C)", "x", 0, 200000, 1e-8, 0),
               knob("lam", "The source (its wavelength is hidden)", "lam", 400, 700, 0.1, 632.8, "nm", 1e-9, hidden=True),
               knob("dn", "Air at one atmosphere (n - 1 is hidden)", "dn", 1, 5, 0.001, 2.765, "x 1e-4", 1e-4, hidden=True),
               knob("al", "The rod (its expansion coefficient is hidden)", "al", 0.1, 30, 0.01, 0.55, "x 1e-6 / K", 1e-6,
                    hidden=True)],
        insts=[inst("N", "readout", "Fringes counted", "N", lc=1, digits=0),
               inst("I", "readout", "Light on the detector", "I", k=100, unit="%", lc=1, digits=0)],
        cols=[col("x", "Control setting", "knob:x", digits=6),
              col("N", "Fringes counted", "inst:N", digits=0)],
        steps=["Switch the source on and adjust the fixed mirror's screws until circular fringes appear.",
               "Set the fringe counter to zero.",
               "Turn the micrometer slowly in one direction only and count the fringes that pass the centre.",
               "After every 50 fringes read the micrometer.",
               "Plot the count against the mirror travel: each fringe is half a wavelength of travel."],
        theory="The beam splitter sends half the light to each mirror and recombines the two returning beams. Moving "
               "one mirror by x changes the path difference by 2x, so one fringe passes the centre for every half "
               "wavelength of travel: N = 2 x / lambda. Counting N fringes over a measured travel gives the "
               "wavelength. The same count measures anything that changes the optical path in one arm. With a cell "
               "of length L in the arm, letting air in to a pressure P adds 2 L (n - 1) P / P0 to the path, so "
               "n - 1 = N lambda P0 / (2 L P). With a rod of length L0 carrying the mirror, heating it by dT moves "
               "the mirror by alpha L0 dT, so alpha = N lambda / (2 L0 dT).",
        safety=LASER_SAFE + " The mirrors and the beam splitter are front-surface coated: never touch or wipe them.",
        questions=[_q("One fringe passes when the mirror moves by",
                      ["half a wavelength", "one wavelength", "a quarter wavelength"],
                      "The light travels to the mirror and back, so the path changes by twice the travel."),
                   _q("Why turn the micrometer in one direction only?",
                      ["To avoid backlash in the screw", "To keep the laser cool", "To save time"],
                      "Reversing takes up the slack in the thread before the mirror moves.")],
        sources=[DU4, DUSEC, HENE, NA_D],
        parts=[("Source", "A He-Ne laser, or a sodium lamp with a ground-glass screen."),
               ("Beam splitter and two mirrors", "One mirror moves on a fine micrometer screw."),
               ("Detector and fringe counter", "Counts the fringes that cross the centre of the pattern.")],
        rows_min=3, hint="Record the control and the fringe count after each batch of fringes.")


def fabry_perot() -> dict:
    return _mk(
        id="fabry-perot", title="Fabry-Perot interferometer: wavelength and finesse",
        chapter="Interference",
        aim="Change the spacing of a Fabry-Perot interferometer, count the rings that collapse at the centre to "
            "find the wavelength, and scan across two neighbouring maxima to find the finesse.",
        kernel="w7_fabry", params={},
        knobs=[knob("x", "Plate travel", "x", -1, 100, 0.00005, 0, "µm", 1e-6, digits=4),
               knob("lam", "The source (its wavelength is hidden)", "lam", 400, 700, 0.1, 632.8, "nm", 1e-9, hidden=True),
               knob("R", "Mirror coatings (their reflectance is hidden)", "R", 0.5, 0.99, 0.001, 0.9, hidden=True)],
        insts=[inst("N", "readout", "Rings counted", "N", lc=1, digits=0),
               inst("I", "readout", "Light at the centre", "I", k=100, unit="%", lc=0.1, digits=1)],
        cols=[col("x", "Plate travel", "knob:x", "µm", 1e-6, digits=4),
              col("N", "Rings counted", "inst:N", digits=0)],
        steps=["Set the two plates parallel: the rings must not open or close as you move your eye across.",
               "Turn the coarse screw slowly and count the rings that collapse at the centre.",
               "After every 25 rings read the screw.",
               "For the finesse, use the fine (piezo) travel: scan through one maximum and note the two settings "
               "where the light is half its peak.",
               "Go on to the next maximum and do the same.",
               "Finesse = spacing of the two maxima / full width of one maximum at half height."],
        theory="Between two partly silvered plates the light is reflected many times, and the transmitted beams all "
               "add in step only when twice the spacing is a whole number of wavelengths. The transmitted intensity "
               "is Airy's formula, I = 1 / (1 + F sin squared(2 pi d / lambda)) with F = 4R / (1 - R) squared, where "
               "R is the reflectance of each plate. The maxima are a half wavelength of spacing apart, so counting N "
               "of them over a travel x gives lambda = 2 x / N, as in the Michelson. What is new is their sharpness: "
               "the higher R, the narrower each maximum. The finesse is the spacing of neighbouring maxima over "
               "the full width of one at half height, and for good plates it is pi sqrt(R) / (1 - R).",
        safety=LASER_SAFE + " The plates are coated on their inner faces: never let them touch each other.",
        questions=[_q("Raising the reflectance of the plates makes the fringes",
                      ["sharper", "wider apart", "fainter at the peak"],
                      "The finesse pi sqrt(R) / (1 - R) rises steeply with R."),
                   _q("For R = 0.90 the finesse is about", ["30", "9", "90"], "pi x 0.949 / 0.10 = 29.8.")],
        sources=[DUSEC, BW, HENE],
        parts=[("Laser and beam expander", "Fills the plates with light."),
               ("Two coated plates", "One moves along the axis on a coarse screw and a fine piezo."),
               ("Detector at the centre of the rings", "Reads the transmitted light.")],
        rows_min=3, hint="Record the screw after each batch of rings; for the finesse record the four half-height settings.")


def fourier_transform_spectroscopy() -> dict:
    return _mk(
        id="fourier-transform-spectroscopy", title="Fourier transform spectroscopy: pass band of a filter",
        chapter="Interference",
        aim="Pass white light through an interference filter into a Michelson interferometer, record how the fringe "
            "visibility dies away with path difference, and find the width of the filter's pass band.",
        kernel="w7_fts", params={},
        knobs=[knob("stage", "Where you are working (0 the interferometer, 1 the computer)", "stage", 0, 1, 1, 0),
               knob("x", "Path difference (or the wavelength cursor on the computer)", "x", 0, 60, 0.00001, 0, "µm", 1e-6,
                    digits=5),
               knob("lam0", "The filter (its centre wavelength is hidden)", "lam0", 400, 700, 0.1, 550, "nm", 1e-9, hidden=True),
               knob("fwhm", "The filter (its band width is hidden)", "fwhm", 1, 50, 0.01, 10, "nm", 1e-9, hidden=True)],
        insts=[inst("N", "readout", "Fringes from zero path difference", "N", lc=1, digits=0),
               inst("V", "readout", "Fringe visibility", "V", lc=0.01, digits=2),
               inst("T", "readout", "Computed spectrum at the cursor", "T", k=100, unit="%", lc=0.1, digits=1)],
        cols=[col("stage", "Where", "knob:stage", digits=0),
              col("x", "Path difference", "knob:x", "µm", 1e-6, digits=3),
              col("N", "Fringe number", "inst:N", digits=0),
              col("V", "Visibility", "inst:V", digits=2)],
        steps=["Put the interference filter in front of the lamp and find the white-light fringes: they show only "
               "near zero path difference.",
               "Set the mirror at zero path difference, where the fringes are clearest.",
               "Move the mirror in steps of five fringes. At each step read the path difference and the fringe "
               "visibility (Imax - Imin) / (Imax + Imin).",
               "The fringe spacing gives the centre wavelength of the band.",
               "Plot ln(visibility) against the square of the path difference: the slope gives the band width.",
               "On the computer, sample the interferogram and take its Fourier transform to see the band directly."],
        theory="Each wavelength in the light makes its own cosine fringes in a Michelson interferometer, so the "
               "detector signal against path difference x, the interferogram, is the Fourier cosine transform of "
               "the spectrum. A narrow band gives fringes that last over a long path difference; a broad band gives "
               "fringes that die away quickly. For a band that is a Gaussian in wavenumber with standard deviation "
               "s about 1 / lambda0, the interferogram is I(x) = 1/2 [1 + V(x) cos(2 pi x / lambda0)] with "
               "visibility V(x) = exp(-2 pi squared s squared x squared). The fringe period gives lambda0, the "
               "decay of V gives s, and the full width at half height in wavelength is 2.355 s lambda0 squared. "
               "A computer does the same for a band of any shape by transforming the sampled interferogram.",
        safety="The lamp housing gets hot. Interference filters are soft-coated: hold them by the rim. Never touch "
               "the interferometer mirrors.",
        questions=[_q("A narrower pass band gives fringes that",
                      ["last over a longer path difference", "are closer together", "are fainter"],
                      "The coherence length is about lambda squared over the band width."),
                   _q("The interferogram and the spectrum are related by",
                      ["a Fourier transform", "a logarithm", "a derivative"],
                      "Each wavelength contributes one cosine to the interferogram.")],
        sources=[DUSEC, BW],
        parts=[("White lamp and interference filter", "The filter's pass band is what you have to find."),
               ("Michelson interferometer", "One mirror moves on a fine screw to change the path difference."),
               ("Detector and computer", "The computer samples the interferogram and transforms it.")],
        rows_min=3, hint="Record the path difference, the fringe count and the visibility every five fringes.")


# ====================================================================================== diffraction
def lycopodium_particle_size() -> dict:
    return _mk(
        id="lycopodium-particle-size", title="Particle size of lycopodium powder by laser diffraction",
        chapter="Diffraction",
        aim="Send a laser beam through a glass plate dusted with lycopodium powder, measure the radii of the dark "
            "rings of the corona on a screen, and find the mean diameter of the particles.",
        kernel="w7_corona", params={},
        knobs=[knob("x", "Cursor from the centre of the pattern", "x", -80, 80, 0.1, 0, "mm", 0.001, digits=1),
               knob("dia", "The powder (its particle size is hidden)", "dia", 5, 100, 0.01, 32, "µm", 1e-6, hidden=True)],
        insts=[inst("I", "readout", "Brightness on the cursor", "I", k=100, unit="%", lc=0.1, digits=1)],
        cols=[col("x", "Radius of the dark ring", "knob:x", "mm", 0.001, digits=1),
              col("I", "Brightness there", "inst:I", "%", 0.01, digits=1)],
        steps=["Dust a clean glass plate lightly with lycopodium powder and tap off the excess.",
               "Stand the plate in the laser beam, square to it, and put the screen one metre away.",
               "A bright central disc ringed by dark and bright rings appears on the screen.",
               "Run the cursor out to the first dark ring and read its radius; then the second dark ring.",
               "For each ring work out sin(theta) from the radius and the distance, and the diameter from the "
               "ring's constant."],
        theory="Lycopodium spores are nearly equal spheres. By Babinet's principle an opaque disc diffracts light, "
               "away from the forward direction, exactly as a circular hole of the same size does; and because the "
               "particles lie at random the patterns of all of them add in intensity. The screen therefore shows "
               "the Airy pattern of one particle, I = (2 J1(u) / u) squared with u = pi d sin(theta) / lambda. The "
               "dark rings are at the zeros of the Bessel function J1: sin(theta) = 1.220 lambda / d for the first "
               "and 2.233 lambda / d for the second. Measuring a ring's radius r on a screen at distance D gives "
               "theta from tan(theta) = r / D and so the diameter d.",
        safety=LASER_SAFE + " Lycopodium powder is a fine dust that burns fiercely in air: keep it away from "
               "flames, use very little and do not breathe it in.",
        questions=[_q("Why do many particles give the same pattern as one?",
                      ["They are equal and randomly placed, so their intensities add", "They touch each other",
                       "The laser is polarised"], "Random positions wash out the cross terms; only the single-particle pattern is left."),
                   _q("Finer powder gives rings that are", ["larger", "smaller", "the same size"],
                      "sin(theta) is proportional to lambda / d.")],
        sources=[AICTE, BW, HENE,
                 {"title": "Lycopodium clavatum spores: mean diameter about 32 micrometres", "note": MEM}],
        parts=[("Laser", "A low-power laser at bench height."),
               ("Glass plate dusted with lycopodium powder", "The spores are nearly equal spheres."),
               ("Screen with a scale and cursor", "The corona falls on it one metre away.")],
        rows_min=2, hint="Record the radius of the first and of the second dark ring.")


def telescope_resolving_power() -> dict:
    return _mk(
        id="telescope-resolving-power", title="Resolving power of a telescope",
        chapter="Diffraction",
        aim="View two close bright slits through a telescope whose objective is covered by an adjustable slit, "
            "narrow that slit until the two images are just resolved, and compare the resolving power with "
            "Rayleigh's limit.",
        kernel="w7_resolve", params={},
        knobs=[knob("x", "Width of the slit over the objective", "x", 0.1, 5, 0.01, 2.0, "mm", 0.001, digits=2),
               knob("s", "The pair of object slits (their separation is hidden)", "s", 0.5, 5, 0.001, 2.0, "mm", 0.001,
                    hidden=True)],
        insts=[inst("dip", "readout", "Brightness midway between the two images", "dip", k=100, unit="%", lc=0.1, digits=1)],
        cols=[col("x", "Slit width at the limit", "knob:x", "mm", 0.001, digits=2),
              col("dip", "Brightness midway", "inst:dip", "%", 0.01, digits=1)],
        steps=["Light the pair of object slits with the sodium lamp and stand the telescope 3 m away.",
               "Focus the telescope: with the aperture slit wide open the two images are clearly separate.",
               "Narrow the aperture slit slowly. Each image broadens into a diffraction band and the dark gap "
               "between them fills in.",
               "Stop where the two images are just resolved: the brightness midway has risen to 81 % of the peak "
               "(Rayleigh's limit). Read the slit width a.",
               "The least angle resolved is lambda / a, and the resolving power is its reciprocal, a / lambda."],
        theory="Seen through an aperture of width a, a point or line source is not a point in the image but a "
               "diffraction band whose first minimum lies at an angle lambda / a from its centre. Two sources an "
               "angle apart give two such bands. Rayleigh's criterion calls them just resolved when the centre of "
               "one falls on the first minimum of the other; for a slit aperture the brightness midway between "
               "them is then 8 / pi squared = 81 % of the peak. So the least angle a telescope can resolve is "
               "lambda / a (1.22 lambda / a for a round objective), and its resolving power is a / lambda. In this "
               "experiment two slits s apart at a distance D subtend s / D, so at the limit a / lambda = D / s.",
        safety=LAMP_SAFE,
        questions=[_q("Halving the aperture makes the least angle resolved",
                      ["twice as large", "half as large", "no different"], "The limit is lambda / a."),
                   _q("At Rayleigh's limit the centre of one image falls on",
                      ["the first minimum of the other", "the centre of the other", "the second maximum of the other"],
                      "That is the definition of the criterion.")],
        sources=[IP, BW, NA_D],
        parts=[("Sodium lamp and a pair of fine slits", "Two close line sources."),
               ("Adjustable slit with a micrometer", "Covers the telescope objective and sets its aperture."),
               ("Telescope", "Shows the two images merging as the aperture is narrowed.")],
        rows_min=1, hint="Record the slit width at which the two images are just resolved.")


# ====================================================================================== polarisation
def malus_law() -> dict:
    return _mk(
        id="malus-law", title="Malus's law and the polarisation direction of laser light",
        chapter="Polarisation",
        aim="Turn an analyser in the path of polarised light, record the photocurrent at each angle, verify "
            "Malus's cosine-squared law and find the direction of polarisation of the source.",
        kernel="w7_malus", params={"th0": 35 * DEG},
        knobs=[knob("x", "Analyser", "x", 0, 360, 1, 0, "°", DEG, digits=0),
               knob("th0", "The light (its plane of polarisation is hidden)", "th0", 0, 180, 0.01, 35, "°", DEG, hidden=True),
               knob("ext", "Leak through crossed polarisers (hidden)", "ext", 0.00001, 0.1, 0.00001, 0.002, hidden=True)],
        insts=[inst("I", "readout", "Photocurrent", "I", k=1e6, unit="µA", lc=0.01, digits=2)],
        cols=[col("x", "Analyser angle", "knob:x", "°", DEG, digits=0),
              col("I", "Photocurrent", "inst:I", "µA", 1e-6, digits=2)],
        steps=["Send the polarised beam through the analyser on to the photodiode.",
               "Set the analyser to 0 degrees and read the photocurrent.",
               "Turn the analyser in 20 degree steps up to 160 degrees, reading the photocurrent each time.",
               "The angle of greatest current is the direction of polarisation of the light.",
               "Plot the current against cos squared of the angle from that direction: Malus's law gives a "
               "straight line."],
        theory="A polariser passes only the component of the electric field along its axis. If plane-polarised "
               "light of intensity I0 meets an analyser whose axis makes an angle theta with the field, the "
               "transmitted amplitude is the field times cos(theta), and the intensity is I0 cos squared(theta): "
               "Malus's law. The current is greatest when the analyser lies along the field and, ideally, zero "
               "when it is crossed; a real polariser and a real laser leave a small leak, and the ratio of the "
               "greatest to the least current is the extinction ratio. Because the law has a period of 180 degrees, "
               "readings spread evenly over half a turn fix the direction of polarisation, not just the single "
               "largest reading.",
        safety=LASER_SAFE + " Each polariser reflects part of the beam: check where the reflections go.",
        questions=[_q("The analyser is turned 60 degrees from the direction of polarisation. The intensity is",
                      ["a quarter of the maximum", "half the maximum", "three quarters of the maximum"],
                      "cos squared(60 degrees) = 1/4."),
                   _q("Why do crossed polarisers not give exactly zero?",
                      ["Real polarisers leak a little of the other component", "The photodiode is slow",
                       "Malus's law fails at 90 degrees"], "The leak sets the extinction ratio.")],
        sources=[DU13, DUSEC, BW],
        parts=[("Laser, or a lamp with a polariser", "The source of plane-polarised light."),
               ("Analyser in a divided rotary mount", "Turned through known angles."),
               ("Photodiode and microammeter", "Reads the transmitted light.")],
        rows_min=3, hint="Record the photocurrent every 20 degrees from 0 to 160 degrees.")


def babinet_compensator() -> dict:
    return _mk(
        id="babinet-compensator", title="Elliptically polarised light with a Babinet compensator",
        chapter="Polarisation",
        aim="Calibrate a Babinet compensator with plane-polarised light, then use the shift of its dark fringe and "
            "the analyser setting that makes the fringe black to find the shape and tilt of an ellipse of "
            "polarisation.",
        kernel="w7_babinet", params={"psi": 30 * DEG, "del": 60 * DEG, "A": 135 * DEG},
        knobs=[knob("stage", "The light (0 plane-polarised for calibration, 1 the light under test)", "stage", 0, 1, 1, 0),
               knob("A", "Analyser", "A", 0, 180, 0.1, 135, "°", DEG, digits=1),
               knob("x", "Compensator micrometer", "x", 0, 5, 0.005, 0, "mm", 0.001, digits=3),
               knob("psi", "The light under test (its amplitude ratio is hidden)", "psi", 5, 85, 0.01, 30, "°", DEG, hidden=True),
               knob("del", "The light under test (its phase difference is hidden)", "del", 5, 175, 0.01, 60, "°", DEG,
                    hidden=True)],
        insts=[inst("I", "readout", "Brightness on the cross-wire", "I", k=100, unit="%", lc=0.1, digits=1)],
        cols=[col("stage", "Light", "knob:stage", digits=0),
              col("A", "Analyser", "knob:A", "°", DEG, digits=1),
              col("x", "Micrometer", "knob:x", "mm", 0.001, digits=3)],
        steps=["Send plane-polarised light at 45 degrees to the compensator's axes through it, with the analyser "
               "crossed: straight dark fringes appear.",
               "Set a dark fringe on the cross-wire and read the micrometer; move to the next dark fringe and read "
               "again. The difference is the travel for a phase of 2 pi.",
               "Put in the light under test (here made with a quarter-wave plate). The dark fringe has moved: bring "
               "it back to the cross-wire and read the micrometer.",
               "The fringe is now grey, not black. Turn the analyser until it is perfectly black and read the "
               "analyser.",
               "The fringe shift gives the phase difference, the analyser angle gives the amplitude ratio; the "
               "ellipse follows from the two."],
        theory="A Babinet compensator is two thin quartz wedges with crossed optic axes. Along its length the phase "
               "difference it adds between the two field components changes steadily, by 2 pi over a travel beta. "
               "With plane-polarised light at 45 degrees and a crossed analyser the dark fringes mark the places "
               "where the added phase is a whole number of turns. Elliptically polarised light already has a phase "
               "difference delta between its components, so the dark fringe moves by delta beta / 2 pi; that "
               "measures delta. Where the compensator has cancelled delta the light is plane-polarised again, in a "
               "direction set by the amplitude ratio tan(psi), and the analyser crossed to it (at 90 degrees + psi) "
               "makes the fringe black. The ellipse then follows: sin 2 chi = sin 2 psi sin delta gives the ratio "
               "of its axes, tan(chi), and tan 2 alpha = tan 2 psi cos delta gives the tilt alpha of its major axis.",
        safety=LAMP_SAFE + " The quartz wedges are thin and unmounted at the edges: turn the micrometer gently and "
               "never force it past its stops.",
        questions=[_q("The dark fringe shifts by a quarter of the fringe spacing. The phase difference is",
                      ["90 degrees", "45 degrees", "180 degrees"], "A full spacing is 360 degrees."),
                   _q("Why does the fringe go fully black only at one analyser angle?",
                      ["The two components have unequal amplitudes", "The lamp flickers", "Quartz absorbs light"],
                      "The analyser must be crossed to the plane-polarised light left after compensation.")],
        sources=[DU13, BW, IP],
        parts=[("Sodium lamp and polariser", "Gives plane-polarised light."),
               ("Quarter-wave plate", "Turns the plane-polarised light into the elliptical light under test."),
               ("Babinet compensator", "Two quartz wedges moved by a micrometer."),
               ("Analyser and eyepiece", "The analyser turns in a divided circle.")],
        rows_min=4, hint="Record two neighbouring dark fringes for calibration, then the shifted fringe and the analyser at black.")


# ====================================================================================== fibre optics and lasers
def fibre_near_field_profile() -> dict:
    return _mk(
        id="fibre-near-field-profile", title="Near-field intensity and index profile of a multimode fibre",
        chapter="Lasers, fibre optics and applied optics",
        aim="Image the lit end face of a multimode fibre with a microscope objective, scan a small detector across "
            "the image, and find the exponent of the fibre's refractive-index profile from the near-field intensity.",
        kernel="w7_nearfield", params={},
        knobs=[knob("x", "Detector across the image", "x", -12, 12, 0.1, 0, "mm", 0.001, digits=1),
               knob("g", "The fibre (its profile exponent is hidden)", "g", 1, 20, 0.01, 2, hidden=True)],
        insts=[inst("P", "readout", "Power on the detector", "P", k=1e9, unit="nW", lc=1, digits=0)],
        cols=[col("x", "Detector position", "knob:x", "mm", 0.001, digits=1),
              col("P", "Power", "inst:P", "nW", 1e-9, digits=0)],
        steps=["Launch light from the LED into the fibre so that it fills the whole core (overfilled launch).",
               "Cleave the far end, clamp it, and image the end face on to the detector plane with the x400 objective.",
               "Centre the pinhole detector on the image and read the power.",
               "Move the detector outwards in steps and read the power each time, out to nine tenths of the core radius.",
               "For each reading work out r / a and 1 - I / I0, and plot one against the other on log scales: the "
               "slope is the profile exponent g."],
        theory="A multimode fibre guides, at a distance r from its axis, only the rays inside the local acceptance "
               "cone, whose size is set by n squared(r) - n2 squared. If every mode carries the same power (an "
               "overfilled launch, with leaky modes neglected) the intensity across the end face, the near field, "
               "is proportional to that quantity. For the usual power-law profile "
               "n squared(r) = n1 squared [1 - 2 Delta (r / a) to the power g], this gives "
               "I(r) / I(0) = 1 - (r / a) to the power g. So the near field is a direct picture of the index "
               "profile: g = 2 is the parabolic profile of a graded-index fibre, and a large g is close to a step.",
        safety=FIBRE_SAFE,
        questions=[_q("A step-index fibre has a near field that is", ["flat across the core", "parabolic", "a narrow spike"],
                      "A step is the limit of large g, where 1 - (r / a) to the power g stays near 1."),
                   _q("Why must the launch fill all the modes?",
                      ["Only then does the intensity follow the local numerical aperture", "To make the fibre brighter",
                       "To avoid heating the core"], "The relation assumes equal power in every mode.")],
        sources=[DUSEC, GT,
                 {"title": "F. M. E. Sladen, D. N. Payne and M. J. Adams, Appl. Phys. Lett. 28, 255 (1976): near-field "
                           "scanning of fibre index profiles", "note": MEM},
                 {"title": "50/125 micrometre graded-index multimode fibre: core radius 25 micrometres (ITU-T G.651.1)"}],
        parts=[("LED source", "Launches light into every mode of the fibre."),
               ("Multimode fibre", "Its index profile is what you have to find."),
               ("Microscope objective", "Magnifies the end face 400 times."),
               ("Pinhole detector on a translation stage", "Scans across the magnified image.")],
        rows_min=4, hint="Record the power at the centre and at several positions out to nine tenths of the core radius.")


def fibre_bending_loss() -> dict:
    return _mk(
        id="fibre-bending-loss", title="Bending loss in a multimode fibre",
        chapter="Lasers, fibre optics and applied optics",
        aim="Wind one turn of a multimode fibre on mandrels of smaller and smaller radius, measure the power that "
            "still comes through, and see how the loss grows as the bend tightens.",
        kernel="w7_bend", params={},
        knobs=[knob("stage", "The fibre (0 laid straight, 1 one turn on the mandrel)", "stage", 0, 1, 1, 0),
               knob("x", "Mandrel radius", "x", 4, 40, 1, 30, "mm", 0.001, digits=0),
               knob("Dl", "The fibre (its index difference is hidden)", "Dl", 0.2, 3, 0.001, 1, "%", 0.01, hidden=True)],
        insts=[inst("P", "readout", "Power out of the fibre", "P", k=1e6, unit="µW", lc=0.01, digits=2),
               inst("dB", "readout", "Loss on the bend", "dB", unit="dB", lc=0.01, digits=2)],
        cols=[col("stage", "Fibre", "knob:stage", digits=0),
              col("x", "Mandrel radius", "knob:x", "mm", 0.001, digits=0),
              col("P", "Power out", "inst:P", "µW", 1e-6, digits=2)],
        steps=["Launch light into the fibre and lay it straight on the bench. Read the power at the far end: this "
               "is the reference.",
               "Wind one full turn of the fibre round the 30 mm mandrel and read the power again.",
               "Repeat on the 20, 12, 8 and 6 mm mandrels.",
               "Loss in decibels = 10 log10(reference power / power on the bend).",
               "Plot the loss against the bend radius."],
        theory="On a bend the outer side of each guided wave would have to travel faster than light in the cladding "
               "to keep up, so the highest modes leak away. Gloge counted the modes a step-index fibre of core "
               "radius a still guides on a bend of radius R: the guided fraction is "
               "1 - [2a / R + (3 / (2 n2 k R)) to the power 2/3] / (2 Delta), with k = 2 pi / lambda and Delta the "
               "relative index difference between core and cladding. With the power shared equally among the "
               "modes, that fraction is also the fraction of the power that gets through. The loss therefore rises "
               "slowly at first and then steeply as R falls towards a few millimetres, and a fibre with a larger "
               "Delta holds its light better round the same bend.",
        safety=FIBRE_SAFE + " Do not bend a glass fibre tighter than the smallest mandrel: it snaps without warning.",
        questions=[_q("Which fibre loses less light on the same bend?",
                      ["The one with the larger index difference", "The one with the larger core", "The longer one"],
                      "The lost fraction is inversely proportional to Delta."),
                   _q("Why do the highest modes leak first?",
                      ["They travel closest to the critical angle", "They are the brightest", "They are in the centre of the core"],
                      "A small extra tilt at the bend takes them past the critical angle.")],
        sources=[DUSEC, KEISER,
                 {"title": "D. Gloge, Appl. Opt. 11, 2506 (1972): bending loss in multimode fibres with graded and "
                           "ungraded core index", "note": MEM}],
        parts=[("850 nm source", "Launches light into the fibre."),
               ("Multimode fibre and a set of mandrels", "One turn is wound on each mandrel in turn."),
               ("Optical power meter", "Reads the power at the far end.")],
        rows_min=4, hint="Record the power with the fibre straight, then with one turn on each mandrel.")


def fibre_splice_loss() -> dict:
    return _mk(
        id="fibre-splice-loss", title="Power loss at a splice between two multimode fibres",
        chapter="Lasers, fibre optics and applied optics",
        aim="Measure the power through an unbroken multimode fibre and again with a mechanical splice in it, and "
            "find the loss the splice causes in decibels.",
        kernel="w7_splice", params={},
        knobs=[knob("stage", "The fibre (0 unbroken reference, 1 with the splice in it)", "stage", 0, 1, 1, 0),
               knob("off", "The splice (its sideways offset is hidden)", "off", 0, 40, 0.01, 10, "µm", 1e-6, hidden=True)],
        insts=[inst("P", "readout", "Power out of the fibre", "P", k=1e6, unit="µW", lc=0.01, digits=2)],
        cols=[col("stage", "Fibre", "knob:stage", digits=0),
              col("P", "Power out", "inst:P", "µW", 1e-6, digits=2)],
        steps=["Launch light into the unbroken reference fibre and read the power at its far end.",
               "Without disturbing the launch, replace it by the fibre that has the mechanical splice in it.",
               "Read the power again.",
               "Splice loss in decibels = 10 log10(reference power / power through the splice)."],
        theory="At a splice the two cores must face each other exactly. If they are displaced sideways by d, only "
               "the light that falls on the area common to both cores is caught by the second fibre. For two equal "
               "step-index fibres of core radius a, with the power spread evenly over the modes, the coupled "
               "fraction is that common area over the core area: "
               "eta = (2 / pi) [acos(u) - u sqrt(1 - u squared)], with u = d / 2a. The splice loss is "
               "-10 log10(eta) decibels. A gap between the ends, a tilt, or a mismatch of core size or numerical "
               "aperture adds further loss; an index-matching gel removes the Fresnel reflection at the two faces.",
        safety=FIBRE_SAFE,
        questions=[_q("An offset of one fifth of the core diameter costs about",
                      ["1.3 dB", "0.1 dB", "6 dB"], "u = 0.2 gives eta = 0.75, and -10 log10(0.75) = 1.27 dB."),
                   _q("Why is an index-matching gel used in a mechanical splice?",
                      ["To remove the reflection at the two glass-air faces", "To glue the fibres", "To cool the splice"],
                      "Each glass-air face would otherwise reflect about 4 % of the light.")],
        sources=[DUSEC, KEISER, GT,
                 {"title": "50/125 micrometre multimode fibre: core radius 25 micrometres (ITU-T G.651.1)"}],
        parts=[("850 nm source", "Launches light into the fibre."),
               ("Mechanical splice", "Two cleaved ends butted in a V-groove; the offset between the cores is unknown."),
               ("Optical power meter", "Reads the power at the far end.")],
        rows_min=2, hint="Record the power through the reference fibre and through the spliced fibre.")


def fibre_mode_field_diameter() -> dict:
    return _mk(
        id="fibre-mode-field-diameter", title="Mode field diameter of a single-mode fibre from its far field",
        chapter="Lasers, fibre optics and applied optics",
        aim="Swing a detector on an arm round the end of a single-mode fibre, record how the power falls with "
            "angle, and find the mode field diameter from the width of the far field.",
        kernel="w7_mfd", params={},
        knobs=[knob("x", "Angle of the detector arm", "x", -12, 12, 0.1, 0, "°", DEG, digits=1),
               knob("w0", "The fibre (its spot size is hidden)", "w0", 2, 8, 0.001, 4.6, "µm", 1e-6, hidden=True)],
        insts=[inst("P", "readout", "Power on the detector", "P", k=1e9, unit="nW", lc=0.1, digits=1)],
        cols=[col("x", "Arm angle", "knob:x", "°", DEG, digits=1),
              col("P", "Power", "inst:P", "nW", 1e-9, digits=1)],
        steps=["Launch the 1310 nm source into the fibre and strip the cladding modes with a few small loops.",
               "Clamp the cleaved far end at the centre of the goniometer.",
               "Set the arm at 0 degrees and read the power.",
               "Swing the arm in 1.5 degree steps out to 6 degrees, reading the power each time.",
               "Plot ln(power) against the square of the angle: a straight line of slope -2 / theta0 squared.",
               "Mode field diameter = 2 lambda / (pi theta0)."],
        theory="The one mode a single-mode fibre carries is very nearly a Gaussian beam of spot size w0, and the "
               "mode field diameter is 2 w0: it is this, not the core diameter, that fixes splice loss and bend "
               "sensitivity. Leaving the fibre the Gaussian spreads by diffraction, and far from the end its "
               "intensity falls with angle as P(theta) = P0 exp(-2 theta squared / theta0 squared), where "
               "theta0 = lambda / (pi w0) is the angle at which the intensity is 1 / e squared of its peak. "
               "Measuring that width gives the spot size without any microscope: the smaller the mode, the wider "
               "it spreads.",
        safety=FIBRE_SAFE,
        questions=[_q("A fibre with a smaller mode field diameter has a far field that is",
                      ["wider", "narrower", "the same"], "theta0 = lambda / (pi w0)."),
                   _q("Why strip the cladding modes first?",
                      ["They would add stray light to the far field", "They heat the fibre", "They change the wavelength"],
                      "Only the guided mode should reach the detector.")],
        sources=[DUSEC, GT,
                 {"title": "Standard single-mode fibre (ITU-T G.652 type): mode field diameter 9.2 micrometres at 1310 nm",
                  "note": MEM}],
        parts=[("1310 nm laser source", "Launches light into the fibre."),
               ("Single-mode fibre with its end at the pivot", "Its mode field diameter is what you have to find."),
               ("Detector on a goniometer arm", "Swings round the fibre end."),
               ("Optical power meter", "Reads the power on the detector.")],
        rows_min=3, hint="Record the power every 1.5 degrees from 0 to 6 degrees.")


def laser_thermal_expansion_quartz() -> dict:
    d = michelson_fringe_counting()
    d.update(
        id="laser-thermal-expansion-quartz", title="Thermal expansion of quartz using a laser",
        topic="Lasers, fibre optics and applied optics", chapter="Lasers, fibre optics and applied optics",
        aim="Heat a quartz rod that carries one mirror of a laser interferometer, count the fringes that pass as "
            "it warms, and find its coefficient of linear expansion.",
        params={"mode": 2.0, "x": 25.0},
        steps=["Stand the quartz rod in the tube furnace with the small mirror on its free end, in one arm of the "
               "interferometer.",
               "Switch the laser on, get fringes on the detector and set the counter to zero at room temperature.",
               "Raise the temperature slowly so that the rod stays at the furnace temperature.",
               "Each time five more fringes have passed, read the thermometer.",
               "Plot the fringe count against temperature: the slope is 2 alpha L0 / lambda."],
        safety=LASER_SAFE + " The furnace tube and the rod stay hot long after the heater is off: do not touch them.",
        questions=[_q("Why can a laser measure so small an expansion?",
                      ["One fringe is only half a wavelength of movement", "The laser heats the rod",
                       "Quartz is transparent"], "Half of 633 nm is about 0.3 micrometres per fringe."),
                   _q("Fused quartz is used for precise optical parts because",
                      ["it hardly expands on heating", "it is cheap", "it is soft"],
                      "Its expansion coefficient is about twenty times smaller than that of ordinary glass.")],
        sources=[DUSEC, HENE,
                 {"title": "Fused quartz (vitreous silica): linear expansion coefficient about 0.55 x 10^-6 per kelvin "
                           "near room temperature", "note": MEM}, SIM],
        bodies=_bodies(("He-Ne laser", "The light source of the interferometer."),
                       ("Quartz rod in a tube furnace", "The rod carries one mirror on its free end."),
                       ("Detector and fringe counter", "Counts the fringes as the rod grows.")),
    )
    d["knobs"][0]["value"] = 25
    d["table"]["hint"] = "Read the thermometer each time five more fringes have passed."
    return d


def solid_state_laser_characteristics() -> dict:
    return _mk(
        id="solid-state-laser-characteristics", title="Characteristics of a solid-state (diode) laser",
        chapter="Lasers, fibre optics and applied optics",
        aim="Raise the drive current of a laser diode in steps, record the light output at each, and find the "
            "threshold current and the slope efficiency from the light-current curve.",
        kernel="w7_ld", params={},
        knobs=[knob("x", "Drive current", "x", 0, 40, 0.1, 0, "mA", 0.001, digits=1),
               knob("Ith", "The diode (its threshold is hidden)", "Ith", 5, 80, 0.01, 20, "mA", 0.001, hidden=True),
               knob("eta", "The diode (its slope efficiency is hidden)", "eta", 0.05, 1.5, 0.001, 0.5, "W/A", hidden=True)],
        insts=[inst("P", "readout", "Optical power", "P", k=1000, unit="mW", lc=0.001, digits=3)],
        cols=[col("x", "Drive current", "knob:x", "mA", 0.001, digits=1),
              col("P", "Optical power", "inst:P", "mW", 0.001, digits=3)],
        steps=["Mount the laser diode facing the power-meter head and set the current limit on the driver.",
               "Raise the current from zero in steps and read the optical power at each step.",
               "Below threshold the output is weak and rises slowly: the diode is only an LED.",
               "Above threshold the output rises steeply and in a straight line.",
               "Draw a straight line through the points below threshold and another through those above: they "
               "meet at the threshold current. The slope of the upper line is the slope efficiency."],
        theory="A laser diode is a forward-biased junction between two mirrors. At low current the injected "
               "carriers recombine at random and the junction glows weakly like an LED. As the current rises the "
               "gain grows until, at the threshold current, it just balances the loss through the mirrors and in "
               "the material. Beyond that almost every extra carrier adds a photon to the laser mode, so the "
               "output rises in a straight line, P = eta (I - Ith). The slope eta, in watts per ampere, is the "
               "slope efficiency. The threshold is read from the light-current curve as the point where the two "
               "straight parts meet. Both numbers drift with temperature, which is why the diode sits on a "
               "temperature-controlled mount.",
        safety="Laser diodes are destroyed in an instant by too much current or by static: set the current limit "
               "first and earth yourself. The beam diverges widely but is still a laser beam: never look into the "
               "diode, and keep the power-meter head in front of it.",
        questions=[_q("Below threshold the diode", ["emits weakly, like an LED", "emits nothing", "lases in pulses"],
                      "Spontaneous emission is present at any forward current."),
                   _q("The slope efficiency is the", ["extra light per extra ampere above threshold",
                                                       "light at threshold", "voltage across the diode"],
                      "It is the gradient of the straight upper part of the curve.")],
        sources=[DUSEC,
                 {"title": "Laser diode under test: threshold 20 mA and slope 0.5 W/A are illustrative values for a "
                           "5 mW 650 nm index-guided diode, not a named part", "note": "unsourced / illustrative"}],
        parts=[("Laser-diode current driver", "A constant-current source with a fine control and a current limit."),
               ("Laser diode on a mount", "Its threshold and slope efficiency are what you have to find."),
               ("Power-meter head and meter", "Reads the optical power.")],
        rows_min=7, hint="Record the power at three currents below threshold and four above it.")


BUILDERS = (
    tir_gaussian_eyepiece, wollaston_air_film, nodal_slide, fresnel_biprism, michelson_fringe_counting, fabry_perot,
    fourier_transform_spectroscopy, lycopodium_particle_size, telescope_resolving_power, malus_law,
    babinet_compensator, fibre_near_field_profile, fibre_bending_loss, fibre_splice_loss, fibre_mode_field_diameter,
    laser_thermal_expansion_quartz, solid_state_laser_characteristics,
)
