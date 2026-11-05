"""Lab pack `msc_elec`: M.Sc. benches of nuclear spectroscopy, microwaves and advanced electronics. The physics
lives in `packs/msc_elec.py` (and its JavaScript twin); every lab here names the studio RIG that draws the bench.

Radioactive work follows the real rules of a teaching lab: sealed sources only, handled with tongs from behind lead,
counted at a set distance and locked away afterwards. Microwave power is a few milliwatts and is never aimed at a
person. The procedure of each lab says so.
"""
from __future__ import annotations

from ..catalog import B, SIM, board, inst, knob, lab

DU = {"title": "University of Delhi M.Sc. Physics practical lists (PH-DSE5116 nuclear physics, PH-DSE5163 and "
               "PH-DSE5114 electronics) and the SGGU / MLSU M.Sc. laboratory lists"}
NNDC = {"title": "NNDC / ENSDF evaluated nuclear data (BNL): gamma energies and intensities of Cs-137, Co-60, "
                 "Na-22, Ba-133, Am-241, Eu-152, K-40 and the U-238 and Th-232 series"}
KNOLL = {"title": "G. F. Knoll, Radiation Detection and Measurement, 4th ed.: ch. 2 (Compton edge, Klein-Nishina), "
                  "ch. 8-10 (scintillator and germanium resolution), ch. 12"}
RAD_SAFE = {"title": "AERB Safety Guidelines for sealed radioactive sources in teaching laboratories "
                     "(source handled with tongs behind a shield, kept in its locked store)"}
LAB_MODEL = {"title": "Simulated detector (lab settings)",
             "note": "The photopeak share and the intrinsic efficiency of the crystal are lab settings chosen to be "
                     "typical; peak positions, widths, Compton edge and geometry follow the textbook formulas"}
UNSCEAR = {"title": "UNSCEAR 2000 Report, Annex B: world-average soil activity concentrations K-40 400, U-238 series "
                    "35 and Th-232 series 30 Bq/kg"}

GROUP_N = "Physics · Nuclear Physics"


def _nuc_bodies(hpge: bool = False) -> list[dict]:
    return [
        board(1.0, 0.6),
        B("castle", "box", name="Lead castle", info="Lead bricks around the detector; open at the front.",
          size=[0.3, 0.62, 0.3], pos=[-0.35, 0.31, -0.1], color="#53565c"),
        B("det", "cylinder", name="Detector", info="The detector hangs in the roof of the castle.", r=0.043, h=0.12,
          pos=[-0.35, 0.5, -0.1], color="#b9bec5"),
        B("src", "cylinder", name="Sealed source", info="A sealed disc source on its rail, moved only with tongs.",
          r=0.01, h=0.004, pos=[-0.35, 0.3, -0.1], color="#c9462f"),
        B("nim", "box", name="NIM bin", info="High voltage, amplifier and multichannel analyser.",
          size=[0.34, 0.2, 0.22], pos=[0.15, 0.1, -0.2], color="#cdc9bf"),
    ]


def _gs(id, title, aim, task, params, theory, steps, questions, tour_say, check, sources, extra_knobs=(),
        hpge=False, level="M.Sc. Physics", safety=None):
    base = {"src": 0.0, "gain": 1.97, "off": 6.0, "nch": 1024.0, "R662": 0.07, "w0": 0.0, "pf662": 0.35,
            "et662": 0.55, "kE": 0.6, "act": 37.0, "d": 10.0, "rad": 3.81, "t": 300.0, "seed": 41.0, "bg": 0.0,
            "task": float(task)}
    base.update(params)
    knobs = [knob("t", "Live time", "t", 20, 1000, 10, base["t"], "s"),
             knob("d", "Source distance below the detector face", "d", 3, 40, 1, base["d"], "cm"),
             knob("gain", "Energy per channel (hidden: this amplifier setting)", "gain", 0.05, 6.0, 0.0001, base["gain"],
                  "keV/ch", hidden=True)] + list(extra_knobs)
    return lab(
        id=id, rig="msc-gamma-spectrometer", title=title, group=GROUP_N, level=level, topic="Nuclear physics",
        chapter="Nuclear physics", aim=aim, kernel="msc_gspec", params=base, autorun=True,
        camera={"pos": [0.0, 0.9, 1.1], "look": [-0.05, 0.25, -0.2]}, floor=-0.03, bodies=_nuc_bodies(hpge),
        knobs=knobs,
        instruments=[inst("rate", "readout", "Photons stopping in the crystal per second", "rate", unit="1/s", digits=1),
                     inst("om", "readout", "Fraction of the photons that reach the crystal", "omega", digits=4),
                     inst("f0", "readout", "FWHM of the strongest line", "fwhm0", unit="keV", digits=2)],
        steps=steps, theory=theory,
        safety=safety or ("Sealed sources only. Move them with the tongs, from behind the lead, never with your "
                          "fingers; keep them at arm's length, put them back in the locked store as soon as the counting "
                          "is over, and wash your hands afterwards. Bring the detector high voltage up slowly."),
        tour=[{"say": tour_say}], questions=questions, sources=sources, check=check)


