"""Prayogshala lab pack: UNDERGRADUATE WAVE OPTICS - the B.Sc. optics practicals, on four real benches.

Thirteen set-ups, grouped by the apparatus they are actually done on, so one rig serves a whole bench:

    spectrometer-bench   a prism spectrometer (collimator, prism table, telescope, divided circle with two verniers):
                         the angle of the prism, the refractive index by minimum deviation, the dispersive power and
                         Cauchy constants from the mercury lines, and a plane transmission grating on the same table
                         for wavelength, dispersive power and resolving power.
    interference-bench   a travelling microscope over a glass plate: Newton's rings, and the air wedge between two
                         flats held apart by a spacer.
    laser-bench          a low-power laser, a slide holder and a screen: the double slit, a grating, the track
                         spacing of a compact disc and the numerical aperture of a fibre.
    polar-bench          a polariser, an analyser on a divided circle and a photocell: Brewster's angle, and the
                         specific rotation of a sugar solution in a half-shade polarimeter.

Every reading comes from this area's own kernels (`packs/optics_ug.py`), and every lab carries its own check: the
kernel's simulated reading against the textbook formula, within 1 %.
"""
from __future__ import annotations

import math

from ..catalog import B, col, inst, knob, lab

DEG = math.pi / 180
R2D = 180 / math.pi
GRP = "Physics · Wave Optics"
LVL = "B.Sc. / UG"

SIM = {"title": "Hoola Prayogshala kernel",
       "note": "readings come from the simulation code; checked against the textbook formula in Hoola's tests"}
DU = {"title": "University of Delhi LOCF 2019 B.Sc. (Hons.) Physics: Waves and Optics Lab (C-IV) and "
               "Electromagnetic Theory Lab (C-XIII)"}
IP = {"title": "Indu Prakash and Ram Krishna, A Text Book of Practical Physics (optics section)"}
SUBRA = {"title": "C. L. Arora, B.Sc. Practical Physics - spectrometer, interferometry and polarimetry"}
NA_D = {"title": "NIST Atomic Spectra Database: sodium D lines 588.995 nm and 589.592 nm (mean 589.3 nm)"}
HG = {"title": "NIST Atomic Spectra Database: mercury lines 404.656, 435.833, 546.074, 576.960 and 579.066 nm"}
HENE = {"title": "He-Ne laser red line 632.8 nm (vacuum wavelength 632.991 nm; ISO 11146 / NIST)"}
BK7 = {"title": "SCHOTT N-BK7 data sheet: nF = 1.52238 (486.13 nm), nd = 1.51680, nC = 1.51432 (656.27 nm); "
                "the two-term Cauchy constants here are fitted to that nF and nC"}
GRAT15 = {"title": "Plane transmission grating ruled 15 000 lines per inch, so d = 25.4 mm / 15 000 = 1.6933 um"}
GRAT300 = {"title": "Plane transmission grating ruled 300 lines per mm, so d = 3.3333 um"}
CD = {"title": "ECMA-130 (Compact Disc Read Only Memory): track pitch 1.6 um"}
POF = {"title": "Step-index plastic optical fibre: PMMA core n1 = 1.492, fluorinated polymer cladding n2 = 1.402, "
                "so NA = 0.51 (Mitsubishi Eska and Toray PFU data sheets)"}
SUGAR = {"title": "Specific rotation of sucrose at the sodium D line, 20 C: [alpha] = +66.5 degrees per dm per g/mL "
                  "(CRC Handbook of Chemistry and Physics; IUPAC)"}


def _bench(x=0.0, w=1.1, d=0.6):
    return B("bench", "box", name="Laboratory bench", size=[w, 0.02, d], pos=[x, -0.02, 0], color="wood", cut=False)


# ====================================================================================== the prism spectrometer bench
def spectrometer_prism_angle() -> dict:
    return lab(
        id="spectrometer-prism-angle", rig="spectrometer-bench",
        title="Spectrometer: adjustment and the angle of a prism", group=GRP, level=LVL,
        topic="Geometrical optics and the spectrometer", chapter="Geometrical optics and the spectrometer",
        aim="Set the spectrometer for parallel light by Schuster's method, then measure the refracting angle A of a "
            "prism from the two beams reflected off its polished faces.",
        kernel="spectrometer", params={"A": 1.0471976}, autorun=True,
        camera={"pos": [0.0, 0.55, 0.95], "look": [0.0, 0.03, 0.0]}, floor=-0.2,
        bodies=[
            _bench(),
            B("circle", "cylinder", name="Divided circle", info="The main scale, half a degree to a division, read "
              "with two verniers 180 degrees apart (least count 1 minute).", r=0.17, h=0.012, pos=[0, 0.006, 0],
              color="brass"),
            B("tableb", "cylinder", name="Prism table", info="Three levelling screws hold the prism table.",
              r=0.055, h=0.006, pos=[0, 0.03, 0], color="steel"),
            B("prism", "prism", name="Glass prism", info="An equilateral glass prism. Its refracting angle A is what "
              "you have to measure.", side=0.05, depth=0.04, angle="A", pos=[0, 0.055, 0], color="glass", opacity=0.45),
            B("coll", "cylinder", name="Collimator", info="A slit at the focus of its lens: it sends out parallel light.",
              r=0.022, h=0.3, pos=[-0.3, 0.09, 0], rot=[0, 0, 1.5708], color="#2b2f36"),
            B("tele", "cylinder", name="Telescope", info="Turned round the circle to catch each image; a cross-wire in "
              "the eyepiece is set on the image.", r=0.022, h=0.3, pos=[0.22, 0.09, 0.2], rot=[0, 0.7, 1.5708],
              color="#2b2f36"),
            B("lamp", "box", name="Sodium lamp", info="The source: its light falls on the collimator slit.",
              size=[0.08, 0.12, 0.08], pos=[-0.47, 0.06, 0], color="#f0c020"),
            B("rays", "rays", name="Light", var="rays", color="ray"),
            B("lbl", "text", text="divided circle", size=0.018, pos=[0.0, 0.015, 0.2]),
        ],
        knobs=[knob("A", "Prism (its angle is hidden)", "A", 50, 70, 0.1, 60, "°", DEG, hidden=True),
               knob("lam", "Wavelength of the light", "lam", 400, 700, 0.1, 589.3, "nm", 1e-9),
               knob("i", "Angle of incidence on the first face", "i", 30, 80, 0.5, 50, "°", DEG)],
        instruments=[inst("sep", "readout", "Angle between the two reflected images", "refl_sep", k=R2D, unit="°",
                          lc=0.0167, digits=3),
                     inst("dv", "readout", "Deviation of the emergent beam", "dev", k=R2D, unit="°", digits=2)],
        table={"columns": [col("sep", "Angle between the reflected images (2A)", "inst:sep", "°", DEG, digits=3)],
               "calc": "spect_prism_A", "rows_min": 3, "truth": "p.A", "result_k": R2D, "result_unit": "°",
               "result_digits": 2,
               "hint": "Set the cross-wire on each reflected image, read both verniers, and record the angle between "
                       "the two telescope positions."},
        steps=["Level the prism table and focus the telescope on a distant object, so it is set for parallel light.",
               "Set the slit narrow and bring the direct image on the cross-wire; read the circle.",
               "Put the prism on the table with its apex towards the collimator, so both polished faces are lit.",
               "Turn the telescope to the image reflected off the first face and read both verniers.",
               "Turn it to the image off the second face and read again: the angle between the two positions is 2A.",
               "Repeat on the other pair of verniers and take the mean."],
        theory="Light from the collimator falls on both polished faces of the prism at once. Turning a mirror through "
               "an angle turns the reflected beam through twice that angle, so the angle between the two reflected "
               "beams is exactly twice the refracting angle of the prism: A = (angle between the images) / 2. "
               "Schuster's method sets the instrument for parallel light without needing a distant object: focus the "
               "telescope on the far face of the prism inside minimum deviation, the collimator on the near face "
               "outside it, and repeat until both are sharp together.",
        safety="A sodium lamp runs hot and its choke is at mains voltage: do not touch the lamp while it is on, and "
               "never look down the collimator straight at the arc.",
        questions=[{"q": "Why is the angle between the two reflected images twice the angle of the prism?",
                    "options": ["A mirror turned by an angle turns the beam by twice that angle",
                                "The light is refracted twice", "The verniers are 180 degrees apart"], "answer": 0,
                    "why": "Reflection doubles the rotation, and the two faces are inclined at A."},
                   {"q": "What is the least count of a spectrometer circle with 30 vernier divisions on 29 "
                         "half-degree divisions?",
                    "options": ["1 minute", "30 minutes", "1 degree"], "answer": 0,
                    "why": "0.5 degrees / 30 = 1 minute of arc."}],
        sources=[DU, SUBRA, SIM],
        check={"params": {"A": 1.0471976}, "reading": "refl_sep", "textbook": "spect_sep"},
    )


