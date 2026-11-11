"""Lab pack `ph3_nuc`: PhD / M.Sc. benches of nuclear, particle and cosmic-ray physics and of astrophysical data
analysis. The physics lives in `packs/ph3_nuc.py` (and its JavaScript twin); each lab names the studio RIG that draws
the real bench.

    ph3-coincidence       coincidence counting: resolving time from accidental coincidences (rig ph3-coincidence)
    ph3-pulse-coincidence true and accidental coincidences of Na-22 / Co-60 (same rig)
    ph3-compton           Compton scattering: scattered energy vs angle, electron rest energy (rig ph3-compton)
    ph3-compton-angular   the Klein-Nishina cross-section, total cross-section (same rig)
    ph3-alpha             alpha spectrometry with a Si surface-barrier detector, energy loss and range (rig ph3-alpha)
    ph3-muon              mean life of stopped cosmic-ray muons (rig ph3-muon)
    ph3-transit           exoplanet transit light curve - SIMULATED DATA (rig ph3-transit)
    ph3-hi21              the 21 cm line and the Galactic rotation curve - SIMULATED DATA (rig ph3-hi21)

Radioactive work follows the real rules of a teaching lab: sealed sources only, handled with tongs from behind a lead
shield and returned to a locked store. Where a lab needs archive data that cannot be fetched (TESS / Kepler light curves,
21 cm survey spectra), the data are SIMULATED from a stated model with a seeded generator and the title card says so.
Every counting or noisy result is checked within a stated statistical tolerance against an exact relation.
"""
from __future__ import annotations

from ..catalog import B, board, inst, knob, lab

GRP_N = "Physics · Nuclear, Particle and Cosmic-ray Physics"
GRP_A = "Physics · Radio Astronomy and Astrophysical Data"
SIM = {"title": "Hoola Prayogshala kernel",
       "note": "counts are drawn from the lab's own seed; checked against an exact relation in Hoola's tests"}
RAD_SAFE = {"title": "AERB safety guidelines for sealed radioactive sources in teaching laboratories",
            "note": "sources handled with tongs behind a lead shield, kept in a locked store"}
KNOLL = {"title": "G. F. Knoll, Radiation Detection and Measurement, 4th ed. (Wiley, 2010)",
         "note": "coincidence counting and accidental rates, scintillation spectrometry, alpha-particle energy loss"}
MELISS = {"title": "A. C. Melissinos and J. Napolitano, Experiments in Modern Physics, 2nd ed. (Academic Press, 2003)"}
MITJL = {"title": "MIT OpenCourseWare 8.13-14 Experimental Physics Junior Lab: experiments page",
         "note": "the Compton, muon, Rutherford and 21-cm experiments this lab follows in outline"}
CODATA = {"title": "SI 2019 and CODATA 2018: c, e, h, electron rest energy 510.99895 keV, classical electron radius",
          "note": "no source needed beyond the defining constants"}
ILLUS = "Illustrative lab settings, not from a datasheet: "
NOLASER = ""


def _stat(tol: str, why: str) -> dict:
    return {"title": "About this lab's check",
            "note": f"Run on the noise-free response, within {tol} of the exact relation. {why}"}


def _q(q, options, answer, why):
    return {"q": q, "options": options, "answer": answer, "why": why}


def _bench(n: int = 2) -> list[dict]:
    out = [board(1.2, 0.8, -0.01)]
    out.append(B("crate", "box", name="Electronics crate", size=[0.3, 0.12, 0.2], pos=[0.25, 0.06, -0.1], color="#2b2f36"))
    for i in range(n):
        out.append(B(f"det{i}", "cylinder", name="Detector", r=0.04, h=0.12, pos=[-0.3 + 0.2 * i, 0.06, 0.0], color="#2c3138"))
    return out


def _mk(id, rig, title, kernel, params, aim, steps, theory, safety, questions, sources, check, topic, chapter,
        grp=GRP_N, level="Ph.D.", knobs=None, instruments=None):
    return lab(id=id, rig=rig, title=title, group=grp, level=level, topic=topic, chapter=chapter, aim=aim,
               kernel=kernel, params=params, autorun=True, camera={"pos": [0.0, 0.6, 0.9], "look": [0.0, 0.05, 0.0]},
               floor=-0.03, bodies=_bench(), knobs=knobs or [], instruments=instruments or [], steps=steps,
               theory=theory, safety=safety, questions=questions, sources=sources, check=check)


SRC_SAFE = ("Sealed sources only. Move them with the tongs, from behind the lead shield, never with your fingers; "
            "keep them at arm's length, and put them back in their locked store as soon as the readings are done.")