NAI_STEPS = [
    "Switch on the high voltage, slowly, and wait for the detector to settle.",
    "Take a known source from the lead store with the tongs and put it on the rail below the detector.",
    "Take a spectrum for the live time given and find its tallest photopeak.",
    "Fit the peak with a Gaussian and write the centroid channel in the book.",
    "Do the same for each known source; draw channel against energy and fit a straight line.",
    "Put the unknown source on the rail, take its spectrum, fit its peak and read its energy off your line.",
]


def nai_calibration() -> dict:
    return _gs(
        "msc-nai-calibration", "NaI(Tl) spectrometer: energy calibration and the unknown gamma energy",
        "Calibrate the channel scale of a NaI(Tl) gamma spectrometer with sources of known energy, and find the energy "
        "of the strongest line of an unknown source from the calibration line.",
        0, {"src": 0.0},
        "A gamma ray that is stopped completely in a scintillation crystal gives a pulse proportional to its energy, so "
        "a photopeak sits at a channel number that is a straight line in energy, E = a + b × channel. Peaks of known "
        "energy fix the line. Each peak is a Gaussian, because the number of light photons made fluctuates; fitting it "
        "gives the centroid to a small fraction of a channel, and its width is the energy resolution. The counts in a "
        "channel are Poisson numbers, so a longer live time gives a cleaner peak.",
        NAI_STEPS,
        [{"q": "If the amplifier gain is doubled, the photopeak of a given line moves to", "options": [
            "Twice the channel number", "Half the channel number", "The same channel"], "answer": 0,
          "why": "Channel is proportional to pulse height, which is proportional to gain."},
         {"q": "The centroid of a Gaussian peak is found by a fit rather than by reading the tallest channel because",
          "options": ["It uses all the channels of the peak and gives a fraction of a channel",
                      "The tallest channel is always wrong", "The fit is faster"], "answer": 0,
          "why": "The scatter of one channel is Poisson noise; the fit averages it."}],
        "A NaI(Tl) crystal on its photomultiplier inside a lead castle, a source on a rail below it, and the analyser.",
        {"reading": "E_pk", "textbook": "msc_gs_E", "tol": 0.01},
        [DU, NNDC, KNOLL, RAD_SAFE, SIM])


def nai_efficiency() -> dict:
    return _gs(
        "msc-nai-efficiency", "NaI(Tl) detection efficiency: photopeak counts against source distance",
        "Count the photopeak of a calibrated source at several distances from a NaI(Tl) crystal, find the absolute "
        "efficiency at each, and from it the intrinsic photopeak efficiency of the crystal.",
        2, {"src": 0.0, "seed": 43.0},
        "Only a fraction Ω of the photons a source emits reaches the crystal: for a point source on the axis of a disc "
        "of radius a, at distance d, Ω = ½(1 − d/√(d² + a²)). Of those, the crystal turns a fraction ε_int into a "
        "full-energy pulse. The counts in the photopeak, divided by the photons emitted (activity × time × photons per "
        "decay), is the absolute efficiency ε_abs = Ω ε_int. It falls with distance as Ω does; the intrinsic efficiency "
        "stays constant, and is a property of the crystal and the photon energy.",
        ["Switch on the high voltage and put the calibrated source on the rail.",
         "Set a distance, take a spectrum and fit the photopeak; write down its net area.",
         "Repeat at four or more distances between 5 and 30 cm.",
         "Work out ε_abs = area / (A t I) and the geometric fraction Ω for each distance.",
         "ε_abs / Ω should be the same at every distance: that is the intrinsic efficiency."],
        [{"q": "The absolute photopeak efficiency changes with distance because", "options": [
            "The solid angle changes", "The crystal gets smaller", "The photons lose energy in air"], "answer": 0,
          "why": "Ω falls about as 1/d² when d is large compared with the crystal radius."},
         {"q": "Doubling the live time doubles the area of the photopeak but changes the efficiency by", "options": [
             "Nothing", "A factor of two", "A factor of four"], "answer": 0,
          "why": "Efficiency is counts per photon emitted, so the time cancels."}],
        "A calibrated source on a rail that can be set from 3 to 40 cm below the crystal.",
        {"reading": "eff_pk", "textbook": "msc_gs_eff", "tol": 0.02},
        [DU, NNDC, KNOLL, LAB_MODEL, RAD_SAFE, SIM])


