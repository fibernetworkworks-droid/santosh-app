"""Lab pack `pg_matter_w9`: M.Sc. (wave 9) solid state, nuclear, modern, wave and microwave set-ups of
`syllabus/physics/pg.json`. Physics: the `pg_matter_w9` kernel pack (`pm9_*`) and its JavaScript twin.

One studio rig, `pm9-msc-bench`, draws the apparatus of each set-up (the GM counting castle, the spark counter, the
proportional counter and the scintillation spectrometer with their multichannel analyser, the magnetic beta
spectrometer, the coincidence table, the Hall and furnace benches, the oil bath, the monochromator, the cryostat with
its lock-in, the Stefan enclosures, the X-ray goniometer, the LC ladder, the pulse-echo set, the sound tube, the Lecher
line, the waveform analyser, the transducer stations and the microwave goniometer) and walks one sweep per stage.

Every lab's check runs the kernel's own plan and fit (the same rows the rig records) against the textbook relation.
Counting data is SIMULATED DATA from the lab's seed. Constants written from memory are labelled "from memory - verify";
design values of a particular instrument are labelled illustrative. English only.
"""
from __future__ import annotations

from ..catalog import B, board, inst, knob, lab

RIG = "pm9-msc-bench"
LEVEL = "M.Sc."
G_NUC = "Physics · Nuclear Physics"
G_SOL = "Physics · Solid State Physics"
G_MOD = "Physics · Modern Physics"
G_WAV = "Physics · Waves and Electronics"
CH_NUC = "Nuclear physics"
CH_SOL = "Solid state and materials"
CH_MOD = "Modern physics"
CH_WAV = "Waves, oscillations and electronics"
CH_MW = "Microwaves"

DU = {"title": "University of Delhi, M.Sc. Physics (effective 2025-26, A.C. 24.07.2025 Appendix-09): lab lists of "
               "PH-DSE5116/5216 Advanced Nuclear Physics, 5120 Advanced Solid State Physics, 5163/5164 labs"}
IITK = {"title": "IIT Kanpur Department of Physics, M.Sc. Lab (PHY 461/462) list of experiments"}
SGGU = {"title": "Shri Govind Guru University, M.Sc. Physics (CBCS) Semester 1 and 2 syllabus, MSC1P109/110/209/210 labs"}
SIM = {"title": "Hoola Prayogshala kernel pack pg_matter_w9",
       "note": "SIMULATED DATA: every reading comes from the simulation code and is checked against the textbook relation in Hoola's tests"}
ILLUS = {"title": "Illustrative instrument values",
         "note": "source strengths, efficiencies, gains, dimensions, component values and calibrations of this particular "
                 "apparatus are chosen to be typical of a teaching laboratory; they are not properties of a named device"}
KNOLL = {"title": "G. F. Knoll, Radiation Detection and Measurement, 4th ed. (Wiley): dead time, the two-source method, "
                  "GM and proportional counters",
         "note": "W = 26.2 eV and Fano factor about 0.17 for argon, avalanche variance b about 0.5 - cited from memory, "
                 "not fetched - verify"}
NNDC = {"title": "NNDC / ENSDF decay data (Brookhaven)",
        "note": "Cs-137 beta end point 514.0 keV (94.4 %), 661.657 keV gamma yield 85.1 %, K conversion line 624.2 keV; "
                "Sr-90 545.9 keV and Y-90 2278.5 keV end points; Tl-204 763.7 keV; Am-241 alpha 5.4857 MeV, Np L X-rays "
                "13.95 and 17.61 keV; Fe-55 Mn K-alpha 5.895 keV - from memory - verify"}
KATZ = {"title": "L. Katz and A. S. Penfold, Rev. Mod. Phys. 24, 28 (1952): R = 0.412 E^(1.265 - 0.0954 ln E) g/cm^2 in "
                 "aluminium; N. Feather (1938): R = 0.543 E - 0.160 g/cm^2 for E above about 0.8 MeV",
        "note": "the empirical mass absorption coefficient mu_m = 17 E^-1.14 cm^2/g and Feather's coefficients are quoted "
                "from memory - verify"}
SZE = {"title": "S. M. Sze, Physics of Semiconductor Devices: germanium ni about 2.4e13 cm^-3, mobilities 3900 and 1900 "
                "cm^2/V s at 300 K; band gaps Ge 0.66, Si 1.12 eV at 300 K",
       "note": "the 0 K linear extrapolations Eg0 (Ge 0.782 eV, Si 1.206 eV) and the T^-1.5 lattice mobility law are the "
               "usual teaching approximations - from memory - verify"}
RAD_SAFE = ("Sealed sources only. Handle them with tongs, keep them shielded and at arm's length, return them to the locked "
            "store as soon as the readings are done, and wash your hands afterwards.")
HV_SAFE = ("The detector supply is at high voltage: make every connection with it switched off and turned to zero, and "
           "raise the voltage slowly.")
EL_SAFE = "Switch the supplies off before changing a connection, and keep the currents inside the instruments' ranges."
HOT_SAFE = "The furnace, the bath and the lamp get hot: use the tongs and gloves, and let them cool before touching."
COLD_SAFE = ("Liquid nitrogen burns skin and displaces air: wear the face shield and cryogenic gloves, pour slowly, and "
             "work in a ventilated room.")


def _q(q, opts, ans, why):
    return {"q": q, "options": opts, "answer": ans, "why": why}


def _bodies(name: str, info: str) -> list[dict]:
    return [board(1.4, 0.7),
            B("main", "box", name=name, info=info, size=[0.42, 0.14, 0.26], pos=[-0.28, 0.07, -0.25], color="#4a4f57"),
            B("unit", "box", name="Instruments", info="The supply, the readout and the recorder of the experiment.",
              size=[0.4, 0.12, 0.22], pos=[0.4, 0.06, -0.22], color="#2b2f36")]


def _mk(id, kernel, group, chapter, title, aim, params, knobs, insts, theory, steps, questions, sources, check, safety,
        name, info, tour):
    return lab(id=id, rig=RIG, title=title, group=group, level=LEVEL, topic=chapter, chapter=chapter, aim=aim,
               kernel=kernel, params=params, autorun=True, camera={"pos": [0.1, 0.9, 1.15], "look": [0.1, 0.1, -0.25]},
               floor=-0.03, bodies=_bodies(name, info), knobs=knobs, instruments=insts, steps=steps, theory=theory,
               safety=safety, tour=tour, questions=questions, sources=sources, check=check)


Y = [inst("y", "readout", "Reading", "y", digits=3)]


# ================================================================================================= nuclear
def gm_deadtime() -> dict:
    return _mk(
        "pm9-gm-deadtime", "pm9_gmdt", G_NUC, CH_NUC, "GM counter: plateau, operating voltage and dead time",
        "Plot the counting plateau of a GM tube with a Cs-137 source, choose the operating voltage, and find the tube's "
        "dead time by the two-source method with Cs-137 and Sr-90. SIMULATED DATA.",
        {"x": 300.0, "s": 0.0},
        [knob("x", "Tube voltage or source arrangement", "x", 0, 800, 1, 300),
         knob("tau", "This tube (its dead time is hidden)", "tau", 5e-5, 1e-3, 1e-6, 3e-4, "s", hidden=True)],
        [inst("y", "readout", "Count rate", "y", unit="counts/s", lc=0.01, digits=2)],
        "A GM tube gives one pulse for each ionising particle, whatever its energy, once the voltage is above the "
        "threshold; over the PLATEAU the count rate barely changes with voltage, and the operating voltage is set about "
        "a third of the way along it. After each pulse the tube is dead for a time tau, so at a true rate n it records "
        "m = n / (1 + n tau) (non-paralysable). With two sources the losses do not add: the true rates satisfy "
        "n1 + n2 = n12 + nb, which the measured m1, m2, m12 and background mb only obey for the right tau. Solving that "
        "equation gives the dead time.",
        ["Raise the voltage in 20 V steps with the Cs-137 source on the shelf and count 30 s at each.",
         "Plot the plateau and set the operating voltage about a third of the way along it.",
         "Count the background with no source.",
         "Count Cs-137 alone, then Cs-137 and Sr-90 together, then Sr-90 alone, in exactly the same places.",
         "Find the dead time tau from n1 + n2 = n12 + nb with n = m / (1 - m tau)."],
        [_q("The two-source count m12 is less than m1 + m2 - mb because", ["Of dead-time losses", "The sources shield "
            "each other", "Of the background"], 0, "More counts are lost at the higher rate."),
         _q("The operating voltage is chosen", ["On the plateau, about a third along", "At the threshold",
            "Where continuous discharge begins"], 0, "There the rate is least sensitive to the voltage.")],
        [DU, IITK, KNOLL, ILLUS, SIM],
        {"params": {"t": 1.0e7}, "reading": "res", "textbook": "pm9_tau"}, RAD_SAFE + " " + HV_SAFE,
        "Lead castle with an end-window GM tube", "The GM tube over a source shelf inside lead bricks, and its scaler.",
        [{"say": "The GM tube in its lead castle, the two sealed sources in their store, and the scaler-timer."}])