# ====================================================================================== coincidence counting
def coincidence() -> dict:
    return _mk(
        "ph3-coincidence", "ph3-coincidence", "Coincidence counting: resolving time from accidental coincidences",
        "ph3_coinc",
        {"A1": 3.0e4, "A2": 2.4e4, "b1": 60.0, "b2": 50.0, "tau": 6.0e-8, "k": 1.0, "Rt": 0.0, "t": 100.0, "seed": 31.0,
         "j": 0.0},
        "Count two unrelated sources with two detectors and a coincidence unit at four gate widths, and find the "
        "resolving time of the unit from the accidental coincidence rate, R_acc = 2 tau R1 R2.",
        ["Put each source in front of its own detector with the tongs; the lead wall between them keeps them apart.",
         "Set the gate to x1, count for 100 s and write N1, N2 and the coincidences down.",
         "Repeat at x2, x3 and x4, changing nothing else.",
         "Plot the coincidence rate against the gate setting: a straight line through the origin.",
         "The slope is 2 tau R1 R2; divide by 2 R1 R2 (using the mean singles rates) to get tau."],
        "Two detectors seeing UNRELATED events still give coincidences by chance: when a pulse from detector 2 falls "
        "within the gate of a pulse from detector 1, the unit cannot tell they are unrelated. A pulse in detector 2 "
        "counts if it arrives up to tau before or tau after one in detector 1, a window of 2 tau, so the accidental "
        "rate is R_acc = 2 tau R1 R2. It rises in proportion to the gate width, which is why accidentals are the "
        "enemy of fast timing and why a short resolving time matters. Reading the line the other way, a measured "
        "R_acc with the two singles rates gives tau. The counts are Poisson numbers, so the result carries a "
        "statistical scatter of about two per cent.",
        SRC_SAFE,
        [_q("Two unrelated sources give coincidences by chance at a rate of", ["2 tau R1 R2", "tau R1 R2", "R1 R2 / tau"], 0,
            "The window is tau before and tau after: 2 tau."),
         _q("Doubling the gate width makes the accidental rate", ["Twice as big", "Four times as big", "Half as big"], 0,
            "R_acc is proportional to tau."),
         _q("Why is a lead wall put between the two sources?", ["So that no pulse in one detector is caused by the other source",
                                                              "To protect the detectors from light", "To raise the count rate"], 0,
            "Then every coincidence is by chance and the line goes through zero.")],
        [KNOLL, MELISS, RAD_SAFE, SIM,
         _stat("1 %", "The counts of the real student run are Poisson numbers; the result of one run is good to about 2-3 %."),
         {"title": ILLUS + "rates, background and gate width",
          "note": "the singles rates, the unit width of the gate and the background of this simulated bench are lab settings"}],
        {"reading": "tau_fit", "textbook": "ph3_coinc_tau", "tol": 0.01}, "Nuclear instrumentation and timing",
        "Nuclear, particle and cosmic-ray physics",
        knobs=[knob("k", "Gate setting", "k", 1, 4, 1, 1), knob("t", "Counting time", "t", 10, 600, 10, 100, "s"),
               knob("tau", "This unit (its unit width is hidden)", "tau", 5, 3000, 1, 60, "ns", 1e-9, hidden=True)],
        instruments=[inst("rc", "readout", "Coincidence rate", "rc", unit="/s", digits=1),
                     inst("acc", "readout", "Accidental part", "acc", unit="/s", digits=1)])