def scint_comparison() -> dict:
    return _gs(
        "msc-scintillator-comparison", "Gamma detection with different scintillators: NaI(Tl) resolution",
        "Take the Cs-137 spectrum with a scintillation detector, fit the 662 keV photopeak and find the energy "
        "resolution; then compare crystals.",
        1, {"src": 0.0, "seed": 53.0},
        "The resolution R = FWHM/E of a scintillation detector is set by how many electrons the photomultiplier "
        "collects: more light per MeV and a better match to the tube give a narrower photopeak. NaI(Tl) gives about 7 % "
        "at 662 keV, CsI(Tl) and BGO are wider, and a plastic scintillator has so low an atomic number that it has no "
        "photopeak at all, only the Compton continuum ending at its edge. The fit of the photopeak gives the centroid "
        "and the FWHM; the edge is found as the steepest fall of the continuum.",
        ["Switch on the high voltage and put the Cs-137 source on the rail.",
         "Take a spectrum and fit the 662 keV photopeak (or, for plastic, find the Compton edge).",
         "Write the centroid, FWHM and resolution in the book.",
         "Repeat with a different live time to see how steady the value is.",
         "Compare with the other crystals of the family."],
        [{"q": "Which crystal in the list gives the narrowest photopeak?", "options": [
            "NaI(Tl)", "BGO", "Plastic"], "answer": 0,
          "why": "NaI(Tl) has the highest light yield for its stopping power among these."},
         {"q": "Why does the plastic scintillator have no photopeak?", "options": [
             "Its atomic number is too low for photoelectric absorption", "It is too thin", "It has no light output"],
          "answer": 0, "why": "The photoelectric cross-section goes roughly as Z to the fourth or fifth power."}],
        "A scintillation detector and the Cs-137 source: one tall photopeak on a flat Compton continuum.",
        {"reading": "cmp_pk", "textbook": "msc_gs_cmp", "tol": 0.01},
        [DU, NNDC, KNOLL, LAB_MODEL, RAD_SAFE, SIM])


def hpge_spectra() -> dict:
    return _gs(
        "msc-hpge-spectra", "HPGe gamma spectra: energy scale from Eu-152",
        "Fit six or more lines of Eu-152 with a high-purity germanium detector and find the energy per channel of the "
        "analyser from the straight line of energy against channel.",
        5, {"src": 5.0, "gain": 0.2031, "off": 0.8, "nch": 8192.0, "R662": 0.001708, "w0": 0.8166, "pf662": 0.5,
            "et662": 0.4, "kE": 0.6, "rad": 3.0, "seed": 47.0},
        "A germanium detector collects the charge of the electron-hole pairs made by a gamma ray, so its resolution is "
        "about forty times better than that of a scintillator: about 1.8 keV at 1332 keV. The width follows FWHM² = "
        "w0² + F E, a constant electronic noise plus a statistical part that grows with energy. Europium-152 has many "
        "lines from 122 to 1408 keV known to a fraction of a keV, so fitting them gives the energy per channel and shows "
        "how linear the analyser is.",
        ["Switch on the high voltage (the crystal is already cold: the dewar is full).",
         "Put the Eu-152 source on the rail and take a spectrum.",
         "Step through the peaks, fit each one and write it down.",
         "The book matches each peak to the line of the nuclear-data table.",
         "Fit energy against channel: the slope is the energy per channel."],
        [{"q": "Why does germanium separate lines that NaI(Tl) cannot?", "options": [
            "Its photopeaks are far narrower", "It is more efficient", "It is cheaper"], "answer": 0,
          "why": "A resolution of about 0.1 % against about 7 %."},
         {"q": "A germanium detector must be kept cold because", "options": [
             "Its leakage current at room temperature would swamp the signal", "The source needs cooling",
             "The lead becomes soft"], "answer": 0,
          "why": "The band gap of germanium is small, so thermal carriers are plentiful at room temperature."}],
        "A germanium detector on its liquid-nitrogen dewar; the Eu-152 spectrum is a forest of sharp lines.",
        {"reading": "E_pk", "textbook": "msc_gs_E", "tol": 0.01},
        [DU, NNDC, KNOLL, LAB_MODEL, RAD_SAFE, SIM],
        safety=("Sealed sources only, moved with tongs from behind lead and returned to the locked store. Liquid "
                "nitrogen: wear gloves and a face shield, never seal a container of it, and keep the room ventilated."),
        hpge=True)


BUILDERS = (nai_calibration, nai_efficiency, scint_comparison, hpge_spectra)