def gm_efficiency() -> dict:
    return _mk(
        "pm9-gm-efficiency", "pm9_gmeff", G_NUC, CH_NUC, "Efficiency of a GM counter for beta particles",
        "Count a calibrated Sr-90/Y-90 beta source at known distances under an end-window GM tube and find the tube's "
        "intrinsic efficiency from the solid angle the window subtends. SIMULATED DATA.",
        {"x": 0.03, "s": 1.0},
        [knob("x", "Source to window distance", "x", 0.0, 10.0, 0.1, 3.0, "cm", 0.01),
         knob("eint", "This tube (its intrinsic efficiency is hidden)", "eint", 0.001, 1.0, 0.001, 0.9, hidden=True)],
        [inst("y", "readout", "Count rate", "y", unit="counts/s", lc=0.01, digits=2)],
        "A source of activity A emitting y particles per decay sends a fraction G of them into a window of radius a "
        "at distance d on its axis: G = (1 - d / sqrt(d^2 + a^2)) / 2. Of the particles that enter, the tube counts a "
        "fraction eps, its intrinsic efficiency: nearly every beta particle that crosses the window makes an avalanche, "
        "but a gamma ray must first knock an electron out of the wall, so eps for gammas is only about a per cent. "
        "With the background nb taken off and the dead time corrected, eps = (n - nb) / (A y G).",
        ["Count the background with the source in its store.",
         "Put the source on the slide 2 cm below the window and count.",
         "Repeat at 3, 4, 5 and 6 cm.",
         "Correct each rate for dead time, take the background off, and divide by A y G for each distance.",
         "The ratios agree if the geometry is right: their mean is the intrinsic efficiency."],
        [_q("A GM tube's efficiency for gamma rays is low because", ["A gamma must first eject an electron from the "
            "wall", "Gamma rays are slower", "The window stops them"], 0, "The gas itself hardly absorbs gamma rays."),
         _q("Halving the distance from a small window", ["Raises the rate by about four", "Doubles the rate",
            "Changes nothing"], 0, "Far from the window G falls as 1/d^2.")],
        [DU, SGGU, KNOLL, NNDC, {"title": "Sr-90 source certificate 3.7 kBq (0.1 microcurie); Sr-90 and Y-90 in "
                                          "secular equilibrium give two betas per Sr-90 decay",
                                 "note": "the activity is an illustrative certificate value"}, ILLUS, SIM],
        {"params": {"t": 1.0e7}, "reading": "res", "textbook": "pm9_eint"}, RAD_SAFE + " " + HV_SAFE,
        "GM tube over a source slide", "An end-window GM tube looking down at a graduated source slide, and its scaler.",
        [{"say": "The GM tube looks down at the graduated slide; the calibrated source sits on its carriage."}])


def beta_feather() -> dict:
    return _mk(
        "pm9-beta-feather", "pm9_betaf", G_NUC, CH_NUC, "Range of Sr-90/Y-90 betas in aluminium and Feather's rule",
        "Count a Sr-90/Y-90 source through stacked aluminium foils, find the range where the beta counts end, and turn "
        "it into the end-point energy with Feather's rule; the mass absorption coefficient from the slope. SIMULATED DATA.",
        {"x": 0.0, "s": 1.0},
        [knob("x", "Aluminium in the beam", "x", 0, 2000, 5, 0, "mg/cm²", 0.001),
         knob("E1", "This source (its end point is hidden)", "E1", 0.3, 3.5, 0.0001, 2.2785, "MeV", hidden=True)],
        [inst("y", "readout", "Count rate", "y", unit="counts/s", lc=0.01, digits=2)],
        "A beta source has a continuous spectrum up to an end point E. In aluminium the count rate first falls almost "
        "exponentially with the areal density x, N = N0 exp(-mu_m x), and then, at the RANGE R of the most energetic "
        "particles, the betas end and only the bremsstrahlung tail and the background are left. A Sr-90 source is in "
        "equilibrium with its daughter Y-90, so the curve has two parts: the soft Sr-90 betas (0.546 MeV) die out "
        "early, and the range is set by the Y-90 betas. Feather's rule R = 0.543 E - 0.160 g/cm^2 turns the range into "
        "the end-point energy (for E above about 0.8 MeV). Here each group is cut off sharply at its Katz-Penfold "
        "range; a real curve rounds off just before it.",
        ["Count the background for 30 minutes with the source in its store.",
         "Count through the foils of the box from 0 to 2 g/cm^2 (the thickest one shows only the tail).",
         "Near the end of the curve, stack 5 mg/cm^2 foils to halve the gap between the last foil that still shows "
         "betas (3 standard deviations above the tail) and the first that does not.",
         "The range is the midpoint of that last gap.",
         "Feather's rule gives E = (R + 0.160) / 0.543 MeV; the early slope gives mu_m."],
        [_q("In Sr-90/Y-90 the range is set by", ["The Y-90 betas", "The Sr-90 betas", "The bremsstrahlung"], 0,
            "Y-90 has the higher end point, 2.28 MeV."),
         _q("Feather's rule relates", ["Range to end-point energy", "Half-life to energy", "Dead time to voltage"], 0,
            "R = 0.543 E - 0.160 g/cm^2.")],
        [DU, KATZ, NNDC, KNOLL, SIM],
        {"params": {"t": 1.0e6, "tl": 1.0e7}, "reading": "res", "textbook": "pm9_range", "tol": 0.01},
        RAD_SAFE, "GM tube with a foil stack", "An end-window GM tube over the source shelf, aluminium foils between.",
        [{"say": "The GM tube in its castle; the foils of known areal density are laid on the shelf above the source."}])


def k40_ux2() -> dict:
    return _mk(
        "pm9-k40-ux2", "pm9_k40", G_NUC, CH_NUC, "Absolute activity of K-40 and its partial beta half-life",
        "Calibrate a GM counting tray with a UX2 beta standard, count a weighed layer of potassium chloride, and find "
        "the specific activity of potassium and the partial beta-decay half-life of K-40. SIMULATED DATA.",
        {"x": 1.0, "s": 2.0},
        [knob("x", "Count number", "x", 0, 5, 1, 1),
         knob("T12", "This isotope (its half-life is hidden)", "T12", 0.1, 10.0, 0.0001, 1.248, "x 10⁹ y", 1e9, hidden=True)],
        [inst("y", "readout", "Count rate", "y", unit="counts/s", lc=0.001, digits=3)],
        "Natural potassium holds 0.0117 % of K-40, so a gram of potassium contains about 1.8e18 K-40 nuclei. If the "
        "counter sees a fraction eps of the beta particles from a layer in a tray, eps can be found with a STANDARD "
        "of known beta emission rate in the same tray and geometry: the classic one is UX2 (Pa-234m, end point 2.27 "
        "MeV) in equilibrium with uranium. Then the beta emission rate of the potassium salt is (net rate) / eps, and "
        "since A_beta = lambda_beta N, the partial beta-decay half-life is T_beta = ln2 N / A_beta. Here both layers are "
        "assumed to be counted with the same eps (same thickness and backscatter, end points of the same order).",
        ["Count the empty tray twice (the background).",
         "Count the UX2 standard in the tray three times.",
         "Count a 100 g layer of potassium chloride, levelled in the same tray, three times.",
         "eps = (standard - background) / its certified emission rate.",
         "A_beta = (salt - background) / eps; T_beta = ln2 N(K-40) / A_beta."],
        [_q("The partial half-life is longer than the half-life because", ["Only 89 % of decays are beta decays",
            "The counter misses some betas", "Potassium is diluted"], 0, "T_beta = T_half / branching ratio."),
         _q("The standard must be counted", ["In the same tray and geometry", "Without the tray", "At a different shelf"],
            0, "Only then is the efficiency the same.")],
        [DU, {"title": "NNDC / NUBASE: K-40 half-life 1.248e9 y, beta-minus branch 89.28 %; IUPAC K-40 abundance 0.0117 %, "
                       "atomic weights K 39.0983, Cl 35.453", "note": "from memory - verify"},
         {"title": "UX2 (Pa-234m) beta standard of certified emission rate 1000 betas per second",
          "note": "illustrative certificate value; Pa-234m end point 2.27 MeV from memory - verify"}, ILLUS, SIM],
        {"params": {"t": 1.0e10}, "reading": "res", "textbook": "pm9_tbeta"},
        "Uranium standards are sealed: never open them, handle them with tongs and wash your hands afterwards. "
        "Potassium chloride is harmless but keep it off the electronics.",
        "GM tube over a counting tray", "An end-window GM tube in a lead castle over a shallow counting tray.",
        [{"say": "The GM tube in its castle over a shallow tray; the standard and the salt jar wait beside it."}])