def pulse_coincidence() -> dict:
    return _mk(
        "ph3-pulse-coincidence", "ph3-coincidence", "Pulse width, singles and true coincidences of Na-22",
        "ph3_coinc",
        {"A1": 1.7e4, "A2": 1.7e4, "b1": 60.0, "b2": 50.0, "tau": 1.0e-7, "k": 1.0, "Rt": 210.0, "t": 200.0, "seed": 37.0,
         "j": 0.0},
        "With a source that sends two quanta from one decay to two detectors, count the singles and the coincidences "
        "at four gate widths, and separate the true coincidence rate from the accidental ones by the straight line "
        "of rate against gate width.",
        ["Put the source midway between the detectors with the tongs.",
         "Set the gate to x1, count for 200 s and write the singles and the coincidences down.",
         "Repeat at x2, x3 and x4: widening the pulses lets more chance coincidences in.",
         "Plot the coincidence rate against the gate setting.",
         "Extend the line back to zero width: the intercept is the true coincidence rate."],
        "When a nucleus emits two quanta together, a detector on each side gives pulses that always overlap: the "
        "TRUE coincidence rate, which does not depend on how wide the gate is as long as it is wide enough to catch "
        "the pair. On top of it, unrelated pulses overlap by chance at 2 k tau R1 R2, in proportion to the gate. So "
        "R_c = R_true + 2 k tau R1 R2: a straight line whose slope shows how pulse width raises the accidentals and "
        "whose intercept at k = 0 is the true rate. Narrow pulses (a short shaping time) therefore give a cleaner "
        "coincidence spectrum at the cost of timing jitter eventually cutting off the true events. The counts are "
        "Poisson numbers, so the true rate carries a statistical scatter of about two per cent.",
        SRC_SAFE,
        [_q("The true coincidence rate is found as", ["The intercept of the line at zero gate width", "The slope of the line",
                                                     "The rate at the widest gate"], 0,
            "It does not depend on the gate width; the accidentals vanish as the width goes to zero."),
         _q("Na-22 gives true coincidences because", ["A positron annihilates into two back-to-back 511 keV quanta",
                                                      "It emits one very strong gamma ray", "Its two detectors are close together"], 0,
            "The pair leaves in opposite directions, one into each detector."),
         _q("Making the shaped pulses twice as wide makes the accidental part", ["Twice as big", "Unchanged", "Half as big"], 0,
            "R_acc = 2 k tau R1 R2.")],
        [KNOLL, MELISS, RAD_SAFE, SIM,
         {"title": "NNDC / ENSDF: Na-22 (beta+ about 90 %, two 511 keV quanta per positron) and Co-60 (1173 and 1332 keV in cascade)",
          "note": "branching quoted to about two figures only"},
         _stat("1 %", "The counts of a real run are Poisson numbers; the true rate of one run is good to about 2-3 %."),
         {"title": ILLUS + "source strength, geometry, efficiencies and pulse width",
          "note": "the true coincidence rate 210 per second and the singles rates are set by the lab, not measured on a particular source"}],
        {"reading": "Rt_fit", "textbook": "ph3_coinc_rt", "tol": 0.01}, "Nuclear instrumentation and timing",
        "Nuclear, particle and cosmic-ray physics",
        knobs=[knob("k", "Gate setting", "k", 1, 4, 1, 1), knob("t", "Counting time", "t", 10, 600, 10, 200, "s"),
               knob("Rt", "This source (its true rate is hidden)", "Rt", 10, 2000, 1, 210, "/s", hidden=True)],
        instruments=[inst("rc", "readout", "Coincidence rate", "rc", unit="/s", digits=1),
                     inst("acc", "readout", "Accidental part", "acc", unit="/s", digits=1)])


# ====================================================================================== Compton scattering
def compton() -> dict:
    return _mk(
        "ph3-compton", "ph3-compton", "Compton scattering: energy against angle and the electron rest energy",
        "ph3_compton",
        {"th": 90.0, "ne25": 2.76, "t": 600.0, "seed": 17.0, "task": 0.0, "coin": 0.0},
        "Scatter the 662 keV gamma rays of Cs-137 from an aluminium rod, measure the energy of the scattered photons "
        "at seven angles with a NaI(Tl) spectrometer, and find the electron rest energy from E'(theta).",
        ["Calibrate the MCA with two known lines: Am-241 (59.54 keV) and the direct Cs-137 beam (661.66 keV).",
         "Put the scatterer in the beam. Swing the detector arm to 20 degrees and count for 600 s.",
         "Find the scattered photopeak in the spectrum: its channel gives E', its net area the count.",
         "Repeat at 40, 60, 80, 100, 120 and 140 degrees.",
         "Plot 1/E' against (1 - cos theta): the slope is 1/(m c^2) and the intercept 1/E0."],
        "A photon that scatters off a free electron at rest loses energy, and the loss depends only on the angle: "
        "E' = E0 / (1 + (E0 / m c^2)(1 - cos theta)). Written as 1/E' = 1/E0 + (1 - cos theta)/(m c^2), it is a "
        "straight line whose slope is the reciprocal of the electron rest energy, found from the photon energies "
        "alone. How many photons go in each direction is the Klein-Nishina cross-section per electron; the "
        "scatterer's electrons scatter almost as if free because 662 keV is far above their binding energy. The "
        "detector is a NaI(Tl) crystal: the scattered line makes a photopeak at E' on a Compton shelf. In this "
        "simulation the scatterer is treated as thin, so absorption inside it is not modelled (a real rod needs a "
        "correction of 20-30 % in the counts, not in the energies).",
        SRC_SAFE + " The beam leaves the collimator in one direction only: keep out of it.",
        [_q("The energy of a photon Compton scattered through 180 degrees is about", ["E0 / (1 + 2 E0/mc2)", "E0 / 2", "Zero"], 0,
            "cos 180 = -1, so E' = E0 / (1 + 2 E0/mc2): the smallest energy."),
         _q("Which plot of the readings is a straight line?", ["1/E' against 1 - cos theta", "E' against theta", "E' against cos theta"], 0,
            "1/E' = 1/E0 + (1 - cos theta)/mc2."),
         _q("A bound electron scatters like a free one at 662 keV because", ["The photon energy is far above the binding energy",
                                                                             "Aluminium has no bound electrons", "The beam is collimated"], 0,
            "Binding energies are keV or less; the photon carries 662 keV.")],
        [KNOLL, MITJL, CODATA,
         {"title": "NNDC / ENSDF: Cs-137 (Ba-137m) gamma 661.657 keV, 85.1 % per decay; Am-241 gamma 59.5409 keV",
          "note": "values entered from memory of the evaluated tables; check against NNDC before quoting"},
         {"title": "Klein and Nishina (1929); NIST XCOM for the electron density of aluminium (Z/A = 0.48181)"}, SIM,
         _stat("1 %", "Peaks are located with a centroid within three widths; the real run adds counting noise of about 0.2 %."),
         {"title": ILLUS + "source strength, collimator, geometry, detector resolution and efficiency card",
          "note": "R662 = 7.5 % and the efficiency card are typical of a 2-inch NaI(Tl) (Knoll) but are not those of a particular crystal"}],
        {"reading": "mc2", "textbook": "ph3_compton_mc2", "tol": 0.01}, "Gamma-ray interactions", "Nuclear, particle and cosmic-ray physics",
        knobs=[knob("th", "Detector angle", "th", 20, 140, 5, 90, "deg"), knob("t", "Counting time", "t", 60, 1800, 60, 600, "s")],
        instruments=[inst("ep", "readout", "Scattered photon energy", "Ep", unit="keV", digits=1)])