def prism_index_spectrometer() -> dict:
    return lab(
        id="prism-index-spectrometer", rig="spectrometer-bench",
        title="Refractive index of a prism by minimum deviation", group=GRP, level=LVL,
        topic="Geometrical optics and the spectrometer", chapter="Geometrical optics and the spectrometer",
        aim="Find the angle of minimum deviation of a prism in sodium light and work out the refractive index of "
            "its glass from n = sin((A + Dm)/2) / sin(A/2).",
        kernel="spectrometer", params={"lam": 5.893e-7}, autorun=True,
        camera={"pos": [0.0, 0.55, 0.95], "look": [0.0, 0.03, 0.0]}, floor=-0.2,
        bodies=[
            _bench(),
            B("circle", "cylinder", name="Divided circle", info="Main scale and two verniers, least count 1 minute.",
              r=0.17, h=0.012, pos=[0, 0.006, 0], color="brass"),
            B("tableb", "cylinder", name="Prism table", r=0.055, h=0.006, pos=[0, 0.03, 0], color="steel"),
            B("prism", "prism", name="Glass prism", info="The prism under test; the index of its glass is hidden.",
              side=0.05, depth=0.04, angle="A", pos=[0, 0.055, 0], color="glass", opacity=0.45),
            B("coll", "cylinder", name="Collimator", info="Sends parallel sodium light onto the first face.",
              r=0.022, h=0.3, pos=[-0.3, 0.09, 0], rot=[0, 0, 1.5708], color="#2b2f36"),
            B("tele", "cylinder", name="Telescope", info="Follows the emergent beam; the cross-wire is set on the "
              "yellow image of the slit.", r=0.022, h=0.3, pos=[0.24, 0.09, 0.16], rot=[0, 0.55, 1.5708],
              color="#2b2f36"),
            B("lamp", "box", name="Sodium lamp", info="A sodium lamp gives one yellow line, so there is one image to "
              "set on.", size=[0.08, 0.12, 0.08], pos=[-0.47, 0.06, 0], color="#f0c020"),
            B("rays", "rays", name="Light through the prism", var="rays", color="ray"),
        ],
        knobs=[knob("i", "Turn the prism table (angle of incidence)", "i", 30, 80, 0.2, 50, "°", DEG),
               knob("n0", "Glass of this prism (its index is hidden)", "n0", 1.3, 1.8, 0.0001, 1.504518, hidden=True),
               knob("lam", "Wavelength of the light", "lam", 400, 700, 0.1, 589.3, "nm", 1e-9)],
        instruments=[inst("dv", "readout", "Deviation of the emergent beam", "dev", k=R2D, unit="°", lc=0.0167,
                          digits=3),
                     inst("em", "readout", "Angle of emergence", "e", k=R2D, unit="°", digits=2)],
        table={"columns": [col("dm", "Angle of minimum deviation Dm", "inst:dv", "°", DEG, digits=3)],
               "calc": "spect_n", "rows_min": 3, "result_digits": 4,
               "hint": "Turn the prism table slowly: the image walks one way, stops and turns back. Record the "
                       "deviation at that turning point."},
        steps=["Set the spectrometer for parallel light and read the direct position of the slit image.",
               "Place the prism so that light falls on one refracting face and comes out of the other.",
               "Turn the prism table slowly and follow the yellow image with the telescope.",
               "At the position where the image turns back, set the cross-wire on it and read both verniers.",
               "The angle between this reading and the direct reading is Dm.",
               "Repeat three times and work out n = sin((A + Dm)/2) / sin(A/2)."],
        theory="A prism bends light twice. As the prism is turned the deviation falls, reaches a least value and "
               "rises again; at that minimum the ray passes symmetrically through the prism, so r1 = r2 = A/2 and "
               "i = e = (A + Dm)/2. Snell's law at the first face then gives n = sin((A + Dm)/2) / sin(A/2). "
               "A denser glass bends the light more, so its Dm is larger.",
        safety="Hold the prism by its ground top and bottom faces only: a fingerprint on a polished face scatters "
               "the light. The sodium lamp is hot and mains-powered.",
        questions=[{"q": "At minimum deviation the ray inside the prism is",
                    "options": ["parallel to the base", "parallel to the first face", "along the base"], "answer": 0,
                    "why": "The passage is symmetric, r1 = r2 = A/2, so the ray runs parallel to the base."},
                   {"q": "Two prisms of the same angle, one crown and one flint glass. Which gives the larger Dm?",
                    "options": ["Flint", "Crown", "Both the same"], "answer": 0,
                    "why": "Flint glass has the larger refractive index, so it deviates the light more."}],
        sources=[DU, BK7, NA_D, SIM],
        check={"params": {"lam": 5.893e-7}, "reading": "dm", "textbook": "spect_dm"},
    )


def prism_dispersive_power() -> dict:
    return lab(
        id="prism-dispersive-power", rig="spectrometer-bench",
        title="Dispersive power and Cauchy constants of a prism", group=GRP, level=LVL,
        topic="Geometrical optics and the spectrometer", chapter="Geometrical optics and the spectrometer",
        aim="Measure the angle of minimum deviation of a prism for the mercury lines, find n for each line, and get "
            "the dispersive power and the Cauchy constants of the glass.",
        kernel="spectrometer", params={"lam": 4.35833e-7}, autorun=True,
        camera={"pos": [0.0, 0.55, 0.95], "look": [0.0, 0.03, 0.0]}, floor=-0.2,
        bodies=[
            _bench(),
            B("circle", "cylinder", name="Divided circle", r=0.17, h=0.012, pos=[0, 0.006, 0], color="brass"),
            B("tableb", "cylinder", name="Prism table", r=0.055, h=0.006, pos=[0, 0.03, 0], color="steel"),
            B("prism", "prism", name="Glass prism", info="The prism spreads the mercury lines into a spectrum.",
              side=0.05, depth=0.04, angle="A", pos=[0, 0.055, 0], color="glass", opacity=0.45),
            B("coll", "cylinder", name="Collimator", r=0.022, h=0.3, pos=[-0.3, 0.09, 0], rot=[0, 0, 1.5708],
              color="#2b2f36"),
            B("tele", "cylinder", name="Telescope", info="Set the cross-wire on each coloured line in turn.",
              r=0.022, h=0.3, pos=[0.24, 0.09, 0.16], rot=[0, 0.55, 1.5708], color="#2b2f36"),
            B("lamp", "box", name="Mercury lamp", info="A mercury lamp gives separate violet, green and yellow lines.",
              size=[0.08, 0.12, 0.08], pos=[-0.47, 0.06, 0], color="#bcd6f0"),
            B("rays", "rays", name="Light through the prism", var="rays", color="ray"),
        ],
        knobs=[knob("lam", "Mercury line on the cross-wire", "lam", 400, 600, 0.1, 435.8, "nm", 1e-9),
               knob("i", "Turn the prism table (angle of incidence)", "i", 30, 80, 0.2, 50, "°", DEG),
               knob("nB", "Glass of this prism (its dispersion is hidden)", "nB", 1.0, 20.0, 0.0001, 4.2211,
                    "×10⁻¹⁵ m²", 1e-15, hidden=True)],
        instruments=[inst("dv", "readout", "Deviation of the line on the cross-wire", "dev", k=R2D, unit="°",
                          lc=0.0167, digits=3)],
        table={"columns": [col("lam", "Mercury line", "knob:lam", "nm", 1e-9, digits=1),
                           col("dm", "Minimum deviation Dm", "inst:dv", "°", DEG, digits=3)],
               "calc": "spect_n", "rows_min": 3, "result_digits": 4,
               "hint": "For every mercury line: turn the prism table to minimum deviation, set the cross-wire on "
                       "that line and record its deviation."},
        steps=["Set the spectrometer for parallel light with the mercury lamp on the slit.",
               "Place the prism and find the spectrum: violet is deviated most, yellow least.",
               "Turn the prism table to minimum deviation for the violet line (435.8 nm) and read the circle.",
               "Do the same for the green line (546.1 nm) and the yellow line (579.1 nm).",
               "Work out n for each line from n = sin((A + Dm)/2) / sin(A/2).",
               "Plot n against 1 / wavelength squared: the slope is Cauchy's B and the intercept is A.",
               "The dispersive power is (n_violet - n_yellow) / (n_mean - 1)."],
        theory="The refractive index of glass falls as the wavelength rises, which is why a prism spreads white "
               "light. Over the visible range Cauchy's two-term law n = A + B / wavelength squared fits well, so a "
               "graph of n against 1 / wavelength squared is a straight line whose slope is B. The dispersive power "
               "of the glass is the spread of index divided by the mean deviating power, "
               "w = (n_violet - n_yellow) / (n_mean - 1); it is a property of the glass alone, not of the angle of "
               "the prism.",
        safety="A mercury lamp emits ultraviolet light: never run it with its outer envelope broken, and do not "
               "stare at the arc.",
        questions=[{"q": "Which mercury line is deviated most by the prism?",
                    "options": ["The violet line at 435.8 nm", "The green line at 546.1 nm",
                                "The yellow line at 579.1 nm"], "answer": 0,
                    "why": "n is largest at the shortest wavelength, so violet is deviated most."},
                   {"q": "Dispersive power depends on",
                    "options": ["the glass only", "the angle of the prism only", "both equally"], "answer": 0,
                    "why": "w = (nV - nY)/(n - 1) contains only the indices of the glass."}],
        sources=[DU, HG, BK7, SIM],
        check={"params": {"lam": 4.35833e-7}, "reading": "dm", "textbook": "spect_dm"},
    )