def spark_alpha() -> dict:
    return _mk(
        "pm9-spark-alpha", "pm9_spark", G_NUC, CH_NUC, "Spark counter: plateau and range of Am-241 alphas in air",
        "Find the counting plateau of a spark counter with an Am-241 source, then move the source away from the grid "
        "and find the mean range of the alpha particles in air. SIMULATED DATA.",
        {"x": 1.0, "s": 1.0},
        [knob("x", "Spark counter voltage or source distance", "x", 0, 6000, 0.1, 1),
         knob("E", "This source (its alpha energy is hidden)", "E", 3.0, 9.0, 0.0001, 5.4857, "MeV", hidden=True)],
        [inst("y", "readout", "Count rate", "y", unit="counts/s", lc=0.01, digits=2)],
        "A spark counter is a fine wire held a millimetre above a flat plate at a few kilovolts: the dense ionisation of "
        "an alpha particle between them triggers a spark, but beta and gamma rays do not. Below a threshold voltage "
        "nothing counts, over a plateau every alpha reaching the gap counts, and too high a voltage gives continuous "
        "sparking. Alpha particles of one energy all travel about the same distance in air; the counts fall to half "
        "at the MEAN range (range straggling rounds the edge). Correcting for the solid angle (counts x d^2), the "
        "half point gives the mean range, which Geiger's rule R = 0.318 E^1.5 cm (E in MeV) relates to the energy.",
        ["With the source 1 cm from the wire, raise the voltage from 3.0 to 5.1 kV in 100 V steps and count 2 minutes.",
         "Set the operating voltage on the plateau, 4.1 kV.",
         "Move the source away from the wire in steps; finer steps near the end of the range.",
         "Correct each rate for the solid angle: multiply by d^2.",
         "The mean range is where the corrected rate falls to half its value near the wire."],
        [_q("A spark counter ignores beta particles because", ["Their ionisation is too sparse to trigger a spark",
            "They are absorbed by the wire", "They are too fast to count"], 0, "Only dense tracks start the spark."),
         _q("Range straggling means", ["Equal-energy alphas stop at slightly different depths", "Alphas change energy "
            "in vacuum", "The counter misses alphas"], 0, "The energy loss is a statistical process.")],
        [DU, NNDC, {"title": "R. D. Evans, The Atomic Nucleus (McGraw-Hill): Geiger's rule R = 0.318 E^1.5 cm of air (E in "
                             "MeV, 4-7 MeV)", "note": "from memory - verify"}, ILLUS, SIM],
        {"params": {"t": 1.0e7}, "reading": "res", "textbook": "pm9_geiger"}, RAD_SAFE + " " + HV_SAFE,
        "Spark counter and source carriage", "A wire-and-plate spark counter facing an alpha source on a micrometer carriage.",
        [{"say": "The spark counter on its stand faces the Am-241 source on the carriage; the EHT unit and scaler are on the right."}])


def prop_counter() -> dict:
    return _mk(
        "pm9-prop-counter", "pm9_prop", G_NUC, CH_NUC, "Proportional counter: gas gain and energy resolution at 5.9 keV",
        "Record the Fe-55 X-ray line of an argon-methane proportional counter on a multichannel analyser: the peak "
        "channel against voltage (gas gain), and the energy resolution of the line. SIMULATED DATA.",
        {"x": 1700.0, "s": 0.0},
        [knob("x", "Counter voltage or MCA channel", "x", 0, 2200, 1, 1700),
         knob("E", "This line (its energy is hidden)", "E", 1.0, 100.0, 0.001, 5.895, "keV", hidden=True)],
        [inst("y", "readout", "Reading", "y", digits=1)],
        "An X-ray absorbed in the gas makes about E / W ion pairs (W = 26.2 eV for argon), and each electron starts an "
        "avalanche near the thin anode wire: the pulse is M E / W electrons, PROPORTIONAL to the energy, with a gas "
        "gain M that grows exponentially with the voltage. The line width comes from two kinds of statistics: the "
        "number of ion pairs (Fano factor F) and the avalanche size (relative variance b), so the resolution is "
        "FWHM / E = 2.355 sqrt((F + b) W / E). In argon an X-ray above 3.2 keV may also leave by an argon K X-ray, "
        "giving an ESCAPE peak 2.96 keV lower.",
        ["With the Fe-55 source on the window, raise the voltage from 1550 to 1850 V and note the peak channel.",
         "Plot ln(peak channel) against voltage: a straight line, the gas gain.",
         "Set 1700 V and record the spectrum around the 5.9 keV line, channel by channel.",
         "Find the centroid and the full width at half maximum.",
         "The resolution is FWHM / centroid (in per cent)."],
        [_q("The escape peak lies", ["2.96 keV below the full-energy line", "At twice the energy", "At the noise edge"],
            0, "An argon K X-ray carries that energy away."),
         _q("Raising the voltage by 77 V here", ["About doubles the gain", "Doubles the resolution",
                                                 "Changes nothing"], 0, "ln2 / 0.009 per volt.")],
        [DU, KNOLL, NNDC, ILLUS, SIM],
        {"params": {"Ntot": 1.0e12}, "reading": "res", "textbook": "pm9_presol"}, RAD_SAFE + " " + HV_SAFE,
        "Proportional counter and MCA", "An argon-methane proportional counter with a beryllium window, its preamplifier, NIM bin and a multichannel analyser.",
        [{"say": "The proportional counter with the Fe-55 source on its window, the NIM bin and the multichannel analyser."}])


def kurie() -> dict:
    return _mk(
        "pm9-kurie", "pm9_kurie", G_NUC, CH_NUC, "Beta spectrum and Kurie plot of Cs-137",
        "Record the beta spectrum of Cs-137 with an anthracene scintillation spectrometer, see the K conversion line, "
        "and find the end-point energy from the straight Kurie plot. SIMULATED DATA.",
        {"x": 100.0, "s": 0.0},
        [knob("x", "Spectrometer setting", "x", 0, 3000, 1, 100),
         knob("T1", "This decay (its end point is hidden)", "T1", 100, 3000, 0.1, 514.0, "keV", hidden=True)],
        [inst("y", "readout", "Counts", "y", digits=0)],
        "In beta decay the energy is shared with an antineutrino, so the electrons have every energy up to an end "
        "point. For an allowed transition N(W) dW = C F(Z, W) p W (W0 - W)^2 dW (W total energy in m c^2 units, p "
        "momentum in m c, F the Fermi function for the daughter's charge). The KURIE function K = sqrt(N / (p W F)) is "
        "then a straight line that meets the axis at W0. With a magnetic spectrometer the momentum window grows with p "
        "and K = sqrt(N / (F p^3)). Cs-137 also gives a sharp line of conversion electrons at 624 keV. Here the shape "
        "factor of forbidden decays and the detector response are left out: the plot is straight by construction.",
        ["Calibrate the spectrometer (energy or momentum against setting).",
         "Record the counts across the whole spectrum, past the end point.",
         "Note the conversion line, if any, beyond the continuum.",
         "Work out K for each point and plot it against W.",
         "Fit the straight middle part (35 to 85 % of the end): it meets the axis at W0; E0 = (W0 - 1) m c^2."],
        [_q("The beta spectrum is continuous because", ["An antineutrino shares the energy", "The detector is "
            "imperfect", "Electrons lose energy in the source"], 0, "That was Pauli's argument for the neutrino."),
         _q("A conversion line is", ["Electrons ejected by the excited daughter's own transition", "A gamma ray",
            "The end point"], 0, "The nucleus gives its energy to an atomic electron.")],
        [DU, IITK, NNDC, {"title": "K. S. Krane, Introductory Nuclear Physics (Wiley): Fermi theory, Kurie plot, "
                                   "non-relativistic Fermi function F = 2 pi eta / (1 - exp(-2 pi eta))",
                          "note": "cited from memory, not fetched - verify"}, ILLUS, SIM],
        {"params": {"Ntot": 1.0e14}, "reading": "res", "textbook": "pm9_endpoint"}, RAD_SAFE + " " + HV_SAFE,
        "Beta spectrometer", "A beta spectrometer with its source, detector and readout.",
        [{"say": "The spectrometer, the source in its holder, and the analyser that counts the electrons."}])


def angular_correlation() -> dict:
    return _mk(
        "pm9-angular-correlation", "pm9_angcorr", G_NUC, CH_NUC, "Directional correlation of the Co-60 gamma cascade",
        "Count prompt coincidences between two NaI(Tl) detectors as one swings from 90 to 180 degrees round a Co-60 "
        "source, take the chance rate off, and find the correlation coefficient a2. SIMULATED DATA.",
        {"x": 90.0, "s": 1.0},
        [knob("x", "Angle between the detectors", "x", 90, 180, 1, 90, "deg"),
         knob("a2", "This cascade (its a2 is hidden)", "a2", 0.0, 0.5, 0.0001, 0.125, hidden=True)],
        [inst("y", "readout", "Coincidence rate", "y", unit="per s", lc=0.001, digits=3)],
        "Co-60 decays to the 4+ level of Ni-60, which reaches the ground state by two gamma rays in cascade, 4+ -> 2+ "
        "(1173 keV) -> 0+ (1332 keV). The first gamma picks out the direction of the intermediate nucleus's spin, so "
        "the second is not emitted at random: W(theta) = 1 + a2 cos^2 theta + a4 cos^4 theta, with a2 = 1/8 and "
        "a4 = 1/24 for this pure E2-E2 cascade (W(180)/W(90) = 1.167). Coincidences are counted at each angle, the "
        "chance coincidences (measured with a delay in one arm) are taken off, and the ratios W(theta)/W(90) are "
        "fitted. Point detectors are assumed: the finite solid angle would reduce the coefficients slightly.",
        ["Set the fixed detector and the movable one 10 cm from the source on the protractor table.",
         "Put a long delay in one arm and count the chance coincidences.",
         "Remove the delay and count coincidences at 90, 105, 120, 135, 150, 165 and 180 degrees.",
         "Take the chance rate off and divide by the value at 90 degrees.",
         "Fit W(theta)/W(90) - 1 = a2 cos^2 + a4 cos^4."],
        [_q("The anisotropy appears because", ["The first gamma aligns the intermediate state's spin", "The source is "
            "not round", "The detectors differ"], 0, "Only the cascade's second photon carries the memory."),
         _q("Chance coincidences are found by", ["Delaying one arm", "Removing the source", "Turning off one "
            "detector"], 0, "A long delay destroys the true coincidences only.")],
        [DU, {"title": "D. R. Hamilton, Phys. Rev. 58, 122 (1940): directional correlation of successive quanta; for "
                       "4(2)2(2)0, a2 = 1/8, a4 = 1/24", "note": "from memory - verify"},
         {"title": "Ni-60 levels: 1173.2 and 1332.5 keV gamma rays of Co-60", "note": "from memory - verify"}, ILLUS, SIM],
        {"params": {"t": 1.0e12}, "reading": "res", "textbook": "pm9_a2"}, RAD_SAFE + " " + HV_SAFE,
        "Coincidence table", "Two NaI(Tl) detectors on a protractor table, one on a swinging arm, round a Co-60 source.",
        [{"say": "The fixed detector, the swinging one on the protractor table, and the coincidence unit."}])