def compton_angular() -> dict:
    return _mk(
        "ph3-compton-angular", "ph3-compton", "Compton scattering: the Klein-Nishina cross-section and its total",
        "ph3_compton",
        {"th": 90.0, "ne25": 2.76, "t": 600.0, "seed": 19.0, "task": 1.0, "coin": 0.0},
        "From the counts in the scattered photopeak at seven angles, find the differential cross-section "
        "d sigma / d Omega of Compton scattering, compare it with the Klein-Nishina curve and integrate it to the "
        "total cross-section per electron.",
        ["Calibrate the MCA with Am-241 (59.54 keV) and the direct Cs-137 beam.",
         "Count at 20, 40, 60, 80, 100, 120 and 140 degrees for 600 s each; find each scattered photopeak.",
         "Correct each net area for the crystal's photopeak efficiency at E' (the efficiency card) and the geometry: that is d sigma/d Omega.",
         "Compare with the Klein-Nishina formula at each angle; the ratio should be one at every angle.",
         "Integrate 2 pi sin(theta) d sigma/d Omega over the angles; fill the unmeasured ends with the Klein-Nishina curve scaled to your data."],
        "The differential cross-section is the number scattered per electron per unit incident flux per steradian. "
        "Klein and Nishina gave it for a free electron: (r_e^2/2)(E'/E0)^2 (E'/E0 + E0/E' - sin^2 theta). At 662 keV "
        "the scattering is strongly forward, but not as forward as the classical Thomson value suggests, and it is "
        "the same per electron in every material, so a scatterer of copper and one of aluminium give the same "
        "curve once the number of electrons is divided out. Integrating over the sphere gives the total "
        "cross-section, 0.256 barn at this energy. In this simulation the scatterer is treated as thin: absorption "
        "inside it is not modelled.",
        SRC_SAFE + " The beam leaves the collimator in one direction only: keep out of it.",
        [_q("Per electron the Compton cross-section of copper compared with aluminium is", ["The same", "About three times larger", "Smaller"], 0,
            "The electrons scatter as free ones; only their number differs."),
         _q("The Klein-Nishina cross-section falls from its forward value to a minimum near", ["90 degrees to 130 degrees", "0 degrees", "Exactly 180 degrees"], 0,
            "At 662 keV it is smallest at large angles and rises slightly again toward backward scattering."),
         _q("To turn net counts into d sigma/d Omega you divide by", ["Flux, electrons, solid angle and photopeak efficiency",
                                                                     "The scatterer's mass only", "The counting time only"], 0,
            "N = flux x electrons x d sigma/d Omega x solid angle x efficiency x time.")],
        [KNOLL, MITJL, CODATA, {"title": "NNDC / ENSDF: Cs-137 (Ba-137m) 661.657 keV, 85.1 %; Am-241 59.5409 keV",
                                "note": "values entered from memory of the evaluated tables; check against NNDC before quoting"},
         {"title": "NIST XCOM: aluminium Z/A = 0.48181, 2.699 g/cm3; copper Z/A = 0.45636, 8.96 g/cm3"}, SIM,
         _stat("2 %", "Seven angles are integrated by the trapezoid rule and the ends are filled from the scaled curve."),
         {"title": ILLUS + "source strength, geometry and the crystal's efficiency card",
          "note": "the photopeak share and efficiency are typical of a 2-inch NaI(Tl) (Knoll), not of a particular crystal"}],
        {"reading": "sigma", "textbook": "ph3_compton_sigma", "tol": 0.02}, "Gamma-ray interactions", "Nuclear, particle and cosmic-ray physics",
        knobs=[knob("th", "Detector angle", "th", 20, 140, 5, 90, "deg"), knob("t", "Counting time", "t", 60, 1800, 60, 600, "s")],
        instruments=[inst("ep", "readout", "Scattered photon energy", "Ep", unit="keV", digits=1)])