def grating_wavelength() -> dict:
    return lab(
        id="grating-wavelength-spectrometer", rig="spectrometer-bench",
        title="Wavelength with a plane transmission grating", group=GRP, level=LVL,
        topic="Diffraction", chapter="Diffraction",
        aim="Set a plane transmission grating for normal incidence on the spectrometer, measure the angle of "
            "diffraction of the first and second orders, and find the wavelength from d sin(theta) = m x wavelength.",
        kernel="planegrating", params={"lam": 5.893e-7, "N": 5906.0}, autorun=True,
        camera={"pos": [0.0, 0.55, 0.95], "look": [0.0, 0.03, 0.0]}, floor=-0.2,
        bodies=[
            _bench(),
            B("circle", "cylinder", name="Divided circle", info="Both verniers are read for every setting.",
              r=0.17, h=0.012, pos=[0, 0.006, 0], color="brass"),
            B("tableb", "cylinder", name="Grating table", r=0.055, h=0.006, pos=[0, 0.03, 0], color="steel"),
            B("grat", "box", name="Plane transmission grating", info="15 000 lines to the inch, held in a frame "
              "square to the beam.", size=[0.05, 0.04, 0.003], pos=[0, 0.055, 0], color="glass", opacity=0.5),
            B("coll", "cylinder", name="Collimator", r=0.022, h=0.3, pos=[-0.3, 0.09, 0], rot=[0, 0, 1.5708],
              color="#2b2f36"),
            B("tele", "cylinder", name="Telescope", info="Turned to the first and second order images on both sides.",
              r=0.022, h=0.3, pos=[0.26, 0.09, 0.12], rot=[0, 0.4, 1.5708], color="#2b2f36"),
            B("lamp", "box", name="Sodium lamp", size=[0.08, 0.12, 0.08], pos=[-0.47, 0.06, 0], color="#f0c020"),
        ],
        knobs=[knob("m", "Order on the cross-wire", "m", 1, 3, 1, 1),
               knob("lam", "Line in the lamp (its wavelength is hidden)", "lam", 400, 700, 0.1, 589.3, "nm", 1e-9,
                    hidden=True),
               knob("N", "Rulings lit by the beam", "N", 500, 12000, 1, 5906)],
        instruments=[inst("th", "readout", "Angle of diffraction of this order", "theta", k=R2D, unit="°", lc=0.0167,
                          digits=3)],
        table={"columns": [col("m", "Order m", "knob:m", digits=0),
                           col("theta", "Angle of diffraction", "inst:th", "°", DEG, digits=3)],
               "calc": "grating_lam", "rows_min": 2, "truth": "p.lam", "result_k": 1e9, "result_unit": "nm",
               "result_digits": 2,
               "hint": "Set the cross-wire on each order on the left and on the right; half the angle between them "
                       "is theta for that order."},
        steps=["Set the telescope for parallel light and bring the direct image on the cross-wire; read the circle.",
               "Turn the telescope through exactly 90 degrees and clamp it.",
               "Put the grating on the table and turn the table until the reflected image is on the cross-wire, "
               "then turn the table 45 degrees: the grating is now normal to the beam.",
               "Release the telescope and set the cross-wire on the first order on the left, then on the right.",
               "Half the angle between the two settings is theta for m = 1.",
               "Repeat for the second order and work out the wavelength for each."],
        theory="A grating is a set of very many equally spaced slits. The waves from all the rulings add up only in "
               "the directions where neighbouring rulings differ by a whole number of wavelengths, "
               "d sin(theta) = m x wavelength. Because thousands of rulings take part, these directions are extremely "
               "sharp, which is why a grating measures wavelength far better than a prism. The setting is made at "
               "normal incidence so that the simple grating equation applies.",
        safety="Never touch the ruled surface of a grating: the rulings are only microns apart and a fingerprint "
               "ruins it. Handle it by the frame.",
        questions=[{"q": "Why are grating lines much sharper than prism images?",
                    "options": ["Thousands of rulings interfere, so the maximum is very narrow",
                                "Gratings absorb less light", "A grating has no dispersion"], "answer": 0,
                    "why": "The width of a principal maximum falls as 1 / N."},
                   {"q": "With 15 000 lines per inch, how many orders of 589.3 nm light can be seen?",
                    "options": ["Two", "Four", "Only one"], "answer": 0,
                    "why": "d / wavelength = 1.6933 / 0.5893 = 2.87, so only m = 1 and 2 exist."}],
        sources=[DU, GRAT15, NA_D, SIM],
        check={"params": {"lam": 5.893e-7, "m": 1.0}, "reading": "theta", "textbook": "grating_theta"},
    )


def grating_resolving_power() -> dict:
    return lab(
        id="grating-resolving-power", rig="spectrometer-bench",
        title="Dispersive power and resolving power of a plane grating", group=GRP, level=LVL,
        topic="Diffraction", chapter="Diffraction",
        aim="Measure how far apart a grating throws two close wavelengths, and find the smallest wavelength "
            "difference it can just separate (its resolving power).",
        kernel="planegrating", params={"lam": 5.893e-7, "N": 5906.0}, autorun=True,
        camera={"pos": [0.0, 0.55, 0.95], "look": [0.0, 0.03, 0.0]}, floor=-0.2,
        bodies=[
            _bench(),
            B("circle", "cylinder", name="Divided circle", r=0.17, h=0.012, pos=[0, 0.006, 0], color="brass"),
            B("tableb", "cylinder", name="Grating table", r=0.055, h=0.006, pos=[0, 0.03, 0], color="steel"),
            B("grat", "box", name="Plane transmission grating", info="Only the rulings inside the beam take part, so "
              "a wider beam resolves better.", size=[0.05, 0.04, 0.003], pos=[0, 0.055, 0], color="glass", opacity=0.5),
            B("stop", "box", name="Adjustable stop", info="Narrowing the stop lights fewer rulings.",
              size=[0.01, 0.03, 0.04], pos=[-0.1, 0.07, 0], color="black"),
            B("coll", "cylinder", name="Collimator", r=0.022, h=0.3, pos=[-0.3, 0.09, 0], rot=[0, 0, 1.5708],
              color="#2b2f36"),
            B("tele", "cylinder", name="Telescope", r=0.022, h=0.3, pos=[0.26, 0.09, 0.12], rot=[0, 0.4, 1.5708],
              color="#2b2f36"),
            B("lamp", "box", name="Sodium lamp", info="Its yellow line is really two lines 0.6 nm apart.",
              size=[0.08, 0.12, 0.08], pos=[-0.47, 0.06, 0], color="#f0c020"),
        ],
        knobs=[knob("N", "Rulings lit by the beam", "N", 500, 12000, 1, 5906),
               knob("m", "Order used", "m", 1, 2, 1, 1),
               knob("lam", "Wavelength", "lam", 400, 700, 0.1, 589.3, "nm", 1e-9)],
        instruments=[inst("rp", "readout", "Smallest resolvable wavelength ratio", "theta", k=R2D, unit="°", digits=3)],
        table={"columns": [col("rp", "Resolving power from the fringe width", "inst:rp", digits=0)],
               "calc": "grating_R", "rows_min": 2, "result_digits": 0,
               "hint": "For each width of the beam, measure the angular width of the line and work out the "
                       "wavelength difference that just fills it."},
        steps=["Set the grating for normal incidence as in the wavelength experiment.",
               "Measure the angle of the first order for two close wavelengths and get the dispersion "
               "(change in angle divided by change in wavelength).",
               "Narrow the stop so that fewer rulings are lit and measure the angular width of the line.",
               "The smallest wavelength difference that can be told apart fills that width (Rayleigh's criterion).",
               "Work out the resolving power, wavelength divided by that difference, and compare it with m x N.",
               "Repeat with a wider beam: more rulings give a higher resolving power."],
        theory="Two things matter. The dispersive power of a grating, d(theta)/d(wavelength) = m / (d cos theta), "
               "says how far apart it throws two wavelengths. The resolving power says whether they can be told "
               "apart at all: a principal maximum is not a line but has an angular half width "
               "wavelength / (N d cos theta), so by Rayleigh's criterion two lines are just separated when one "
               "maximum falls on the first dark edge of the other. That gives a resolving power of m x N, where N is "
               "the number of rulings actually lit - a narrow beam on a fine grating resolves worse than a wide one.",
        safety="Handle the grating by its frame only. Do not force the stop against the grating surface.",
        questions=[{"q": "To resolve the two sodium D lines you need",
                    "options": ["a large number of rulings lit", "a brighter lamp", "a wider slit"], "answer": 0,
                    "why": "Resolving power is m x N, so it grows with the rulings in the beam, not with brightness."},
                   {"q": "Doubling the order m while lighting the same rulings",
                    "options": ["doubles the resolving power", "halves it", "leaves it unchanged"], "answer": 0,
                    "why": "R = m N."}],
        sources=[DU, GRAT15, NA_D, SIM],
        check={"params": {"lam": 5.893e-7, "m": 1.0, "N": 5906.0}, "reading": "rp", "textbook": "grating_rp"},
    )