# ================================================================================================= solid state
def hall_temperature() -> dict:
    return _mk(
        "pm9-hall-temperature", "pm9_hallt", G_SOL, CH_SOL, "Hall effect in p-type germanium from 77 K to 420 K",
        "Measure the Hall voltage and the sample voltage of a lightly doped germanium slab from liquid-nitrogen "
        "temperature to 420 K, and find the band gap from the intrinsic region and the mobility against temperature.",
        {"x": 300.0, "s": 0.0},
        [knob("x", "Sample temperature", "x", 77, 420, 1, 300, "K"),
         knob("Eg0", "This crystal (its band gap is hidden)", "Eg0", 0.3, 1.5, 0.0001, 0.782, "eV", hidden=True)],
        [inst("y", "readout", "Hall voltage", "y", unit="mV", lc=0.001, digits=3)],
        "In a field B a current I through a slab of thickness d gives a Hall voltage V_H = R_H I B / d. At low "
        "temperature the holes from the acceptors carry the current and R_H = 1 / (p e). As the crystal warms, "
        "electron-hole pairs are made across the gap: ni grows as T^1.5 exp(-Eg / 2kT), and because electrons are "
        "about twice as mobile as holes, R_H of a p-type crystal falls, passes through zero and turns negative. In "
        "the intrinsic region n = p = ni and R_H = (mu_p - mu_n) / (e ni (mu_p + mu_n)), so ln(|R_H| T^1.5) against 1/T "
        "is a line of slope Eg0 / 2k (Eg0 is the gap extrapolated linearly to 0 K). The Hall mobility is |R_H| sigma.",
        ["Mount the slab on the probe, lower it into the cryostat and fill the dewar: 77 K.",
         "With 1 mA and 0.3 T, read V_H (reverse the field and average) and the voltage along the slab.",
         "Warm in steps up to 420 K, with small steps above 360 K.",
         "In the intrinsic region plot ln(|R_H| T^1.5) against 1/T: the slope is Eg0 / 2k.",
         "Work out the Hall mobility |R_H| sigma at each temperature."],
        [_q("The Hall voltage of p-type germanium changes sign on heating because", ["Electrons are more mobile than "
            "holes", "The holes freeze out", "The field reverses"], 0, "Once n ~ p the faster electrons win."),
         _q("In the intrinsic region the carrier density grows as", ["T^1.5 exp(-Eg / 2kT)", "T", "exp(-Eg / kT)"], 0,
            "n = p = ni.")],
        [DU, IITK, SZE, ILLUS, SIM],
        {"reading": "res", "textbook": "pm9_eg0", "tol": 0.01}, COLD_SAFE + " " + HOT_SAFE,
        "Hall probe between the magnet poles", "A germanium Hall slab on a temperature-controlled probe between the poles of an electromagnet.",
        [{"say": "The electromagnet, the Hall probe in its cryostat between the poles, and the current source and voltmeters."}])


def two_probe() -> dict:
    return _mk(
        "pm9-two-probe", "pm9_twop", G_SOL, CH_SOL, "Two-probe conductivity of germanium and its band gap",
        "Pass a constant current through an intrinsic germanium bar in a furnace, read the voltage across the same two "
        "probes from 300 to 420 K, and find the conductivity and the band gap.",
        {"x": 300.0, "s": 0.0},
        [knob("x", "Furnace temperature", "x", 290, 430, 1, 300, "K"),
         knob("Eg0", "This crystal (its band gap is hidden)", "Eg0", 0.3, 1.5, 0.0001, 0.782, "eV", hidden=True)],
        [inst("y", "readout", "Voltage across the probes", "y", unit="mV", lc=0.001, digits=3)],
        "A constant current I flows through a bar of length L and cross-section A, and the voltage is read across the "
        "same two contacts, so V = I (L / (sigma A) + 2 Rc). For intrinsic germanium sigma = e ni (mu_n + mu_p); with "
        "ni ~ T^1.5 exp(-Eg0 / 2kT) and lattice mobilities ~ T^-1.5 the powers cancel and ln sigma against 1/T is a "
        "straight line of slope -Eg0 / 2k. The two-probe method includes the contact resistances Rc: harmless for a "
        "high-resistance bar, a large error for a good conductor (that is why the four-probe method exists).",
        ["Clamp the bar between the two probes and put it in the furnace.",
         "Set the constant-current source to 100 microamperes.",
         "Heat in 10 K steps to 420 K, waiting for each temperature to settle, and read the voltage.",
         "Work out sigma = L I / (A V) at each temperature.",
         "Plot ln sigma against 1/T: the slope is -Eg0 / 2k."],
        [_q("The two-probe reading includes", ["The contact resistances", "Only the bulk", "The leads' capacitance"], 0,
            "Current and voltage use the same contacts."),
         _q("For an intrinsic semiconductor sigma rises with T because", ["More carriers cross the gap", "The mobility "
            "rises", "The bar expands"], 0, "The exponential wins over the falling mobility.")],
        [IITK, SGGU, SZE, ILLUS, SIM],
        {"reading": "res", "textbook": "pm9_twop"}, HOT_SAFE + " " + EL_SAFE,
        "Furnace with a two-probe holder", "A tubular furnace with the bar clamped between two probes and a thermocouple beside it.",
        [{"say": "The furnace with the bar between its probes, the constant-current source and the voltmeter."}])


def diode_ideality() -> dict:
    return _mk(
        "pm9-diode-ideality", "pm9_diode", G_SOL, CH_SOL, "Band gap and ideality factor of a silicon diode",
        "Drive a silicon diode at two fixed currents in an oil bath from 300 to 380 K, find its ideality factor and "
        "saturation current at each temperature, and the band gap from ln(I0 / T^3) against 1/T.",
        {"x": 300.0, "s": 0.0},
        [knob("x", "Bath temperature", "x", 290, 400, 1, 300, "K"),
         knob("Eg0", "This diode (its band gap is hidden)", "Eg0", 0.3, 1.6, 0.0001, 1.206, "eV", hidden=True)],
        [inst("y", "readout", "Diode voltage at the first current", "y", unit="mV", lc=0.1, digits=1)],
        "A p-n junction follows I = I0 (exp(V / (n Vt)) - 1) with Vt = kT / e and an ideality factor n between 1 "
        "(diffusion) and 2 (recombination in the depletion layer). At two currents a decade apart the voltages differ "
        "by n Vt ln 10, which gives n; then I0 = I1 / (exp(V1 / (n Vt)) - 1). The saturation current grows as "
        "I0 = C T^3 exp(-Eg0 / kT), so ln(I0 / T^3) against 1/T is a straight line of slope -Eg0 / k, Eg0 being the gap "
        "extrapolated linearly to 0 K. Series resistance is neglected (small currents).",
        ["Put the diode in the oil bath next to the thermometer, leads out.",
         "At each temperature from 300 to 380 K set 0.1 mA and 1 mA in turn and read the diode voltage.",
         "n = (V2 - V1) / (Vt ln 10) at each temperature.",
         "I0 = I1 / (exp(V1 / (n Vt)) - 1).",
         "Plot ln(I0 / T^3) against 1/T: Eg0 = -k x slope."],
        [_q("An ideality factor near 2 means", ["Recombination in the depletion layer dominates", "Pure diffusion "
            "current", "A short circuit"], 0, "n = 1 for ideal diffusion."),
         _q("At a fixed current the diode voltage", ["Falls as the diode warms", "Rises as it warms", "Does not change"],
            0, "About -2 mV per kelvin for silicon.")],
        [DU, SZE, ILLUS, SIM],
        {"reading": "res", "textbook": "pm9_eg0"}, HOT_SAFE + " " + EL_SAFE,
        "Diode in an oil bath", "A diode on long leads in a stirred oil bath on a hot plate, with a thermometer.",
        [{"say": "The diode in the oil bath on the hot plate, the constant-current source and the millivoltmeter."}])