# ====================================================================================== alpha spectrometry
def alpha() -> dict:
    return _mk(
        "ph3-alpha", "ph3-alpha", "Alpha spectrometry: energy loss in air and in a foil, and the range",
        "ph3_alpha",
        {"src": 0.0, "pr": 0.0, "d": 0.03, "tf": 0.0, "seed": 41.0, "t": 120.0},
        "In a vacuum chamber with a silicon surface-barrier detector, calibrate the spectrometer on two alpha "
        "sources, then let air into the chamber in steps and follow the alpha-particle energy as it falls; find the "
        "range in air, the energy resolution, and the stopping power of a gold foil.",
        ["Pump the chamber down. Put the Am-241 source on the rail, 3.0 cm from the detector, and count for 2 minutes.",
         "Do the same with Pu-239: the two peaks give the energy calibration of the MCA.",
         "With Am-241 in place, admit air to 100, 200 ... 700 mbar and record the peak position at each pressure.",
         "Plot the alpha energy to the power 3/2 against the air path (cm at 1013 mbar): it falls on a straight line.",
         "The line reaches zero at the range in air. Then put the gold foil in front of the source in vacuum: the loss gives its stopping power."],
        "An alpha particle loses energy to the gas it crosses at a rate that grows as it slows down, so it has a "
        "well-defined range. For alpha particles of 4-7 MeV in air the range follows the empirical Bragg-Kleeman "
        "rule R = a E^(3/2), so E^(3/2) falls linearly with distance: (E0)^(3/2) - x/a = E^(3/2). The line meets "
        "zero at x = R, the range, and its slope is -1/a. The gas pressure sets the mass the particle crosses, "
        "so distance x at pressure p counts as d p/1013 mbar of air at 15 C. A foil is equivalent to an air "
        "path of mass thickness / (0.56 A^(1/3)). The peaks widen as the path grows, because the energy loss is a "
        "chance process (straggling). Nothing is added to the detector's own width except that.",
        "Sealed sources only, moved with the tongs from behind the shield. Admit air to the chamber slowly and "
        "never touch the detector's front face, which is a thin gold layer; the bias is off while the chamber is open. "
        "Return the sources to the locked store.",
        [_q("The range of a 5.5 MeV alpha particle in air at 1 atm is about", ["4 cm", "4 m", "4 mm"], 0, "About 4 cm."),
         _q("A straight-line plot for the range is", ["E to the 3/2 against distance", "E against distance", "ln E against distance"], 0,
            "R = a E^(3/2), so E^(3/2) falls linearly with x."),
         _q("Letting air in makes the alpha peak", ["Move to lower energy and broaden", "Move up and sharpen", "Stay put"], 0,
            "More energy is lost, and straggling widens the line.")],
        [KNOLL, {"title": "R. D. Evans, The Atomic Nucleus (McGraw-Hill, 1955): Bragg-Kleeman range rule R = 0.318 E^1.5 cm in air",
                 "note": "coefficient 0.318 and the foil rule 0.56 A^(1/3) are the empirical textbook ones; recalled, check against Evans before quoting"},
         {"title": "NNDC / ENSDF: Am-241 alpha lines 5485.56 (84.8 %), 5442.80 (13.1 %), 5388.23 (1.66 %) keV; Pu-239 5156.59 (70.77 %), 5144.3 (17.11 %), 5105.5 (11.94 %) keV",
          "note": "values entered from memory of the evaluated tables; check against NNDC before quoting"},
         RAD_SAFE, SIM, _stat("1 %", "The peaks are located by a centroid; the Am-241 doublet is unresolved, so its centroid sits about 5 keV below the main line."),
         {"title": ILLUS + "detector width, straggling coefficient, source strength, chamber geometry",
          "note": "18 keV intrinsic width and 30 keV per square-root-cm of straggling are typical orders, not those of a particular detector"}],
        {"reading": "range", "textbook": "ph3_alpha_range", "tol": 0.01}, "Charged-particle detectors",
        "Nuclear, particle and cosmic-ray physics", grp=GRP_N, level="M.Sc. Physics",
        knobs=[knob("pr", "Air pressure in the chamber", "pr", 0, 1000, 50, 0, "mbar"), knob("t", "Counting time", "t", 30, 600, 30, 120, "s")],
        instruments=[inst("e1", "readout", "Energy of the main peak", "E1", unit="keV", digits=0),
                     inst("w", "readout", "Peak width (FWHM)", "fwhm", unit="keV", digits=1)])