# ====================================================================================== the interference bench
def newtons_rings() -> dict:
    return lab(
        id="newtons-rings", rig="interference-bench",
        title="Newton's rings", group=GRP, level=LVL,
        topic="Interference", chapter="Interference",
        aim="Measure the diameters of the dark Newton's rings with a travelling microscope and find the radius of "
            "curvature of the plano-convex lens.",
        kernel="newtonrings", params={"R": 1.0, "lam": 5.893e-7}, autorun=True,
        camera={"pos": [0.0, 0.45, 0.7], "look": [0.0, 0.06, 0.0]}, floor=-0.2,
        bodies=[
            _bench(),
            B("plate", "box", name="Plane glass plate", info="The flat the lens rests on; the film between them is "
              "the wedge of air that gives the rings.", size=[0.1, 0.008, 0.1], pos=[0, 0.004, 0], color="glass",
              opacity=0.5),
            B("lens", "lens", name="Plano-convex lens", info="Its radius of curvature is what you have to find.",
              r=0.035, thick=0.008, pos=[0, 0.014, 0], color="glass", opacity=0.45),
            B("glassp", "plane", name="Glass plate at 45 degrees", info="It turns the light from the lamp down onto "
              "the film and lets you look through from above.", size=[0.07, 0.07], pos=[0, 0.09, 0],
              rot=[0.7854, 0, 0], color="glass", opacity=0.35),
            B("micro", "cylinder", name="Travelling microscope", info="A microscope on a screw stage, least count "
              "0.001 cm: the cross-wire is set on each ring in turn.", r=0.018, h=0.16, pos=[0, 0.2, 0],
              color="#2b2f36"),
            B("lamp", "box", name="Sodium lamp", size=[0.08, 0.1, 0.08], pos=[-0.22, 0.05, 0], color="#f0c020"),
            B("ring", "torus", name="Dark ring", info="The dark rings crowd together as you go out.", r=0.012,
              tube=0.0008, pos=[0, 0.0085, 0], rot=[-1.5708, 0, 0], color="ink", illustrative=True,
              bind={"sx": {"var": "rn", "k": 26.3}, "sy": {"var": "rn", "k": 26.3}}),
            B("scalex", "scale", name="Microscope scale (cm)", length=0.1, spacing=0.01, major=5, labels=True,
              label_step=5, tick=0.006, font=0.01, pos=[0, 0.025, 0.07]),
        ],
        knobs=[knob("n", "Ring the cross-wire is on", "n", 2, 20, 1, 10),
               knob("R", "This lens (its radius is hidden)", "R", 0.2, 3.0, 0.001, 1.0, "m", hidden=True),
               knob("lam", "Wavelength of the light", "lam", 400, 700, 0.1, 589.3, "nm", 1e-9),
               knob("mu", "Index of the film between the glasses", "mu", 1.0, 1.6, 0.001, 1.0)],
        instruments=[inst("dn", "readout", "Diameter of this dark ring", "dn", k=1000, unit="mm", lc=0.01, digits=3),
                     inst("tf", "readout", "Thickness of the film under the cross-wire", "tfilm", k=1e9, unit="nm",
                          digits=1)],
        table={"columns": [col("n", "Ring number n", "knob:n", digits=0),
                           col("dsq", "Diameter squared", "inst:dn", "mm²", 1e-6, digits=4)],
               "calc": "rings_R", "rows_min": 3, "truth": "p.R", "result_k": 100, "result_unit": "cm",
               "result_digits": 2,
               "hint": "Set the cross-wire on the same ring on the left and on the right of the centre; the "
                       "difference of the two readings is the diameter."},
        steps=["Rest the lens on the plane plate and light the film through the glass plate at 45 degrees.",
               "Focus the travelling microscope until the rings are sharp, with the dark centre in the middle.",
               "Run the cross-wire out to the 20th dark ring on one side and come back, reading every alternate ring.",
               "Cross the centre and read the same rings on the other side.",
               "The difference of the two readings for a ring is its diameter.",
               "Plot the diameter squared against the ring number: the slope is 4 x wavelength x R, so R follows."],
        theory="Between the curved face of the lens and the flat plate there is a thin film of air whose thickness "
               "grows as the square of the distance from the point of contact, t = r squared / 2R. The light "
               "reflected from the two faces of the film interferes; the reflection at the lower face brings an "
               "extra half-wave, so the point of contact is dark. A dark ring needs 2 x mu x t = n x wavelength, "
               "which gives a diameter D_n = 2 x sqrt(n x wavelength x R / mu). D_n squared is therefore a straight "
               "line in n, and its slope gives R. Filling the film with a liquid shrinks every ring by sqrt(mu).",
        safety="The lens and the plate are optical surfaces: clean them only with lens tissue, and never slide the "
               "lens on the plate. The sodium lamp runs hot.",
        questions=[{"q": "Why is the centre of the Newton's rings pattern dark?",
                    "options": ["The reflection at the lower surface adds half a wave",
                                "The film is thickest there", "The lens absorbs the light"], "answer": 0,
                    "why": "At t = 0 the path difference is half a wavelength, so the two reflections cancel."},
                   {"q": "The air film is replaced by water (mu = 1.33). The rings then",
                    "options": ["shrink", "grow", "do not change"], "answer": 0,
                    "why": "D_n goes as 1 / sqrt(mu), so every ring comes closer in."},
                   {"q": "Why are the outer rings closer together?",
                    "options": ["The diameter goes as the square root of n", "The lamp is dimmer there",
                                "The microscope is out of focus"], "answer": 0,
                    "why": "D_n is proportional to sqrt(n), so the spacing falls as n grows."}],
        sources=[DU, NA_D, SIM],
        check={"params": {"R": 1.0, "lam": 5.893e-7, "n": 10.0}, "reading": "dn", "textbook": "rings_dn"},
    )


def air_wedge() -> dict:
    return lab(
        id="air-wedge-thickness", rig="interference-bench",
        title="Thickness of a thin sheet from air-wedge fringes", group=GRP, level=LVL,
        topic="Interference", chapter="Interference",
        aim="Measure the width of the straight fringes of an air wedge with a travelling microscope and find the "
            "thickness of the paper or wire that holds the two glass plates apart.",
        kernel="airwedge", params={"ts": 5e-5, "L": 0.05, "lam": 5.893e-7}, autorun=True,
        camera={"pos": [0.0, 0.45, 0.7], "look": [0.0, 0.06, 0.0]}, floor=-0.2,
        bodies=[
            _bench(),
            B("lower", "box", name="Lower glass plate", size=[0.09, 0.006, 0.05], pos=[0, 0.003, 0], color="glass",
              opacity=0.5),
            B("upper", "box", name="Upper glass plate", info="It rests on the lower plate at one edge and on the "
              "spacer at the other, so the film between them is a wedge.", size=[0.09, 0.006, 0.05],
              pos=[0, 0.0095, 0], rot=[0, 0, 0.0011], color="glass", opacity=0.5),
            B("spacer", "box", name="Spacer (paper or wire)", info="Its thickness is what you have to find.",
              size=[0.004, 0.0002, 0.05], pos=[0.025, 0.0065, 0], color="#c9a46a",
              bind={"sy": {"var": "p.ts", "k": 5000}}),
            B("glassp", "plane", name="Glass plate at 45 degrees", size=[0.06, 0.06], pos=[0, 0.08, 0],
              rot=[0.7854, 0, 0], color="glass", opacity=0.35),
            B("micro", "cylinder", name="Travelling microscope", info="Least count 0.001 cm; the cross-wire is run "
              "across the fringes.", r=0.018, h=0.16, pos=[0, 0.19, 0], color="#2b2f36"),
            B("lamp", "box", name="Sodium lamp", size=[0.08, 0.1, 0.08], pos=[-0.2, 0.05, 0], color="#f0c020"),
            B("fringe", "box", name="Dark fringe", info="The fringes are straight and parallel to the contact edge.",
              size=[0.0004, 0.0006, 0.05], pos=[0, 0.0105, 0], color="ink", illustrative=True,
              bind={"x": {"var": "xn", "k": 1.0, "c": -0.025}}),
            B("scalex", "scale", name="Microscope scale (cm)", length=0.09, spacing=0.01, major=5, labels=True,
              label_step=5, tick=0.006, font=0.01, pos=[0, 0.025, 0.045]),
        ],
        knobs=[knob("ts", "This spacer (its thickness is hidden)", "ts", 1e-5, 2e-4, 1e-7, 5e-5, "m", hidden=True),
               knob("L", "Contact edge to spacer", "L", 0.02, 0.09, 0.001, 0.05, "m"),
               knob("n", "Fringe the cross-wire is on", "n", 2, 60, 1, 10),
               knob("lam", "Wavelength of the light", "lam", 400, 700, 0.1, 589.3, "nm", 1e-9)],
        instruments=[inst("xn", "readout", "Position of this dark fringe", "xn", k=1000, unit="mm", lc=0.01,
                          digits=3),
                     inst("bt", "readout", "Fringe width (mean of ten)", "beta", k=1000, unit="mm", digits=4)],
        table={"columns": [col("n", "Fringe number n", "knob:n", digits=0),
                           col("x", "Position of the fringe", "inst:xn", "mm", 0.001, digits=3)],
               "calc": "wedge_t", "rows_min": 3, "truth": "p.ts", "result_k": 1e6, "result_unit": "µm",
               "result_digits": 2,
               "hint": "Set the cross-wire on one dark fringe, note the reading, then move ten fringes along and "
                       "note it again."},
        steps=["Lay the two glass plates together and slide the paper or wire in at one end.",
               "Light the film with sodium light through the glass plate at 45 degrees.",
               "Focus the microscope on the straight fringes running parallel to the contact edge.",
               "Set the cross-wire on a dark fringe, read the scale, move ten fringes along and read again.",
               "Divide the difference by ten to get the fringe width.",
               "Measure the distance from the contact edge to the spacer and work out its thickness."],
        theory="Two flats in contact at one edge and held apart at the other enclose a wedge of air whose thickness "
               "grows along the plate, t = ts x / L. The two reflections from the film interfere, with the usual "
               "extra half-wave at the lower surface, so a dark fringe falls wherever "
               "2 x mu x t = n x wavelength. The fringes are therefore straight, parallel to the contact edge and "
               "equally spaced, with a width beta = wavelength x L / (2 x mu x ts). Measuring beta and L gives the "
               "thickness of the spacer to a fraction of a micron, which no micrometer can do.",
        safety="Do not press the plates hard together: a trapped grit scratches an optical flat. The sodium lamp is "
               "hot and mains-powered.",
        questions=[{"q": "The fringes of an air wedge are",
                    "options": ["straight and equally spaced", "circular", "crowded towards the spacer"],
                    "answer": 0, "why": "The thickness grows linearly, so equal thickness means equal spacing."},
                   {"q": "A thicker spacer makes the fringes",
                    "options": ["closer together", "wider apart", "unchanged"], "answer": 0,
                    "why": "beta is inversely proportional to ts."}],
        sources=[DU, NA_D, SIM],
        check={"params": {"ts": 5e-5, "L": 0.05, "lam": 5.893e-7, "n": 10.0}, "reading": "beta",
               "textbook": "wedge_beta"},
    )