def photoconductivity() -> dict:
    return _mk(
        "pm9-photoconductivity", "pm9_photoc", G_SOL, CH_SOL, "Photoconductivity of a CdS cell",
        "Measure the photocurrent of a CdS cell against the lamp distance, its spectral response through a "
        "monochromator, and its decay when the light is cut off; find the band gap from the long-wavelength cut-off.",
        {"x": 20.0, "s": 0.0},
        [knob("x", "Lamp distance, wavelength or time", "x", 0, 800, 0.001, 20),
         knob("Eg", "This film (its band gap is hidden)", "Eg", 0.5, 4.0, 0.0001, 2.42, "eV", hidden=True)],
        [inst("y", "readout", "Photocurrent", "y", unit="µA", lc=0.01, digits=2)],
        "Light with photon energy above the band gap makes electron-hole pairs, and the conductivity rises. The "
        "photocurrent grows with the illumination as I ~ Phi^gamma, often with gamma below 1 because recombination "
        "speeds up as more carriers are made. Below the band gap the material is transparent and the response falls "
        "away: the wavelength where it drops to half its plateau gives Eg = h c / lambda_c. When the light is cut off "
        "the extra carriers recombine and the current decays with a time constant tau (here the lifetime is long for "
        "CdS). The response here is relative, for a constant photon flux at every wavelength.",
        ["Put the cell in its holder at the end of the rail; lamp at 10 cm.",
         "Move the lamp from 10 to 50 cm and read the photocurrent (illumination ~ 1/d^2).",
         "Put the monochromator in front of the cell; read the current from 400 to 700 nm in 5 nm steps.",
         "Close the shutter and read the current at 25 ms intervals.",
         "The cut-off wavelength (half the plateau) gives Eg = 1239.8 / lambda_c eV."],
        [_q("A photoconductor does not respond beyond the cut-off wavelength because", ["The photons cannot cross the "
            "band gap", "The lamp is too weak", "The cell is too thin"], 0, "h c / lambda < Eg."),
         _q("gamma below 1 means", ["Doubling the light less than doubles the current", "The current falls with "
            "light", "The cell saturates at once"], 0, "Recombination grows with the carrier density.")],
        [DU, IITK, {"title": "CRC Handbook / S. M. Sze: band gaps at 300 K, CdS 2.42 eV, CdSe 1.74 eV",
                    "note": "from memory - verify"}, ILLUS, SIM],
        {"reading": "res", "textbook": "pm9_egphoto"}, HOT_SAFE + " CdS is toxic: never break or scratch the cell.",
        "Optical rail with lamp, monochromator and cell", "A lamp on an optical rail, a grating monochromator and the CdS cell in its holder.",
        [{"say": "The lamp on its rail, the monochromator, and the CdS cell wired to the microammeter."}])


def ac_susceptibility() -> dict:
    return _mk(
        "pm9-ac-susceptibility", "pm9_acsusc", G_SOL, CH_SOL, "AC susceptibility of a YBCO pellet",
        "Cool a sintered YBCO pellet inside a mutual-inductance coil set in a liquid-nitrogen cryostat and read the "
        "in-phase and loss signals on a lock-in while it warms: find the diamagnetic onset and Tc.",
        {"x": 100.0, "s": 0.0},
        [knob("x", "Sample temperature", "x", 77, 110, 0.1, 100, "K"),
         knob("Tc", "This pellet (its Tc is hidden)", "Tc", 20, 140, 0.01, 92, "K", hidden=True)],
        [inst("y", "readout", "In-phase signal", "y", unit="µV", lc=0.01, digits=2)],
        "A primary coil drives a small alternating field; two opposed secondary coils cancel each other when empty. A "
        "superconducting sample in one of them expels the field (it is a perfect diamagnet), so the secondary picks up "
        "an in-phase signal proportional to chi' = -1 times the shielded volume. On warming the shielding fails over a "
        "narrow range: the diamagnetic ONSET is where chi' first departs from zero, and Tc is taken at the midpoint of "
        "the step. Where the flux enters, the sample dissipates the drive and the out-of-phase signal chi'' peaks.",
        ["Mount the pellet in the secondary coil on the insert and cool it in the liquid-nitrogen cryostat to 80 K.",
         "Set the lock-in to the drive frequency and null the empty-coil signal.",
         "Warm in steps (0.5 K near the transition) and read the in-phase and out-of-phase signals.",
         "The onset is where the in-phase signal starts to leave its full value.",
         "Tc is the midpoint of the step; the chi'' peak lies there too."],
        [_q("The in-phase signal measures", ["The shielded volume (diamagnetism)", "The resistance", "The heat capacity"],
            0, "chi' = -1 for full shielding."),
         _q("The out-of-phase signal peaks at Tc because", ["Flux moving in the sample dissipates the drive",
            "The coil heats", "The lock-in saturates"], 0, "Losses are largest during flux entry.")],
        [IITK, {"title": "M. K. Wu et al., Phys. Rev. Lett. 58, 908 (1987): YBa2Cu3O7 superconducting near 92 K",
                "note": "from memory - verify"}, ILLUS, SIM],
        {"reading": "res", "textbook": "pm9_tc"}, COLD_SAFE,
        "Cryostat with the coil insert", "A liquid-nitrogen cryostat with a mutual-inductance coil insert, a heater and a sensor.",
        [{"say": "The cryostat holding the coil insert, the temperature controller and the lock-in amplifier."}])


# ================================================================================================= modern
def stefan() -> dict:
    return _mk(
        "pm9-stefan", "pm9_stefan", G_MOD, CH_MOD, "Stefan's constant from a cooling black body",
        "Heat a blackened hollow copper body inside an evacuated enclosure, read its temperature as it cools by "
        "radiation alone, and find Stefan's constant from the cooling rate against T^4 - T0^4.",
        {"x": 0.0, "s": 0.0},
        [knob("x", "Time or lamp voltage", "x", 0, 1000, 0.1, 0),
         knob("sigma", "Nature (Stefan's constant is hidden)", "sigma", 1e-8, 1e-7, 1e-12, 5.670374419e-8, "W/m²K⁴",
              hidden=True)],
        [inst("y", "readout", "Reading", "y", digits=1)],
        "A body of emissivity e and area A at temperature T inside an enclosure at T0 loses heat by radiation at the "
        "rate sigma e A (T^4 - T0^4) (Stefan-Boltzmann). In vacuum there is no convection, and thin supports make "
        "conduction small, so m c dT/dt = -sigma e A (T^4 - T0^4): the cooling rate, read off the cooling curve, plotted "
        "against T^4 - T0^4 is a straight line through the origin of slope sigma e A / (m c). The second method runs a "
        "tungsten lamp at several voltages: at equilibrium the electrical power V I is radiated, P = sigma e_W A_f T^4, "
        "the filament temperature coming from its resistance (R / R0 = (T / T0)^1.2).",
        ["Heat the body to about 620 K inside the enclosure and pump the enclosure down.",
         "Switch the heater off and read the thermocouple every 20 s as the body cools.",
         "Work out dT/dt at each reading from its neighbours.",
         "Plot m c (-dT/dt) / (e A) against T^4 - T0^4: the slope through the origin is sigma.",
         "With the lamp: read V and I at several voltages, find T from R and plot V I against e_W A_f T^4."],
        [_q("The enclosure is evacuated so that", ["Only radiation removes heat", "The body cools faster",
            "The thermocouple works"], 0, "No air, no convection."),
         _q("The rate of loss doubles when", ["T^4 - T0^4 doubles", "T doubles", "T0 halves"], 0,
            "Stefan-Boltzmann law.")],
        [IITK, SGGU, {"title": "CODATA 2018: sigma = 5.670374419e-8 W m^-2 K^-4 (exact, from h, k, c)"},
         {"title": "Copper specific heat 385 J/kg K; lamp-black emissivity about 0.97; tungsten emissivity taken as "
                   "0.35 and R ~ T^1.2", "note": "from memory - verify (the tungsten values vary with temperature)"},
         ILLUS, SIM],
        {"reading": "res", "textbook": "pm9_sigma"}, HOT_SAFE,
        "Stefan apparatus", "A blackened copper body on thin supports inside an evacuated enclosure, or a tungsten lamp with its meters.",
        [{"say": "The blackened body inside the bell jar, its thermocouple meter and the stopwatch."}])