# ====================================================================================== cosmic-ray muons
def muon() -> dict:
    return _mk(
        "ph3-muon", "ph3-muon", "Mean life of cosmic-ray muons stopped in a plastic scintillator",
        "ph3_muon",
        {"Rs": 150.0, "bgr": 0.03, "seed": 53.0, "h": 12.0},
        "Collect the times between a muon stopping in a scintillator block and its decay electron, build the decay "
        "time spectrum over three days, and find the muon mean life; compare it with the free-muon value to see the "
        "effect of the negative muons that are captured.",
        ["Switch on the high voltage and the time-to-amplitude converter; the trigger is a stopping muon (a pulse, then silence).",
         "Take data in blocks of 12 hours: each block adds to the histogram of start-stop delays.",
         "After six blocks (three days) find the floor from the last bins and subtract it.",
         "Plot the logarithm of the counts above the floor against the delay: the slope is -1/tau.",
         "Compare tau with the free-muon mean life: the difference is the capture of mu- on carbon."],
        "A cosmic-ray muon that stops in the scintillator lights it; when it decays after a time t, the electron "
        "lights it again. The delays follow an exponential with the muon's mean life, plus a flat floor of chance "
        "coincidences. A mu+ always decays with the free lifetime 2.197 microseconds. A mu- that stops in carbon "
        "can instead be captured by the nucleus, which shortens its life in the material to about 2.0 microseconds "
        "and removes it from the decay spectrum. At sea level there are about 1.27 mu- for each mu+, so the "
        "histogram is the sum of two exponentials and a straight-line fit gives an apparent life a few per cent "
        "below the free value. The hours of data per block are a lab setting; a real run takes days.",
        "No radioactive source: cosmic rays only. Keep the photomultiplier high voltage switched off while the "
        "tube base is open.",
        [_q("Why is the measured mean life of muons stopped in plastic a little shorter than 2.197 microseconds?",
            ["Negative muons are captured by carbon nuclei", "Muons decay faster at sea level", "The time converter runs fast"], 0,
            "Capture is an extra way for a mu- to disappear."),
         _q("The flat floor of the histogram is", ["Chance coincidences of unrelated pulses", "Muons that never decay", "Electronic noise of the converter only"], 0,
            "Unrelated start and stop pulses fall at any delay with equal probability."),
         _q("The slope of ln(counts above the floor) against delay is", ["-1/tau", "tau", "-tau"], 0, "N = N0 exp(-t/tau).")],
        [MITJL, MELISS,
         {"title": "Particle Data Group, Review of Particle Physics: mu+ lifetime 2.1969811 us; charge ratio of cosmic-ray muons at sea level about 1.27",
          "note": "the free lifetime is a PDG value; the mu-/mu+ ratio of STOPPED muons is taken equal to the flux ratio, a stated simplification"},
         {"title": "Capture lifetime of mu- in carbon, about 2.03 us (Suzuki, Measday and Roalsvig, Phys. Rev. C 35, 2212, 1987)",
          "note": "UNSOURCED / illustrative to the last digit: recalled from that paper's table, not looked up"},
         SIM, _stat("1 %", "The check is run with no capture (so the exact answer is the free lifetime); a real three-day run is good to about 2 %."),
         {"title": ILLUS + "stopping rate, accidental floor and the hours per block",
          "note": "150 stopping muons per hour and 0.03 chance counts per hour per microsecond are not those of a particular detector"}],
        {"params": {"r": 0.0, "bgr": 0.0}, "reading": "tau_fit", "textbook": "ph3_muon_free", "tol": 0.01},
        "Cosmic rays", "Nuclear, particle and cosmic-ray physics",
        knobs=[knob("Rs", "Muons stopping per hour", "Rs", 20, 2000, 10, 150, "/h"), knob("h", "Hours per block", "h", 1, 48, 1, 12, "h")],
        instruments=[inst("n", "readout", "Decays seen in one block", "n", unit="counts", digits=0)])