# ====================================================================================== the laser bench
def laser_double_slit() -> dict:
    return lab(
        id="laser-double-slit", rig="laser-bench",
        title="Wavelength of a laser by double-slit interference", group=GRP, level=LVL,
        topic="Interference", chapter="Interference",
        aim="Measure the fringe width of the double-slit pattern of a laser on a screen and find the wavelength of "
            "the laser light.",
        kernel="doubleslit", params={"lam": 6.328e-7, "d": 5e-4, "a": 4e-5, "D": 1.5}, autorun=True,
        camera={"pos": [0.3, 0.4, 1.0], "look": [0.1, 0.05, 0.0]}, floor=-0.2,
        bodies=[
            _bench(w=1.6),
            B("laser", "cylinder", name="Laser", info="A low-power laser clamped so that the beam runs along the "
              "bench, well below eye level.", r=0.016, h=0.12, pos=[-0.6, 0.05, 0], rot=[0, 0, 1.5708],
              color="#2b2f36"),
            B("holder", "box", name="Slide holder", info="Holds the double slit square to the beam.",
              size=[0.01, 0.07, 0.05], pos=[-0.4, 0.06, 0], color="black"),
            B("slits", "box", name="Double slit", info="Two slits, each 0.04 mm wide, their centres 0.5 mm apart.",
              size=[0.002, 0.02, 0.02], pos=[-0.4, 0.07, 0], color="#1a1a1a"),
            B("beam", "cylinder", name="Laser beam", info="Never put your eye in the beam.", r=0.0008, h=0.2,
              pos=[-0.5, 0.05, 0], rot=[0, 0, 1.5708], color="red", opacity=0.6, illustrative=True),
            B("screen", "plane", name="Screen", info="A white screen with a millimetre scale, 1.5 m from the slits.",
              size=[0.3, 0.2], pos=[0.6, 0.12, 0], rot=[0, 1.5708, 0], color="white"),
            B("fringe", "box", name="Bright fringe", info="The fringes are equally spaced, under a broad envelope.",
              size=[0.001, 0.0015, 0.02], pos=[0.6, 0.05, 0], color="red", illustrative=True,
              bind={"z": {"var": "xk", "k": 1.0}}),
            B("scalez", "scale", name="Screen scale (mm)", length=0.2, spacing=0.005, major=2, labels=False,
              tick=0.004, pos=[0.603, 0.02, 0], rot=[0, 1.5708, 0]),
        ],
        knobs=[knob("lam", "This laser (its wavelength is hidden)", "lam", 400, 700, 0.1, 632.8, "nm", 1e-9,
                    hidden=True),
               knob("d", "Separation of the slits", "d", 0.1, 1.0, 0.01, 0.5, "mm", 0.001),
               knob("D", "Slits to screen", "D", 0.5, 3.0, 0.01, 1.5, "m"),
               knob("k", "Fringe counted out on each side", "k", 2, 8, 1, 4)],
        instruments=[inst("bt", "readout", "Fringe width", "beta", k=1000, unit="mm", lc=0.1, digits=3),
                     inst("xk", "readout", "Position of that fringe", "xk", k=1000, unit="mm", digits=2)],
        table={"columns": [col("beta", "Fringe width", "inst:bt", "mm", 0.001, digits=3)],
               "calc": "dslit_lam", "rows_min": 2, "truth": "p.lam", "result_k": 1e9, "result_unit": "nm",
               "result_digits": 1,
               "hint": "Count out the same number of fringes on each side of the centre and divide the distance "
                       "between them by the number of gaps."},
        steps=["Clamp the laser so that the beam runs along the bench at bench height, never at eye level.",
               "Put the double slit in the holder and centre the beam on it.",
               "Set the screen 1.5 m away and let the pattern spread across its scale.",
               "Mark the 4th bright fringe on the left and the 4th on the right and measure between them.",
               "Divide by 8 to get the fringe width.",
               "Repeat at another screen distance and work out the wavelength from fringe width x d / D."],
        theory="Each slit spreads the light by diffraction, and the two spread beams overlap on the screen. Where "
               "their paths differ by a whole number of wavelengths the waves add, giving bright fringes spaced "
               "beta = wavelength x D / d. The single slit's own diffraction pattern, "
               "sinc squared of (pi a sin theta / wavelength), rides over the fringes as a broad envelope and makes "
               "the far fringes faint; it even removes a fringe altogether wherever d / a is a whole number. "
               "Counting out the same number of fringes on both sides of the centre cancels the small pull of that "
               "envelope.",
        safety="Laser safety: keep the beam horizontal at bench level and never at eye height, never look into the "
               "beam or at a mirror-like reflection of it, and keep watches and rings out of the beam path. Switch "
               "the laser off before leaning over the bench.",
        questions=[{"q": "The screen is moved twice as far away. The fringe width",
                    "options": ["doubles", "halves", "does not change"], "answer": 0,
                    "why": "beta = wavelength x D / d is proportional to D."},
                   {"q": "Why do the far fringes get faint?",
                    "options": ["The single-slit envelope falls away", "The laser is weak",
                                "The fringes get wider"], "answer": 0,
                    "why": "The diffraction pattern of one slit limits how far the fringes carry."}],
        sources=[{"title": "University of Delhi UGCF 2022 B.Sc. (Hons.) Physics: Modern Physics practical, "
                           "wavelength of a laser by a double slit"}, HENE, SIM],
        check={"params": {"lam": 6.328e-7, "d": 5e-4, "a": 4e-5, "D": 1.5, "k": 4.0}, "reading": "beta",
               "textbook": "dslit_beta", "tol": 0.01},
    )