def cu_xrays() -> dict:
    return _mk(
        "pm9-cu-xrays", "pm9_cuxray", G_MOD, CH_MOD, "Characteristic X-rays of copper and the nickel filter",
        "Scan the X-ray spectrum of a copper-anode tube with a LiF crystal, find the K-alpha and K-beta lines and their "
        "wavelengths, and see what a nickel foil does to them. SIMULATED DATA.",
        {"x": 40.0, "s": 0.0},
        [knob("x", "Counter angle 2 theta", "x", 30, 60, 0.1, 40, "deg"),
         knob("la1", "This anode (its K-alpha1 wavelength is hidden)", "la1", 0.5, 3.0, 0.000001, 1.540562, "Å",
              hidden=True)],
        [inst("y", "readout", "Count rate", "y", unit="counts/s", lc=0.1, digits=1)],
        "Electrons stopping in the copper anode give a continuous bremsstrahlung spectrum, ending at the Duane-Hunt "
        "limit lambda_min = h c / e V, and sharp lines where an electron fills a K-shell hole: K-alpha (from L) and "
        "K-beta (from M). A crystal of spacing d reflects wavelength lambda at the Bragg angle, 2 d sin theta = lambda, "
        "into the counter at 2 theta. A nickel foil has its K absorption edge (1.488 A) between the two copper lines: "
        "it absorbs K-beta strongly and passes most of K-alpha, which is how diffractometers get nearly single-"
        "wavelength radiation. K-alpha1 and K-alpha2 are not resolved here; their weighted mean is measured.",
        ["Set 30 kV and the LiF (200) crystal (2d = 4.027 A) on the goniometer.",
         "Scan the counter from 2 theta = 36 to 50 degrees in 0.1 degree steps.",
         "Put the nickel foil in the beam and scan again.",
         "Find the centroid of the strongest line: lambda = 2 d sin theta.",
         "Compare the K-beta / K-alpha ratio with and without the filter."],
        [_q("The nickel foil removes K-beta because", ["Its K edge lies between K-alpha and K-beta", "It is thick",
            "Nickel fluoresces"], 0, "Photons just above an edge are strongly absorbed."),
         _q("K-alpha is emitted when", ["An L electron fills a K hole", "An M electron fills a K hole",
            "An electron is stopped"], 0, "K-beta is the M to K transition.")],
        [IITK, {"title": "Cu K X-ray wavelengths: K-alpha1 1.540562, K-alpha2 1.544390, K-beta1 1.392218 A (Hoelzer et al., "
                         "Phys. Rev. A 56, 4554 (1997)); LiF (200) spacing 2.0135 A",
                "note": "from memory - verify"},
         {"title": "NIST XCOM / FFAST: nickel mass attenuation about 49 cm^2/g at Cu K-alpha and about 276 cm^2/g at "
                   "Cu K-beta; Ni K edge 1.48802 A; Ni density 8.908 g/cm^3",
          "note": "from memory - verify; the power-law interpolation either side of the edge is an approximation"},
         ILLUS, SIM],
        {"params": {"t": 1.0e8}, "reading": "res", "textbook": "pm9_kalpha"},
        "X-rays: work only with the lead-glass door closed and the interlock on; never bypass it.",
        "X-ray unit", "A copper-anode X-ray tube in a shielded cabinet with a crystal goniometer and a counter.",
        [{"say": "The shielded X-ray cabinet with the goniometer: the crystal on the table, the counter on the arm."}])


# ================================================================================================= waves and electronics
def lc_lattice() -> dict:
    return _mk(
        "pm9-lc-lattice", "pm9_lclat", G_WAV, CH_WAV, "Dispersion of a monatomic LC lattice",
        "Drive a ladder of identical L-C sections, read the phase shift per section on a CRO at many frequencies, and "
        "find the dispersion relation and the cut-off frequency of the 'lattice'.",
        {"x": 1000.0, "s": 0.0},
        [knob("x", "Generator frequency", "x", 50, 30000, 1, 1000, "Hz"),
         knob("L", "The coils (their inductance is hidden)", "L", 1e-4, 1.0, 1e-6, 1e-2, "H", hidden=True)],
        [inst("y", "readout", "Phase shift per section", "y", unit="deg", lc=0.5, digits=1)],
        "A ladder of series inductors L and shunt capacitors C is the electrical twin of a chain of masses and springs "
        "(C plays the mass, 1/L the spring). A wave of angular frequency w shifts its phase by phi per section, with "
        "w = (2 / sqrt(LC)) sin(phi / 2): the same dispersion as lattice vibrations. Above the CUT-OFF frequency "
        "fc = 1 / (pi sqrt(LC)) (phi = pi) no wave travels. With alternating capacitors C1 and C2 the 'diatomic' chain "
        "splits into an acoustic and an optical branch with a band GAP between sqrt(2 / L C1) and sqrt(2 / L C2).",
        ["Connect the generator to the first section and the CRO across the input of one section and the output of the next.",
         "At each frequency set the generator and read the phase shift per section from the Lissajous figure.",
         "Go up in steps until the phase reaches 180 degrees.",
         "Plot frequency against sin(phi/2): a straight line through the origin of slope fc.",
         "Compare fc with 1 / (pi sqrt(LC))."],
        [_q("At the cut-off the phase shift per section is", ["180 degrees", "90 degrees", "0"], 0,
            "Neighbouring sections swing in opposite phase."),
         _q("The diatomic lattice shows a band gap because", ["The two capacitors differ", "The coils saturate",
            "Of losses"], 0, "Like two different masses.")],
        [SGGU, {"title": "C. Kittel, Introduction to Solid State Physics, ch. 4: dispersion of a monatomic and a diatomic chain",
                "note": "cited from memory - verify"}, ILLUS, SIM],
        {"reading": "res", "textbook": "pm9_lccut"}, EL_SAFE,
        "LC lattice board", "A board of 20 identical L-C sections with test points, a signal generator and a dual-trace CRO.",
        [{"say": "The lattice board with its row of coils and capacitors, the generator and the CRO."}])


def pulse_echo() -> dict:
    return _mk(
        "pm9-pulse-echo", "pm9_echo", G_WAV, CH_WAV, "Velocity of sound in aluminium by pulse echo",
        "Couple an ultrasonic probe to an aluminium block, read the arrival times of the back-wall echoes on the CRO, "
        "and find the longitudinal velocity of sound and the longitudinal modulus.",
        {"x": 1.0, "s": 0.0},
        [knob("x", "Echo number", "x", 1, 8, 1, 1),
         knob("v", "This block (its sound velocity is hidden)", "v", 1000, 12000, 1, 6320, "m/s", hidden=True)],
        [inst("y", "readout", "Echo time", "y", unit="µs", lc=0.01, digits=2)],
        "A piezoelectric probe sends a short ultrasonic pulse into the block and then listens. The pulse bounces back "
        "and forth between the faces, and the n-th echo returns after t_n = 2 n d / v. The slope of t_n against n "
        "gives v = 2 d / slope, free of the delay in the probe and the couplant. The longitudinal wave speed gives the "
        "P-wave modulus M = rho v^2 (for a thin rod it would be Young's modulus; in a bulk block it is M = E (1 - nu) "
        "/ ((1 + nu)(1 - 2 nu))). Successive echoes grow weaker through absorption and beam spreading.",
        ["Measure the block's thickness with a vernier (50.0 mm) and weigh it for its density.",
         "Put a drop of couplant on the block and press the probe on.",
         "Set the CRO time base so that six echoes are seen.",
         "Read the time of each echo's leading edge.",
         "Fit t against n: v = 2 d / slope; M = rho v^2."],
        [_q("Using the slope of t_n against n removes", ["The fixed delay of the probe", "The block's thickness",
            "Attenuation"], 0, "A constant offset only moves the line."),
         _q("A longitudinal wave in a bulk block measures", ["The P-wave modulus rho v^2", "The shear modulus",
            "Poisson's ratio alone"], 0, "Not Young's modulus, unless the sample is a thin rod.")],
        [DU, {"title": "Olympus NDT, Ultrasonic transducers technical notes, material sound velocities: aluminium 6320, "
                       "mild steel about 5900, acrylic (Perspex) 2730 m/s; densities 2700, 7850, 1180 kg/m^3",
              "note": "from memory - verify"}, ILLUS, SIM],
        {"reading": "res", "textbook": "pm9_v"}, EL_SAFE,
        "Pulse-echo set", "An ultrasonic probe pressed on a metal block, a pulser-receiver and a CRO.",
        [{"say": "The probe on the block, the pulser-receiver and the CRO showing the train of echoes."}])


def sound_cro() -> dict:
    return _mk(
        "pm9-sound-cro", "pm9_sound", G_WAV, CH_WAV, "Velocity of sound in air by the CRO phase method",
        "Drive a loudspeaker at 3 kHz in a tube, put the microphone signal against the speaker signal on the CRO, and "
        "move the microphone to find each straight-line Lissajous figure: half a wavelength apart.",
        {"x": 0.0, "s": 0.0},
        [knob("x", "Straight-line figure number", "x", 0, 9, 1, 0),
         knob("tc", "The room (its temperature is hidden)", "tc", -10, 45, 0.1, 27, "°C", hidden=True)],
        [inst("y", "readout", "Microphone position", "y", unit="mm", lc=0.5, digits=1)],
        "With the speaker signal on X and the microphone signal on Y, the CRO draws an ellipse whose shape follows the "
        "phase difference between them. Each time the microphone moves half a wavelength the phase changes by 180 "
        "degrees and the figure closes into a straight line, tilted alternately one way and the other. The spacing "
        "of the straight-line positions is lambda / 2, so v = f lambda. The speed of sound in dry air rises with "
        "temperature as v = 331.3 sqrt(1 + t / 273.15) m/s.",
        ["Set the generator to 3000 Hz and the CRO in X-Y mode.",
         "Slide the microphone from the speaker until the figure is a straight line; read the scale.",
         "Move on to each next straight line (alternate tilt) and read the scale.",
         "Fit position against line number: the slope is lambda / 2.",
         "v = 2 f slope; compare with 331.3 sqrt(1 + t / 273.15)."],
        [_q("Consecutive straight lines are", ["Half a wavelength apart", "A wavelength apart", "A quarter apart"], 0,
            "The phase changes by pi."),
         _q("The CRO method avoids", ["Judging loudness by ear", "Using a microphone", "Using a generator"], 0,
            "A straight line is sharp to see.")],
        [DU, {"title": "Speed of sound in dry air 331.3 m/s at 0 degrees C, v ~ sqrt(T)", "note": "from memory - verify"},
         ILLUS, SIM],
        {"reading": "res", "textbook": "pm9_vsound"}, EL_SAFE + " Keep the volume low.",
        "Sound tube with speaker and microphone", "A tube with a loudspeaker at one end, a microphone on a graduated slide, a generator and a CRO.",
        [{"say": "The loudspeaker at the end of the tube, the microphone on its slide, the generator and the CRO."}])