# ====================================================================================== transit light curve
def transit() -> dict:
    return _mk(
        "ph3-transit", "ph3-transit", "Exoplanet transit light curve (SIMULATED DATA, TESS-like)",
        "ph3_transit",
        {"P": 3.2, "k": 0.1, "b": 0.3, "rho": 1410.0, "u": 0.35, "t0": 1.3, "sig": 8.0e-4, "cad": 0.0069444, "span": 27.4,
         "seed": 61.0},
        "Analyse a SIMULATED light curve of a star with one planet: find the orbital period with a box least-squares "
        "search, fold the curve, measure the transit depth and duration, and deduce the planet-to-star radius ratio "
        "and the orbit's inclination.",
        ["Load the light curve (27 days, one point every 10 minutes): the dips are too small to see by eye.",
         "Run the box least-squares search over trial periods: the highest peak is the orbital period.",
         "Fold the light curve on that period and look at the transit.",
         "Measure the depth in the middle of the transit and the duration from first to last contact.",
         "Correct the depth for the star's limb darkening to get the radius ratio, then get the impact parameter and inclination."],
        "When a planet crosses the face of its star, the star's light dips by the fraction of its disc that is hidden. "
        "For a small planet at the centre of the disc this is (Rp/Rs)^2, but a star is darker at its edge, so the "
        "dip at mid-transit is (Rp/Rs)^2 (1 - u(1 - mu))/(1 - u/3), where mu = sqrt(1 - b^2) and u is the limb-darkening "
        "coefficient. The period is found by folding the curve on trial periods and keeping the one where a box-shaped "
        "dip is deepest. The duration depends on the impact parameter b, and b/(a/Rs) is cos i; a/Rs follows from "
        "Kepler's third law and the star's density. THE DATA ARE SIMULATED from a stated model with a seeded noise "
        "generator: this is not an observation of any real star.",
        "No hazard. Read the title card: the data are simulated, not archive data.",
        [_q("A planet with one tenth of the star's radius (centre of the disc, no limb darkening) dims the star by", ["1 %", "10 %", "0.1 %"], 0, "(0.1)^2 = 0.01."),
         _q("Folding the light curve on the wrong period", ["Smears the transit into a shallow dip", "Makes the transit deeper", "Changes nothing"], 0,
            "The transits no longer fall at the same phase."),
         _q("Limb darkening makes the mid-transit dip", ["Deeper than (Rp/Rs)^2 for a central transit", "Shallower", "Exactly (Rp/Rs)^2"], 0,
            "The planet hides the brighter centre of the disc.")],
        [{"title": "SIMULATED DATA: a light curve generated here from a stated model (P, Rp/Rs, b, density, u) with seeded Gaussian noise",
          "note": "not a TESS or Kepler observation of any real star; the model is a circular orbit and a linear limb-darkened disc"},
         {"title": "Seager and Mallen-Ornelas (2003), ApJ 585, 1038: transit duration and shape; Mandel and Agol (2002) for the occultation of a limb-darkened star",
          "note": "the formulas used are those of the first paper; the flux is integrated numerically ring by ring"},
         {"title": "Kovacs, Zucker and Mazeh (2002), A&A 391, 369: box least-squares period search"}, CODATA, SIM,
         _stat("1 %", "Run on the noise-free curve with the limb-darkening coefficient set to zero, where the depth is exactly (Rp/Rs)^2."),
         {"title": ILLUS + "period, radius ratio, impact parameter, stellar density, limb-darkening coefficient and noise",
          "note": "a hot Jupiter around a Sun-like star was chosen for the shape of the curve; no real target is meant"}],
        {"params": {"u": 0.0}, "reading": "k_fit", "textbook": "ph3_transit_k", "tol": 0.01}, "Astrophysical data analysis",
        "Radio astronomy and astrophysics data", grp=GRP_A,
        knobs=[knob("k", "This planet (its radius ratio is hidden)", "k", 0.02, 0.3, 0.001, 0.1, "", hidden=True)],
        instruments=[inst("dep", "readout", "Mid-transit depth", "depth", digits=5), inst("du", "readout", "Duration", "dur", unit="d", digits=3)])