def laser_grating() -> dict:
    return lab(
        id="laser-grating-wavelength", rig="laser-bench",
        title="Wavelength and angular spread of a laser with a grating", group=GRP, level=LVL,
        topic="Diffraction", chapter="Diffraction",
        aim="Send a laser beam through a plane grating, measure where the orders land on a screen, and find the "
            "wavelength and the angular spread of the laser.",
        kernel="gratingscreen", params={"lam": 6.328e-7, "d": 3.3333333e-6, "a": 1.6666667e-6, "D": 0.4}, autorun=True,
        camera={"pos": [0.3, 0.4, 1.0], "look": [0.1, 0.05, 0.0]}, floor=-0.2,
        bodies=[
            _bench(w=1.6),
            B("laser", "cylinder", name="Laser", info="Clamped at bench height, beam along the bench.", r=0.016,
              h=0.12, pos=[-0.6, 0.05, 0], rot=[0, 0, 1.5708], color="#2b2f36"),
            B("holder", "box", name="Grating holder", size=[0.01, 0.07, 0.05], pos=[-0.3, 0.06, 0], color="black"),
            B("grat", "box", name="Plane transmission grating", info="300 rulings to the millimetre, square to the "
              "beam.", size=[0.002, 0.03, 0.03], pos=[-0.3, 0.07, 0], color="glass", opacity=0.5),
            B("beam", "cylinder", name="Laser beam", r=0.0008, h=0.28, pos=[-0.45, 0.05, 0], rot=[0, 0, 1.5708],
              color="red", opacity=0.6, illustrative=True),
            B("screen", "plane", name="Screen", info="Half a metre behind the grating, with a scale on it.",
              size=[0.5, 0.2], pos=[0.2, 0.12, 0], rot=[0, 1.5708, 0], color="white"),
            B("spot", "sphere", name="First order spot", info="The orders are sharp bright spots.", r=0.003,
              pos=[0.2, 0.05, 0.2], color="red", illustrative=True, bind={"z": {"var": "xm", "k": 1.0}}),
            B("scalez", "scale", name="Screen scale (cm)", length=0.4, spacing=0.01, major=5, labels=True,
              label_step=10, tick=0.006, font=0.012, pos=[0.203, 0.02, 0], rot=[0, 1.5708, 0]),
        ],
        knobs=[knob("lam", "This laser (its wavelength is hidden)", "lam", 400, 700, 0.1, 632.8, "nm", 1e-9,
                    hidden=True),
               knob("m", "Order measured", "m", 1, 2, 1, 1),
               knob("D", "Grating to screen", "D", 0.2, 1.2, 0.01, 0.4, "m"),
               knob("d", "Grating spacing", "d", 1.0, 4.5, 0.0001, 3.3333333, "µm", 1e-6)],
        instruments=[inst("xm", "readout", "Distance of this order from the centre", "xm", k=100, unit="cm", lc=0.1,
                          digits=3),
                     inst("th", "readout", "Angle of diffraction", "theta", k=R2D, unit="°", digits=2)],
        table={"columns": [col("m", "Order m", "knob:m", digits=0),
                           col("x", "Distance from the centre", "inst:xm", "cm", 0.01, digits=3)],
               "calc": "gscreen_lam", "rows_min": 2, "truth": "p.lam", "result_k": 1e9, "result_unit": "nm",
               "result_digits": 1,
               "hint": "Measure from the straight-through spot to each order, on both sides, and take the mean."},
        steps=["Clamp the laser at bench height with the beam running along the bench.",
               "Set the grating square to the beam in its holder.",
               "Put the screen half a metre behind it and mark the straight-through spot.",
               "Mark the first order on the left and on the right and measure both distances.",
               "Work out the angle from the distance and the grating-to-screen distance.",
               "Find the wavelength from d sin(theta) = m x wavelength; repeat for the second order.",
               "Measure the width of the straight-through spot at two distances to get the beam's angular spread."],
        theory="The grating sends the beam out only in the directions where neighbouring rulings differ by a whole "
               "number of wavelengths, d sin(theta) = m x wavelength. On a screen D behind the grating the m-th "
               "order lands at x = D tan(theta), so measuring x and D gives theta and hence the wavelength. The "
               "straight-through spot itself grows slowly with distance; the rate at which its width grows is the "
               "angular spread (the divergence) of the laser beam, a few milliradians for a gas laser.",
        safety="Laser safety: the beam stays horizontal at bench level, never at eye height. A grating sends several "
               "bright orders out at once, so check where every order goes before you lean over the bench, and never "
               "look back along the beam or at its reflection.",
        questions=[{"q": "With 300 lines per mm and a red laser, the first order comes out at about",
                    "options": ["11 degrees", "2 degrees", "60 degrees"], "answer": 0,
                    "why": "sin(theta) = 632.8 nm / 3333 nm = 0.19, so theta is about 11 degrees."},
                   {"q": "Why must x be turned into an angle before using the grating equation?",
                    "options": ["Because the orders are at large angles, where x is not proportional to theta",
                                "Because the screen is white", "It need not be"], "answer": 0,
                    "why": "x = D tan(theta); the small-angle shortcut fails badly beyond a few degrees."}],
        sources=[DU, GRAT300, HENE, SIM],
        check={"params": {"lam": 6.328e-7, "d": 3.3333333e-6, "D": 0.4, "m": 1.0}, "reading": "xm",
               "textbook": "gscreen_x"},
    )


def cd_track_spacing() -> dict:
    return lab(
        id="cd-track-spacing", rig="laser-bench",
        title="Track spacing of a compact disc by laser diffraction", group=GRP, level=LVL,
        topic="Diffraction", chapter="Diffraction",
        aim="Use the rows of pits on a compact disc as a grating of unknown spacing: measure where the orders land "
            "and work out the track spacing of the disc.",
        kernel="gratingscreen", params={"lam": 6.328e-7, "d": 1.6e-6, "D": 0.3}, autorun=True,
        camera={"pos": [0.3, 0.4, 1.0], "look": [0.1, 0.05, 0.0]}, floor=-0.2,
        bodies=[
            _bench(w=1.6),
            B("laser", "cylinder", name="Laser", info="Clamped at bench height, beam along the bench.", r=0.016,
              h=0.12, pos=[-0.6, 0.05, 0], rot=[0, 0, 1.5708], color="#2b2f36"),
            B("holder", "box", name="Disc holder", size=[0.01, 0.09, 0.09], pos=[-0.3, 0.06, 0], color="black"),
            B("disc", "cylinder", name="Compact disc", info="Its spiral of pits acts as a grating; the spacing "
              "between the tracks is what you have to find.", r=0.06, h=0.0012, pos=[-0.295, 0.08, 0],
              rot=[0, 0, 1.5708], color="#c8ccd2"),
            B("beam", "cylinder", name="Laser beam", r=0.0008, h=0.28, pos=[-0.45, 0.05, 0], rot=[0, 0, 1.5708],
              color="red", opacity=0.6, illustrative=True),
            B("screen", "plane", name="Screen with a hole", info="The screen stands in front of the disc; the beam "
              "goes through a small hole in it and the orders come back onto it.", size=[0.4, 0.2],
              pos=[-0.0, 0.12, 0], rot=[0, 1.5708, 0], color="white"),
            B("spot", "sphere", name="First order spot", r=0.003, pos=[0.0, 0.05, 0.15], color="red",
              illustrative=True, bind={"z": {"var": "xm", "k": 1.0}}),
            B("scalez", "scale", name="Screen scale (cm)", length=0.3, spacing=0.01, major=5, labels=True,
              label_step=10, tick=0.006, font=0.012, pos=[0.003, 0.02, 0], rot=[0, 1.5708, 0]),
        ],
        knobs=[knob("d", "This disc (its track spacing is hidden)", "d", 0.5, 2.5, 0.001, 1.6, "µm", 1e-6,
                    hidden=True),
               knob("m", "Order measured", "m", 1, 2, 1, 1),
               knob("D", "Disc to screen", "D", 0.1, 0.8, 0.005, 0.3, "m"),
               knob("lam", "Wavelength of the laser", "lam", 400, 700, 0.1, 632.8, "nm", 1e-9)],
        instruments=[inst("xm", "readout", "Distance of this order from the centre", "xm", k=100, unit="cm", lc=0.1,
                          digits=3),
                     inst("th", "readout", "Angle of diffraction", "theta", k=R2D, unit="°", digits=2)],
        table={"columns": [col("m", "Order m", "knob:m", digits=0),
                           col("x", "Distance from the centre", "inst:xm", "cm", 0.01, digits=3)],
               "calc": "gscreen_d", "rows_min": 2, "truth": "p.d", "result_k": 1e6, "result_unit": "µm",
               "result_digits": 3,
               "hint": "Measure from the hole in the screen to each returning order and work the spacing out from "
                       "the angle."},
        steps=["Stand the screen in front of the disc and send the laser beam through a small hole in the screen.",
               "Let the beam fall straight onto the recorded side of the disc.",
               "The diffracted orders come back and land on the screen on either side of the hole.",
               "Measure the distance from the hole to the first order on each side and the disc-to-screen distance.",
               "Work out the angle and then the spacing from d sin(theta) = m x wavelength.",
               "Repeat for the second order if it falls on the screen."],
        theory="The data on a compact disc sits in a spiral of pits, and neighbouring turns of the spiral are "
               "equally spaced, so the disc works as a reflection grating. At normal incidence the returning orders "
               "obey the same grating equation, d sin(theta) = m x wavelength, so a known laser wavelength and a "
               "measured angle give the track spacing straight away. A CD comes out at about 1.6 micron and a DVD, "
               "whose tracks are much closer, throws its orders out much wider.",
        safety="Laser safety: a disc is a mirror as well as a grating, so reflected light goes back towards the "
               "laser. Keep the beam at bench level, never at eye height, tilt the disc only in the holder and never "
               "look into the returning beam.",
        questions=[{"q": "A DVD throws its orders out further than a CD because",
                    "options": ["its tracks are closer together", "it is thicker", "it spins faster"], "answer": 0,
                    "why": "sin(theta) = m x wavelength / d grows as d falls."},
                   {"q": "A compact disc works as a grating because",
                    "options": ["its spiral tracks are equally spaced", "it is shiny", "it is circular"],
                    "answer": 0, "why": "A grating needs a regular, equal spacing, which the track pitch gives."}],
        sources=[DU, CD, HENE, SIM],
        check={"params": {"lam": 6.328e-7, "d": 1.6e-6, "D": 0.3, "m": 1.0}, "reading": "xm",
               "textbook": "gscreen_x"},
    )