def lecher_wire() -> dict:
    return _mk(
        "pm9-lecher-wire", "pm9_lecher", G_WAV, CH_WAV, "Lecher wire: wavelength, frequency and dielectric constant",
        "Find the current nodes on a Lecher line driven by a UHF oscillator, first in air (wavelength and frequency) "
        "and then with the wires in a trough of transformer oil (its dielectric constant).",
        {"x": 0.0, "s": 0.0},
        [knob("x", "Node number", "x", 0, 12, 1, 0),
         knob("eps", "The liquid (its dielectric constant is hidden)", "eps", 1.0, 10.0, 0.001, 2.2, hidden=True)],
        [inst("y", "readout", "Bridge position", "y", unit="cm", lc=0.1, digits=1)],
        "Two parallel wires guide an electromagnetic wave; with the far end shorted, standing waves form and a "
        "sliding shorting bridge finds the positions where the detector current dips (or the bulb lights): they are "
        "half a wavelength apart. In air the wave travels at c, so lambda0 = c / f gives the frequency. When the "
        "space between the wires is filled with a liquid of dielectric constant eps, the wave slows to c / sqrt(eps) "
        "and lambda = lambda0 / sqrt(eps), so eps = (lambda0 / lambda)^2.",
        ["Couple the oscillator loosely to the end of the line.",
         "Slide the bridge along the wires in air and note each node position.",
         "Fill the trough with transformer oil to cover the wires.",
         "Find the nodes again.",
         "lambda = twice the node spacing; f = c / lambda0; eps = (lambda0 / lambda)^2."],
        [_q("Nodes on a Lecher line are spaced", ["lambda / 2", "lambda", "lambda / 4"], 0,
            "As in any standing wave."),
         _q("In oil the nodes come closer because", ["The wave travels slower", "The frequency rises",
            "The wires shorten"], 0, "v = c / sqrt(eps).")],
        [DU, {"title": "SI: c = 299792458 m/s (exact). Transformer (mineral) oil dielectric constant about 2.2",
              "note": "the oil value is from memory - verify"}, ILLUS, SIM],
        {"reading": "res", "textbook": "pm9_eps"}, EL_SAFE + " Do not touch the oscillator's output while it is on.",
        "Lecher line", "Two parallel wires on insulating posts over a trough, a UHF oscillator at one end, a sliding bridge.",
        [{"say": "The UHF oscillator, the two wires over their trough and the sliding bridge with its detector."}])


def fourier_analysis() -> dict:
    return _mk(
        "pm9-fourier", "pm9_fourier", G_WAV, CH_WAV, "Fourier analysis of a square wave",
        "Feed a square wave to a tunable analyser, read the amplitude of each harmonic, and compare the Fourier "
        "coefficients with the series of the waveform.",
        {"x": 1.0, "s": 0.0},
        [knob("x", "Harmonic number", "x", 1, 9, 1, 1),
         knob("shape", "The waveform (its kind is hidden)", "shape", 0, 2, 1, 0, hidden=True)],
        [inst("y", "readout", "Harmonic amplitude", "y", unit="V", lc=0.001, digits=3)],
        "Any periodic waveform is a sum of sines and cosines at the fundamental frequency and its multiples. A square "
        "wave of amplitude A holds only odd harmonics, of amplitude 4A / (n pi): they fall as 1/n. A triangular wave "
        "also has only odd harmonics, but they fall as 1/n^2 (8A / (n pi)^2). A half-wave rectified sine has a "
        "constant part A / pi, a fundamental A / 2 and even harmonics 2A / (pi (n^2 - 1)). A tuned filter (or a "
        "spectrum analyser) picks out one harmonic at a time and the CRO reads its amplitude.",
        ["Connect the generator to the analyser and set 1 kHz, amplitude 2 V.",
         "Tune the analyser to the fundamental and read its amplitude.",
         "Tune to each harmonic up to the seventh and read its amplitude.",
         "Divide each amplitude by the fundamental's.",
         "Compare with the Fourier series of the waveform."],
        [_q("A square wave contains", ["Only odd harmonics, falling as 1/n", "All harmonics", "Only even harmonics"], 0,
            "Its half-wave symmetry kills the even ones."),
         _q("A half-wave rectified sine contains", ["A constant, the fundamental and even harmonics", "Only odd "
            "harmonics", "Only the fundamental"], 0, "2A / (pi (n^2 - 1)) for even n.")],
        [SGGU, {"title": "Fourier series of standard waveforms (G. B. Arfken and H. J. Weber, Mathematical Methods for "
                          "Physicists)", "note": "cited from memory - verify"}, ILLUS, SIM],
        {"reading": "res", "textbook": "pm9_fratio"}, EL_SAFE,
        "Waveform analyser", "A function generator, a tunable harmonic analyser and a CRO.",
        [{"say": "The function generator, the tunable analyser and the CRO showing the selected harmonic."}])


def transducers() -> dict:
    return _mk(
        "pm9-transducers", "pm9_trans", G_WAV, CH_WAV, "Characteristics of a thermistor",
        "Heat an NTC thermistor in a water bath, read its resistance from 25 to 85 degrees C, and find its sensitivity "
        "(the B constant) and how far it is from linear.",
        {"x": 25.0, "s": 0.0},
        [knob("x", "Stimulus (temperature, strain, displacement)", "x", -10, 1000, 0.1, 25),
         knob("typ", "The transducer (hidden)", "typ", 0, 3, 1, 0, hidden=True)],
        [inst("y", "readout", "Output", "y", digits=3)],
        "A transducer turns one quantity into an electrical one, and its datasheet gives a SENSITIVITY (output per "
        "unit input) and a LINEARITY (how far the output strays from a straight line). An NTC thermistor's resistance "
        "falls steeply with temperature, R = R25 exp(B (1/T - 1/298.15 K)): very sensitive but far from linear, so its "
        "B constant is found from ln R against 1/T. A strain gauge changes resistance by GF x strain; an LVDT gives a "
        "voltage proportional to its core's displacement near the centre; a thermocouple gives an EMF that grows "
        "almost linearly with the temperature difference of its junctions.",
        ["Put the transducer in its fixture with the meter connected.",
         "Step the stimulus over its range and read the output at each step.",
         "Plot the output against the stimulus.",
         "Fit the straight line (or ln R against 1/T for the thermistor): the slope is the sensitivity.",
         "The largest departure from the line, as a per cent of full scale, is the non-linearity."],
        [_q("An NTC thermistor's resistance", ["Falls as the temperature rises", "Rises with temperature", "Does not "
            "change"], 0, "Negative temperature coefficient."),
         _q("A quarter bridge with a strain gauge gives about", ["Vex GF e / 4", "Vex GF e", "Vex / GF"], 0,
            "For small strain e.")],
        [SGGU, {"title": "NIST ITS-90 thermocouple tables, type K: 2.023 mV at 50 C and 4.096 mV at 100 C (cold junction 0 C)",
                "note": "from memory - verify; the quadratic through these points is an approximation"},
         {"title": "NTC thermistor B = 3950 K, R25 = 10 kohm; foil gauge factor 2.0; LVDT 50 mV/mm",
          "note": "illustrative datasheet values of these particular devices"}, SIM],
        {"reading": "res", "textbook": "pm9_sens"}, HOT_SAFE + " " + EL_SAFE,
        "Transducer test bench", "A bench with a water bath, a cantilever, a micrometer stage and a digital meter.",
        [{"say": "The transducer in its fixture, the stimulus beside it and the digital meter reading its output."}])


def microwave_bragg() -> dict:
    return _mk(
        "pm9-microwave-bragg", "pm9_mwbragg", G_WAV, CH_MW, "Bragg diffraction of microwaves by a ball lattice",
        "Turn a cubic lattice of metal balls on the turntable of a microwave goniometer with the receiver at twice the "
        "angle, find the first- and second-order Bragg reflections, and the lattice spacing.",
        {"x": 10.0, "s": 0.0},
        [knob("x", "Crystal angle theta", "x", 5, 70, 0.5, 10, "deg"),
         knob("d", "This lattice (its plane spacing is hidden)", "d", 1.0, 10.0, 0.01, 4.0, "cm", 0.01, hidden=True)],
        [inst("y", "readout", "Detector reading", "y", unit="%", lc=0.1, digits=1)],
        "A 'crystal' of metal balls spaced a few centimetres apart is to 3 cm microwaves what a real crystal is to "
        "X-rays. The waves scattered from successive planes of balls add up only where the path difference 2 d sin "
        "theta is a whole number of wavelengths: the Bragg law 2 d sin theta = n lambda. The crystal is turned by "
        "theta and the receiver by 2 theta (so the angle of reflection equals the angle of incidence), and sharp "
        "maxima appear at the Bragg angles. With lambda known from the oscillator frequency (10.5 GHz, 2.855 cm), "
        "each maximum gives d.",
        ["Set the transmitter and receiver horns on the goniometer and the ball lattice on the turntable, (100) planes facing the beam.",
         "Switch the Gunn oscillator on (10.5 GHz).",
         "Turn the crystal in 0.5 degree steps from 10 to 60 degrees, the receiver always at 2 theta.",
         "Find the maxima.",
         "d = n lambda / (2 sin theta) for n = 1 and 2; average."],
        [_q("The receiver is kept at 2 theta because", ["Reflection angle equals incidence angle", "It is easier to "
            "read", "The horn is directional"], 0, "Bragg reflection is specular from the planes."),
         _q("The second-order peak lies", ["At sin theta twice that of the first", "At twice the angle exactly",
            "At the same angle"], 0, "sin theta2 = 2 sin theta1.")],
        [IITK, {"title": "Microwave optics kit: 10.5 GHz Gunn oscillator (lambda = c / f = 2.855 cm); the plane spacing "
                          "of the ball lattice is a property of this model", "note": "illustrative"}, SIM],
        {"reading": "res", "textbook": "pm9_d"}, "Never look into the horn at close range; keep the supply below its rated voltage.",
        "Microwave goniometer with a ball lattice", "A Gunn transmitter and a receiving horn on the arms of a goniometer, a cubic ball lattice on the turntable.",
        [{"say": "The transmitter on the fixed arm, the ball lattice on the turntable and the receiver on the swinging arm."}])