# ====================================================================================== 21 cm line
def hi21() -> dict:
    return _mk(
        "ph3-hi21", "ph3-hi21", "The 21 cm hydrogen line and the Galactic rotation curve (SIMULATED DATA)",
        "ph3_hi",
        {"l": 40.0, "vc": 12.0, "sig": 0.25, "seed": 71.0},
        "From SIMULATED 21 cm spectra at five Galactic longitudes, convert frequency to velocity, correct to the "
        "local standard of rest, read the terminal velocity of the gas at each longitude and build the rotation curve "
        "of the Galaxy; find the hydrogen column density along one line of sight.",
        ["Point the telescope at l = 30 degrees on the Galactic plane and integrate; note the Doppler correction in the log.",
         "Change the frequency axis to velocity: v = c (f0 - f)/f0 with f0 = 1420.4058 MHz. Add the logged correction to reach the local standard of rest.",
         "Find the highest-velocity edge of the emission: that is the tangent point, at the terminal velocity.",
         "R = R0 sin l and Theta = v_t + Theta0 sin l, with R0 = 8.5 kpc and Theta0 = 220 km/s. Repeat at 40, 50, 60 and 70 degrees.",
         "Plot Theta against R; sum T dv along one line of sight for the column density N_H = 1.823e18 sum(T dv)."],
        "Hydrogen atoms emit a line at 1420.405752 MHz when the electron's spin flips relative to the proton's. Looking "
        "along the Galactic plane at longitude l in the first quadrant, gas on circular orbits has a radial velocity "
        "that grows as one looks further, until the line of sight is tangent to a circle at R = R0 sin l; beyond that "
        "point the velocity falls. The highest velocity seen is therefore that of the gas AT the tangent point: "
        "v_t = Theta(R0 sin l) - Theta0 sin l. Measuring v_t at several longitudes gives the rotation curve Theta(R). "
        "The line is thin in the gas, so the column density is proportional to the integral of the brightness "
        "temperature over velocity. Because the Earth and the Sun move, the observatory logs a correction to bring "
        "the velocities to the local standard of rest. THE SPECTRA ARE SIMULATED from a stated model (rotation "
        "curve, density, line width, noise): they are not a survey of the real sky.",
        "No hazard. The receiver is passive. Read the title card: the spectra are simulated.",
        [_q("The terminal velocity is measured at the tangent point because there", ["The line of sight runs along the orbit and velocity is largest", "The gas is densest", "The Sun is nearest"], 0,
            "Along the line of sight the radial velocity is largest where it is tangent to the orbit."),
         _q("The 21 cm line is produced by", ["The spin flip of the electron in hydrogen", "An electronic transition from n = 2", "Molecular rotation"], 0,
            "The hyperfine splitting of the hydrogen ground state."),
         _q("A flat rotation curve at large R means", ["Mass keeps growing with radius, more than the visible matter suggests", "No mass beyond the Sun", "The gas has stopped moving"], 0,
            "For circular orbits Theta^2 = G M(<R)/R, so a constant Theta needs M proportional to R.")],
        [{"title": "SIMULATED DATA: 21 cm spectra generated here from a stated model of the Galaxy with seeded Gaussian noise",
          "note": "rotation curve Theta = Th_inf R / sqrt(R^2 + Rc^2), density exp(-R/6 kpc), line width 6 km/s; not a survey of the real sky"},
         {"title": "IAU 1985 standard values R0 = 8.5 kpc, Theta0 = 220 km/s; hydrogen hyperfine line frequency 1420.405751768 MHz",
          "note": "N_H = 1.823e18 cm^-2 per (K km/s) for optically thin gas"},
         MITJL, {"title": "Burton (1988) in Galactic and Extragalactic Radio Astronomy, 2nd ed.: terminal-velocity method"}, SIM,
         _stat("1 %", "The edge is the half-peak point of the smoothed spectrum minus 0.63 line widths, a correction the observatory derived from this model; a noisy run is good to about 0.5 %."),
         {"title": ILLUS + "the rotation-curve shape, the density scale length and the 12 km/s Doppler correction",
          "note": "the 0.63 line-width edge correction is a calibration on this simulated galaxy, not a general constant"}],
        {"reading": "theta_fit", "textbook": "ph3_hi_theta", "tol": 0.01}, "Radio astronomy", "Radio astronomy and astrophysics data",
        grp=GRP_A, knobs=[knob("l", "Galactic longitude", "l", 20, 80, 5, 40, "deg")],
        instruments=[inst("vt", "readout", "Terminal velocity (true)", "vt", unit="km/s", digits=1),
                     inst("th", "readout", "Circular speed at the tangent radius", "Th", unit="km/s", digits=1)])


BUILDERS = (coincidence, pulse_coincidence, compton, compton_angular, alpha, muon, transit, hi21)