def fibre_numerical_aperture() -> dict:
    return lab(
        id="fibre-numerical-aperture", rig="fibre-bench",
        title="Numerical aperture of an optical fibre", group=GRP, level=LVL,
        topic="Lasers, fibre optics and applied optics", chapter="Lasers, fibre optics and applied optics",
        aim="Measure the patch of light that comes out of the far end of a multimode fibre at several distances and "
            "find the numerical aperture and the acceptance angle of the fibre.",
        kernel="fibrecone", params={"n1": 1.492, "n2": 1.402, "dcore": 0.001}, autorun=True,
        camera={"pos": [0.25, 0.3, 0.6], "look": [0.05, 0.04, 0.0]}, floor=-0.2,
        bodies=[
            _bench(w=1.0),
            B("source", "box", name="Fibre-optic light source", info="A lamp or LED launched into the near end of "
              "the fibre.", size=[0.11, 0.07, 0.09], pos=[-0.3, 0.035, 0], color="#2b2f36"),
            B("fibre", "cylinder", name="Plastic optical fibre", info="A step-index plastic fibre, 1 mm core. Its "
              "numerical aperture is what you have to find.", r=0.0012, h=0.3, pos=[-0.1, 0.04, 0.02],
              rot=[0, 0, 1.5708], color="#f0e8d0"),
            B("jig", "box", name="NA jig", info="Holds the fibre end square above a screen, with a screw to set the "
              "distance.", size=[0.05, 0.1, 0.06], pos=[0.06, 0.05, 0], color="black"),
            B("endf", "cylinder", name="Fibre end face", r=0.0015, h=0.002, pos=[0.06, 0.06, 0], color="white"),
            B("screen", "plane", name="Screen with a millimetre grid", info="The patch of light is measured on it "
              "with the grid.", size=[0.08, 0.08], pos=[0.06, 0.0205, 0], rot=[-1.5708, 0, 0], color="white"),
            B("patch", "cylinder", name="Patch of light", info="Its diameter grows as the screen is moved away.",
              r=0.012, h=0.0004, pos=[0.06, 0.021, 0], color="red", opacity=0.55, illustrative=True,
              bind={"sx": {"var": "W", "k": 41.7}, "sz": {"var": "W", "k": 41.7}}),
            B("scalez", "scale", name="Screen grid (mm)", length=0.07, spacing=0.005, major=2, labels=False,
              tick=0.003, pos=[0.06, 0.0215, 0.036]),
        ],
        knobs=[knob("n1", "Core of this fibre (its index is hidden)", "n1", 1.3, 1.6, 0.0001, 1.492, hidden=True),
               knob("n2", "Cladding of this fibre (its index is hidden)", "n2", 1.3, 1.6, 0.0001, 1.402, hidden=True),
               knob("dz", "Fibre end to screen", "dz", 0.002, 0.06, 0.0005, 0.02, "m"),
               knob("dcore", "Core diameter", "dcore", 0.0002, 0.002, 0.00005, 0.001, "m")],
        instruments=[inst("W", "readout", "Diameter of the patch of light", "W", k=1000, unit="mm", lc=0.5,
                          digits=2),
                     inst("na", "readout", "Numerical aperture from this reading", "na", digits=4)],
        table={"columns": [col("dz", "Fibre end to screen", "knob:dz", "mm", 0.001, digits=1),
                           col("W", "Diameter of the patch", "inst:W", "mm", 0.001, digits=2)],
               "calc": "fibre_NA", "rows_min": 3, "result_digits": 3,
               "hint": "For each distance, measure the diameter of the lit patch across the grid."},
        steps=["Launch the light into the near end of the fibre and clamp the far end in the NA jig.",
               "Set the fibre end a few millimetres above the screen, square to it.",
               "Measure the diameter of the lit patch on the millimetre grid.",
               "Move the screen away in steps and measure the diameter each time.",
               "For each pair work out the half angle of the cone from the diameter and the distance.",
               "The sine of that angle is the numerical aperture; the acceptance angle is its arcsine."],
        theory="Light stays in the core of a fibre only if it strikes the core-cladding boundary beyond the critical "
               "angle. Working that condition back to the end face gives an acceptance cone of half angle theta, "
               "with sin(theta) = sqrt(n1 squared - n2 squared) / n_outside. That number is the numerical aperture: "
               "it says how wide a cone the fibre will accept and, by the same geometry, how wide a cone comes out "
               "of the far end. So the patch on a screen a distance z away has a diameter "
               "W = core + 2 z tan(theta), and the slope of W against z gives the numerical aperture. A plastic "
               "fibre has a large NA, about 0.5; a glass telecom fibre is much smaller.",
        safety="Do not launch laser light into the fibre for this measurement unless the source is made for it: the "
               "cone out of the far end is bright. Never look into the end face of a lit fibre.",
        questions=[{"q": "The numerical aperture of a fibre depends on",
                    "options": ["the core and cladding indices", "the length of the fibre",
                                "the brightness of the source"], "answer": 0,
                    "why": "NA = sqrt(n1 squared - n2 squared), a property of the two glasses or plastics."},
                   {"q": "A fibre with a larger NA",
                    "options": ["accepts light from a wider cone", "carries light further",
                                "has a smaller core"], "answer": 0,
                    "why": "The acceptance angle is the arcsine of the NA."}],
        sources=[DU, POF, SIM],
        check={"params": {"n1": 1.492, "n2": 1.402, "dz": 0.02, "dcore": 0.001}, "reading": "na",
               "textbook": "fibre_na"},
    )


# ====================================================================================== the polarisation bench
def brewster_angle() -> dict:
    return lab(
        id="brewster-angle", rig="polar-bench",
        title="Polarisation by reflection: Brewster's angle", group=GRP, level=LVL,
        topic="Polarisation", chapter="Polarisation",
        aim="Reflect polarised light off a glass plate, find the angle at which the reflection of the parallel "
            "component vanishes, and get the refractive index of the glass from n = tan(Brewster's angle).",
        kernel="fresnelrefl", params={"n": 1.5168}, autorun=True,
        camera={"pos": [0.0, 0.45, 0.75], "look": [0.0, 0.05, 0.0]}, floor=-0.2,
        bodies=[
            _bench(),
            B("circle", "cylinder", name="Divided circle", info="The glass plate sits at the centre; the arm with "
              "the photocell swings round the scale.", r=0.15, h=0.01, pos=[0, 0.005, 0], color="brass"),
            B("plate", "box", name="Glass plate", info="A plain glass plate, blackened behind so that only the "
              "front surface reflects.", size=[0.006, 0.05, 0.05], pos=[0, 0.04, 0], color="glass", opacity=0.5),
            B("laser", "cylinder", name="Laser", info="Its light is already polarised; the polariser sets the plane.",
              r=0.014, h=0.1, pos=[-0.2, 0.04, 0.12], rot=[0, 0.6, 1.5708], color="#2b2f36"),
            B("pol", "cylinder", name="Polariser", info="Turned to put the electric field in the plane of "
              "incidence.", r=0.022, h=0.012, pos=[-0.1, 0.04, 0.07], rot=[0, 0.6, 1.5708], color="black"),
            B("cell", "box", name="Photocell on the arm", info="Reads the reflected light; it swings round to follow "
              "the reflected beam.", size=[0.04, 0.03, 0.03], pos=[0.13, 0.045, 0.1], color="#2b2f36"),
            B("meterb", "box", name="Microammeter", info="Shows how much light reaches the photocell.",
              size=[0.1, 0.05, 0.08], pos=[0.3, 0.025, -0.1], color="#2b2f36"),
            B("ray1", "arrow", name="Incident beam", dir=[1, 0, -0.6], len=0.14, pos=[-0.12, 0.04, 0.08],
              color="red", illustrative=True),
            B("ray2", "arrow", name="Reflected beam", dir=[1, 0, 0.6], len=0.14, pos=[0.02, 0.04, 0.01],
              color="red", illustrative=True),
        ],
        knobs=[knob("th", "Angle of incidence", "th", 10, 85, 0.5, 52, "°", DEG),
               knob("n", "This plate (its index is hidden)", "n", 1.2, 1.9, 0.0001, 1.5168, hidden=True)],
        instruments=[inst("rp", "readout", "Reflected light, field in the plane of incidence", "Rp", k=100,
                          unit="%", lc=0.1, digits=3),
                     inst("rs", "readout", "Reflected light, field across the plane", "Rs", k=100, unit="%",
                          digits=2),
                     inst("tb", "readout", "Angle of least reflection", "thb", k=R2D, unit="°", digits=2)],
        table={"columns": [col("thb", "Angle of least reflection", "inst:tb", "°", DEG, digits=3)],
               "calc": "brewster_n", "rows_min": 2, "truth": "p.n", "result_digits": 4,
               "hint": "Turn the plate and the arm together, watch the microammeter and record the angle where the "
                       "reading is least."},
        steps=["Set the polariser so that the electric field lies in the plane of incidence.",
               "Set the plate at about 50 degrees and swing the arm so that the photocell catches the reflected beam.",
               "Read the microammeter, then move the plate and the arm together in 2 degree steps.",
               "Near the minimum take half-degree steps: the reading falls almost to zero.",
               "Record that angle; repeat with the polariser turned by 90 degrees and see that the reflection "
               "does not vanish.",
               "Work out the index from n = tan(Brewster's angle)."],
        theory="When light is reflected off a dielectric, the two polarisations behave differently. Fresnel's "
               "formulae give the reflected fractions R_s and R_p, and R_p falls all the way to zero at one angle, "
               "where the reflected and refracted beams are at right angles. At that angle, Brewster's angle, the "
               "reflected light is completely polarised across the plane of incidence, and tan(Brewster's angle) = "
               "n. The component across the plane never vanishes, which is why the minimum appears only when the "
               "polariser puts the field in the plane of incidence.",
        safety="Laser safety: the plate reflects the beam, so work out where the reflection goes before switching "
               "on, keep the whole path at bench level and never at eye height, and never look into the beam or at "
               "its reflection. Blacken the back of the plate so there is no second reflected beam.",
        questions=[{"q": "At Brewster's angle the reflected light is",
                    "options": ["completely polarised across the plane of incidence",
                                "completely polarised in the plane of incidence", "unpolarised"], "answer": 0,
                    "why": "R_p is zero there, so only the component across the plane is reflected."},
                   {"q": "For glass of index 1.5 Brewster's angle is about",
                    "options": ["56 degrees", "34 degrees", "45 degrees"], "answer": 0,
                    "why": "arctan(1.5) = 56.3 degrees."}],
        sources=[DU, BK7, SIM],
        check={"params": {"n": 1.5168}, "reading": "thb", "textbook": "brewster_th"},
    )