def horn_pattern() -> dict:
    return _mk(
        "pm9-horn-pattern", "pm9_horn", G_WAV, CH_MW, "Radiation pattern of a horn antenna in the E-plane",
        "Turn a pyramidal horn on a turntable in front of a fixed receiving horn, record the received power against "
        "angle in the E-plane, and find the half-power beam width and the gain.",
        {"x": 0.0, "s": 0.0},
        [knob("x", "Horn angle", "x", -60, 60, 1, 0, "deg"),
         knob("b", "This horn (its aperture height is hidden)", "b", 1.0, 20.0, 0.01, 5.2, "cm", 0.01, hidden=True)],
        [inst("y", "readout", "Detector reading", "y", unit="%", lc=0.1, digits=1)],
        "A horn's far-field pattern is the Fourier transform of the field across its mouth. In the E-plane (the plane "
        "of the electric field) the aperture field of the dominant mode is uniform over the height b, giving a pattern "
        "F = sin(v) / v with v = pi b sin(theta) / lambda; in the H-plane it is cosine-tapered across the width a, "
        "giving F = cos(u) / (1 - (2u / pi)^2). The half-power beam width is where F^2 falls to 1/2: about 51 lambda / b "
        "degrees in the E-plane and 68 lambda / a in the H-plane. The gain is G = (8 / pi^2) 4 pi a b / lambda^2.",
        ["Set the transmitting horn on the turntable and the receiving horn 1 m away, square-law detector on.",
         "Point them at each other and set the reading to 100 %.",
         "Turn the transmitting horn from -40 to +40 degrees in 1 degree steps, reading the detector.",
         "Plot the pattern and find the two half-power (50 %) angles.",
         "The beam width is the angle between them; compare with the aperture theory."],
        [_q("The half-power points of a square-law detector read", ["50 % of the peak", "70.7 %", "25 %"], 0,
            "The detector reads power."),
         _q("A wider aperture gives", ["A narrower beam", "A wider beam", "The same beam"], 0, "HPBW ~ lambda / size.")],
        [{"title": "C. A. Balanis, Antenna Theory (Wiley): aperture antennas, the pyramidal horn",
          "note": "cited from memory - verify"},
         {"title": "Horn aperture 7.0 x 5.2 cm, 10.5 GHz (2.855 cm)", "note": "illustrative"}, SIM],
        {"reading": "res", "textbook": "pm9_hpbw"}, "Never look into the horn at close range.",
        "Horn antenna on a turntable", "A pyramidal horn on a graduated turntable facing a receiving horn and a detector.",
        [{"say": "The horn on its graduated turntable, the receiving horn opposite, and the detector meter."}])


def normal_modes() -> dict:
    return _mk(
        "pm9-normal-modes", "pm9_coupled", G_WAV, CH_WAV, "Normal modes of two coupled pendulums",
        "Time the in-phase and out-of-phase normal modes of two equal pendulums joined by a light spring, time the beat "
        "period when one is started alone, and find the coupling constant.",
        {"x": 0.0, "s": 0.0},
        [knob("x", "Way of starting (0 in phase, 1 opposite, 2 one only)", "x", 0, 2, 1, 0),
         knob("k", "The coupling spring (its stiffness is hidden)", "k", 0.05, 20.0, 0.001, 1.0, "N/m", hidden=True)],
        [inst("y", "readout", "Time", "y", digits=3)],
        "Two equal oscillators joined by a weak coupling have two NORMAL MODES in which both move at one frequency: in "
        "phase (the coupling is never stretched, w1 = sqrt(g / L) for pendulums) and in opposite phase (the coupling "
        "adds its restoring force twice, w2 = sqrt(g / L + 2k / m)). Any other motion is a mixture of the two, so if "
        "one pendulum alone is started the energy passes back and forth between them with the BEAT period "
        "2 pi / (w2 - w1). The coupling constant is kappa = (w2^2 - w1^2) / (w2^2 + w1^2) = (T1^2 - T2^2) / "
        "(T1^2 + T2^2). Two LC circuits coupled by a mutual inductance M behave the same way, with "
        "w = 1 / sqrt((L +- M) C) and kappa = M / L.",
        ["Hang the two pendulums from the same rigid support and join the bobs with the light spring.",
         "Pull both bobs aside equally the same way and release: time 10 oscillations of the in-phase mode.",
         "Pull them aside equally in opposite directions: time 10 oscillations of the out-of-phase mode.",
         "Pull one bob aside, hold the other, release: time one beat (from one stillness of a bob to the next).",
         "kappa = (T1^2 - T2^2) / (T1^2 + T2^2); compare the beat period with 2 pi / (w2 - w1)."],
        [_q("In the in-phase mode the spring", ["Is never stretched", "Is stretched twice as much", "Breaks the "
            "symmetry"], 0, "Both bobs move together."),
         _q("A weaker coupling gives", ["A longer beat period", "A shorter beat period", "No beats"], 0,
            "The two frequencies come closer.")],
        [SGGU, {"title": "Coupled oscillators and normal modes (H. J. Pain, The Physics of Vibrations and Waves)",
                "note": "cited from memory - verify"}, ILLUS, SIM],
        {"reading": "res", "textbook": "pm9_kappa"}, "Keep the amplitude small (under 5 degrees) and your head clear of the swinging bobs.",
        "Coupled pendulums", "Two equal pendulums on a rigid support, their bobs joined by a light spring, and a stopwatch.",
        [{"say": "The two equal pendulums on the rigid support, joined by a light spring, and the stopwatch."}])


def gas_photocell() -> dict:
    return _mk(
        "pm9-gas-photocell", "pm9_gasphoto", G_MOD, CH_MOD, "Characteristics of a gas-filled photocell",
        "Plot the current of a gas-filled photocell against the anode voltage (collection, then gas amplification), "
        "and against the distance of the lamp: check that the photocurrent follows the light flux.",
        {"x": 0.0, "s": 0.0},
        [knob("x", "Anode voltage or lamp distance", "x", 0, 100, 0.5, 0),
         knob("Vg", "This cell (its gas-gain onset is hidden)", "Vg", 10, 80, 0.1, 35, "V", hidden=True)],
        [inst("y", "readout", "Photocurrent", "y", unit="µA", lc=0.001, digits=3)],
        "Light ejects photoelectrons from the cathode. As the anode voltage rises the current first grows and levels "
        "off when every photoelectron is collected (the saturation current, proportional to the light). In a GAS-"
        "filled cell the electrons then gain enough energy between collisions to ionise the argon, and each makes "
        "more electrons: above a few tens of volts the current rises again (gas amplification). At a fixed voltage "
        "the current stays proportional to the light flux, which falls as 1 / d^2 for a small lamp at distance d: a "
        "log-log plot of the current (dark current taken off) against d is a line of slope -2.",
        ["Set the lamp 20 cm from the cell and connect the cell through the microammeter to the supply.",
         "Raise the anode voltage from 0 to 90 V in 5 V steps and read the current.",
         "Set 60 V. Switch the lamp off and read the dark current.",
         "Switch on and move the lamp from 15 to 50 cm, reading the current.",
         "Plot ln(I - Idark) against ln d: the slope is -2 if the current follows the flux."],
        [_q("The current rises again above about 40 V because", ["The electrons ionise the gas", "More light is "
            "falling", "The cathode heats"], 0, "Gas amplification."),
         _q("A photocurrent proportional to the light gives, against distance,", ["A slope of -2 on a log-log plot",
            "A straight line through the origin", "A constant"], 0, "Flux ~ 1/d^2.")],
        [SGGU, {"title": "Gas-filled photocell characteristics (B. L. Worsnop and H. T. Flint, Advanced Practical Physics)",
                "note": "cited from memory - verify; the cell's saturation current, onset voltage and gain are illustrative"},
         SIM],
        {"reading": "res", "textbook": "pm9_isq"}, HOT_SAFE + " Do not exceed the cell's rated voltage: a glow discharge damages the cathode.",
        "Gas-filled photocell on a rail", "A lamp on an optical rail and a gas-filled photocell in its holder, with a supply and a microammeter.",
        [{"say": "The lamp on its rail, the gas-filled photocell and the supply with its microammeter."}])


BUILDERS = (gm_deadtime, gm_efficiency, beta_feather, k40_ux2, spark_alpha, prop_counter, kurie, angular_correlation,
            hall_temperature, two_probe, diode_ideality, photoconductivity, ac_susceptibility, stefan, cu_xrays,
            lc_lattice, pulse_echo, sound_cro, lecher_wire, fourier_analysis, transducers, microwave_bragg, horn_pattern,
            normal_modes, gas_photocell)