def polarimeter_sugar() -> dict:
    return lab(
        id="polarimeter-sugar", rig="polar-bench",
        title="Specific rotation of sugar solution with a polarimeter", group=GRP, level=LVL,
        topic="Polarisation", chapter="Polarisation",
        aim="Measure how far a sugar solution turns the plane of polarisation in a half-shade polarimeter and find "
            "the specific rotation of sugar, then the concentration of an unknown solution.",
        kernel="polarimeter", params={"alpha": 66.5, "Ldm": 2.0}, autorun=True,
        camera={"pos": [0.0, 0.4, 0.8], "look": [0.0, 0.06, 0.0]}, floor=-0.2,
        bodies=[
            _bench(w=1.2),
            B("lamp", "box", name="Sodium lamp", info="Specific rotation is quoted at the sodium D line.",
              size=[0.08, 0.1, 0.08], pos=[-0.4, 0.05, 0], color="#f0c020"),
            B("pol", "cylinder", name="Polariser and half-shade", info="A half-wave plate over one half of the "
              "field makes the two halves equally bright only at one setting of the analyser.", r=0.025, h=0.03,
              pos=[-0.25, 0.06, 0], rot=[0, 0, 1.5708], color="black"),
            B("tube", "cylinder", name="Polarimeter tube", info="A 20 cm glass tube filled with the solution.",
              r=0.016, h=0.2, pos=[0, 0.06, 0], rot=[0, 0, 1.5708], color="glass", opacity=0.4),
            B("liquid", "cylinder", name="Sugar solution", info="A solution of cane sugar; it turns the plane of "
              "polarisation to the right.", r=0.013, h=0.19, pos=[0, 0.06, 0], rot=[0, 0, 1.5708], color="water",
              opacity=0.5),
            B("anal", "cylinder", name="Analyser on a divided circle", info="Turned until the two halves of the "
              "field look equally dim; its circle is read in degrees.", r=0.045, h=0.014, pos=[0.17, 0.06, 0],
              rot=[0, 0, 1.5708], color="brass"),
            B("eyep", "cylinder", name="Eyepiece", r=0.014, h=0.05, pos=[0.26, 0.06, 0], rot=[0, 0, 1.5708],
              color="#2b2f36"),
            B("needle", "needle", name="Analyser pointer", length=0.038, pos=[0.175, 0.06, 0], rot=[0, 1.5708, 0],
              bind={"rz": {"var": "match", "k": 1.0}}, color="red"),
            B("flask", "cylinder", name="Flask of the solution", info="Weighed sugar in a measured volume of water.",
              r=0.03, h=0.08, pos=[-0.3, 0.04, 0.16], color="glass", opacity=0.4),
        ],
        knobs=[knob("conc", "Concentration of this solution (hidden)", "conc", 0.02, 0.25, 0.001, 0.1, "g/mL",
                    hidden=True),
               knob("Ldm", "Length of the tube", "Ldm", 1.0, 4.0, 0.5, 2.0, "dm"),
               knob("phi", "Analyser setting", "phi", 70, 160, 0.1, 90, "°", DEG),
               knob("alpha", "Sugar in this bottle (its specific rotation is hidden)", "alpha", 20, 100, 0.1, 66.5,
                    hidden=True)],
        instruments=[inst("il", "readout", "Light through the left half", "il", k=100, unit="%", digits=1),
                     inst("ir", "readout", "Light through the right half", "ir", k=100, unit="%", digits=1),
                     inst("mt", "readout", "Setting at which the halves match", "match", k=R2D, unit="°", lc=0.05,
                          digits=2)],
        table={"columns": [col("c", "Concentration", "knob:conc", "g/mL", digits=3),
                           col("rot", "Rotation of the plane", "inst:mt", "°", DEG, digits=3)],
               "calc": "polari_alpha", "rows_min": 3, "truth": "p.alpha", "result_unit": "°/(dm·g/mL)",
               "result_digits": 2,
               "hint": "For each solution, find the analyser setting where the two halves match and subtract the "
                       "setting for pure water."},
        steps=["Fill the tube with distilled water, put it in the polarimeter and find the setting at which the two "
               "halves of the field look equally dim. This is the zero.",
               "Make up solutions of known strength by weighing sugar into a measured volume of water.",
               "Fill the tube with the strongest solution, with no air bubble in the light path, and find the new "
               "match setting.",
               "The difference from the zero is the rotation.",
               "Repeat for three more concentrations and plot the rotation against the concentration.",
               "The slope divided by the tube length in decimetres is the specific rotation; use it to read off the "
               "concentration of the unknown solution."],
        theory="Cane sugar is optically active: its molecules turn the plane of polarisation of light passing "
               "through the solution. The rotation is proportional to the length of the column and to the "
               "concentration, rotation = [alpha] x L(dm) x c(g/mL), where [alpha] is the specific rotation of the "
               "substance at that wavelength and temperature; for sucrose at the sodium D line and 20 degrees "
               "Celsius it is +66.5 degrees per decimetre per g/mL. The eye cannot judge when a field is darkest, "
               "but it is very good at telling two halves apart, so a half-shade plate splits the field in two and "
               "the setting where both halves look equally dim is the measurement.",
        safety="The sodium lamp and its choke run at mains voltage and get hot. Wipe up spilt solution at once: "
               "sugar on the bench ends up on the optics.",
        questions=[{"q": "Why is a half-shade plate used?",
                    "options": ["The eye judges two halves equal better than it judges one field darkest",
                                "It makes the field brighter", "It polarises the light"], "answer": 0,
                    "why": "A match between two halves is far more sensitive than an absolute minimum."},
                   {"q": "The tube is replaced by one twice as long. The rotation",
                    "options": ["doubles", "halves", "does not change"], "answer": 0,
                    "why": "Rotation is proportional to the length of the column."},
                   {"q": "Specific rotation is quoted at the sodium D line because",
                    "options": ["the rotation depends on the wavelength", "sodium lamps are cheap",
                                "sugar absorbs yellow light"], "answer": 0,
                    "why": "Optical rotation is strongly dispersive, so the wavelength must be stated."}],
        sources=[DU, SUGAR, NA_D, SIM],
        check={"params": {"alpha": 66.5, "Ldm": 2.0, "conc": 0.1}, "reading": "rot", "textbook": "polari_rot"},
    )


BUILDERS = (
    spectrometer_prism_angle, prism_index_spectrometer, prism_dispersive_power, grating_wavelength,
    grating_resolving_power, newtons_rings, air_wedge, laser_double_slit, laser_grating, cd_track_spacing,
    fibre_numerical_aperture, brewster_angle, polarimeter_sugar,
)
