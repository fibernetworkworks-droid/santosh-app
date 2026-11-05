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
        camera={"pos": [-0.02, 0.95, 1.52], "look": [-0.03, 0.27, -0.2]}, floor=-0.03, bodies=_nuc_bodies(hpge),
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


# ============================================================================================ microwaves
LIAO = {"title": "S. Y. Liao, Microwave Devices and Circuits, 3rd ed. (Prentice-Hall): slotted line, VSWR, double-minimum "
                 "method, impedance by the shift method, reflex klystron, Gunn diode"}
WR90 = {"title": "WR-90 rectangular waveguide, EIA / IEC 60153: inside 22.86 mm x 10.16 mm, TE10 cut-off 6.557 GHz, "
                 "operating band 8.2 - 12.4 GHz"}
VONHIPPEL = {"title": "A. R. von Hippel (ed.), Dielectric Materials and Applications, MIT Press (1954): permittivity "
                      "of Lucite, Teflon and fused quartz at 10 GHz"}
GROUP_M = "Physics · Microwaves"


def _mw_bodies() -> list[dict]:
    return [
        board(1.0, 0.6),
        B("src", "box", name="Source", info="Gunn oscillator on its mount.", size=[0.06, 0.03, 0.04], pos=[-0.4, 0.1, -0.2],
          color="#b5a054"),
        B("line", "box", name="Slotted line", info="A waveguide section with a slot along its broad wall.",
          size=[0.3, 0.0112, 0.0239], pos=[0.0, 0.085, -0.2], color="#b5a054"),
        B("ind", "box", name="Detector indicator", info="Analogue dial.", size=[0.2, 0.15, 0.14], pos=[0.35, 0.08, -0.1],
          color="#cdc9bf"),
    ]


def _mw(id, title, aim, task, params, theory, steps, questions, check, sources, kernel="msc_mwline", knobs=None,
        instruments=None, safety=None, tour=None):
    base = {"f": 9.5e9, "a": 0.02286, "g": 0.5, "phi": 1.0, "gs": 0.995, "xl": 0.1105, "x": 0.05, "p0": 100.0, "sam": 0.0,
            "ls": 0.004, "er": 2.6, "task": float(task)} if kernel == "msc_mwline" else {"task": float(task)}
    base.update(params)
    return lab(
        id=id, rig="msc-microwave-bench", title=title, group=GROUP_M, level="M.Sc. Physics", topic="Microwaves",
        chapter="Microwaves", aim=aim, kernel=kernel, params=base, autorun=True,
        camera={"pos": [-0.2, 0.62, 1.3], "look": [-0.2, 0.06, -0.2]}, floor=-0.03, bodies=_mw_bodies(),
        knobs=knobs or [knob("x", "Probe position on the slotted line", "x", 0.0, 100.0, 0.05, 50.0, "mm", 0.001),
                        knob("xl", "Load plane on the scale (hidden: where this load ends)", "xl", 100.0, 125.0, 0.01, 110.5,
                             "mm", 0.001, hidden=True)],
        instruments=instruments or [inst("I", "readout", "Detector current", "I", unit="µA", digits=2),
                                    inst("lg", "readout", "Guide wavelength (calculated)", "lam_g", unit="mm", digits=2),
                                    inst("s", "readout", "VSWR of this load", "vswr", digits=2)],
        steps=steps, theory=theory,
        safety=safety or ("The microwave power is a few milliwatts, but never look into an open waveguide or horn and "
                          "never aim a horn at a person. Keep the supply within its ranges and switch it off before "
                          "changing the load."),
        tour=tour or [{"say": "An X-band bench: source, isolator, attenuator, wavemeter, slotted line with its probe, and the load."}],
        questions=questions, sources=sources, check=check)


def mw_vswr() -> dict:
    return _mw(
        "msc-microwave-vswr", "Slotted line: guide wavelength in WR-90 from the standing-wave minima",
        "Find the guide wavelength of an X-band waveguide from the spacing of the minima of the standing wave against a "
        "short circuit, and compare it with the value calculated from the frequency and the guide dimensions.",
        0, {"g": 0.5, "phi": 1.0},
        "A wave in a rectangular guide moves with the guide wavelength λg = λ₀/√(1 − (λ₀/2a)²), longer than the "
        "free-space wavelength λ₀ because of the cut-off at λ = 2a. Against a short circuit the wave is totally "
        "reflected and the incident and reflected waves make a standing wave whose minima are half a guide wavelength "
        "apart. A probe in a slot along the broad wall, with a square-law crystal detector, finds those minima. The "
        "positions of two successive minima give λg = 2(x₂ − x₁).",
        ["Switch the source on and set the attenuator so that the detector reads about half scale at a maximum.",
         "Check that the short circuit is on the end of the line.",
         "Slide the probe along the slot and find a minimum of the detector current; read its position.",
         "Find the next minimum along the slot and read that position too.",
         "Repeat with a third minimum if the slot is long enough, and take the average spacing.",
         "Work out λg = 2 × (average spacing) and compare with the calculated λg."],
        [{"q": "Two successive minima of the standing wave are", "options": ["Half a guide wavelength apart", "One guide wavelength apart",
                                                                              "One free-space wavelength apart"], "answer": 0,
          "why": "The standing wave repeats every λg/2."},
         {"q": "Which wavelength is longer in the same guide?", "options": ["The guide wavelength", "The free-space wavelength",
                                                                           "They are equal"], "answer": 0,
          "why": "λg = λ₀/√(1 − (λ₀/2a)²) is always larger than λ₀."}],
        {"reading": "res", "textbook": "msc_mw_res", "tol": 0.01}, [DU, LIAO, WR90, SIM])


def mw_dielectric() -> dict:
    return _mw(
        "msc-microwave-dielectric", "Dielectric constant of Perspex by the waveguide slab-shift method",
        "Put a slab of a dielectric against the short circuit of a slotted line, measure how far the minima of the "
        "standing wave move, and find the dielectric constant of the slab at 9.5 GHz.",
        4, {"sam": 1.0, "er": 2.6, "ls": 0.004},
        "A slab of length l against the short changes the load the line sees, so every minimum of the standing wave "
        "moves by Δ. In the slab-filled guide the phase constant is βd = √(εr k₀² − (π/a)²), and the match of the "
        "impedances at the front face gives tan β(l − Δ) = (β/βd) tan(βd l), with β the phase constant of the empty "
        "guide. Measuring Δ gives εr by solving this equation (it has a single root when βd l < π/2).",
        ["Switch the source on. With the short circuit alone, find a minimum near the middle of the slot and read it.",
         "Put the slab into the guide, against the short circuit.",
         "Find the minimum nearest to the one you recorded and read its position; the shift is the difference.",
         "Solve tan β(l − Δ) = (β/βd) tan(βd l) for εr."],
        [{"q": "Putting the dielectric slab in the guide moves the minima because", "options": [
            "The wave is slower and its phase constant larger in the slab", "The slab absorbs the wave", "The source frequency changes"],
          "answer": 0, "why": "βd is larger than β, so the electrical length of the slab is greater."},
         {"q": "The slab must fit the cross-section of the guide exactly because", "options": [
             "An air gap changes the effective permittivity and spoils the equation", "The slab would fall out",
             "It would heat up"], "answer": 0, "why": "The equation is for a guide completely filled over the length l."}],
        {"reading": "res", "textbook": "msc_mw_res", "tol": 0.01}, [DU, LIAO, WR90, VONHIPPEL, SIM],
        tour=[{"say": "A slotted line ending in a short circuit, with a dielectric slab that fits the guide against the short."}])


def klystron() -> dict:
    return _mw(
        "msc-reflex-klystron", "Reflex klystron: reflector-voltage modes and electronic tuning",
        "Sweep the reflector voltage of a reflex klystron, find its modes, and measure the electronic tuning range of "
        "a mode with a wavemeter.",
        0, {"V0": 300.0, "L": 0.00126, "f0": 9.0e9, "Q": 400.0, "vr": 150.0, "P0": 30.0, "mode": 2.0},
        "In a reflex klystron the electron beam is turned back by a reflector at −Vr and returns to the cavity after a "
        "transit time T. The tube oscillates when the electrons return at the right phase, N = f T = n + 3/4 cycles, "
        "so the reflector voltage must be near Vr + V₀ = 2Lf√(2mV₀/e)/(n + 3/4): each n is a mode, a window of reflector "
        "voltage in which the power rises and falls. Inside a mode the frequency is pulled either side of the cavity "
        "frequency; the change between the half-power points is the electronic tuning range.",
        ["Switch the supply on and wait for the heater to warm up; the beam is on at 300 V.",
         "Sweep the reflector voltage from 20 to 500 V and watch the power: it shows separate modes.",
         "Tune to the centre of a mode (the power maximum) and write down the reflector voltage.",
         "Find the two reflector voltages at which the power has fallen to half and read the frequency with the "
         "wavemeter at each: the difference is the electronic tuning range.",
         "Repeat for the other modes and compare the voltages with Vr + V₀ ∝ 1/(n + 3/4)."],
        [{"q": "The mode with the highest reflector voltage has", "options": ["The smallest n and the shortest transit time", "The largest n",
                                                                               "No oscillation"], "answer": 0,
          "why": "A larger Vr + V₀ gives a shorter transit and fewer cycles N."},
         {"q": "Why does the output power of the modes fall as n increases?", "options": [
             "The bunching is weaker for a longer transit time", "The supply weakens", "The cavity heats"], "answer": 0,
          "why": "The electronic efficiency goes roughly as 1/N."}],
        {"reading": "vr_c", "textbook": "msc_ky_vr", "tol": 0.01}, [DU, LIAO, SIM], kernel="msc_klys",
        knobs=[knob("vr", "Reflector voltage", "vr", 20, 500, 1, 150, "V"),
               knob("L", "This tube (reflector spacing is hidden)", "L", 0.5, 3.0, 0.01, 1.26, "mm", 0.001, hidden=True)],
        instruments=[inst("P", "readout", "Output power", "P", unit="mW", digits=2), inst("f", "readout", "Frequency", "f_GHz", unit="GHz", digits=4),
                     inst("N", "readout", "Transit cycles N", "N", digits=3)],
        tour=[{"say": "A reflex klystron on its mount with its power supply, a wavemeter and a detector."}])


def gunn() -> dict:
    return _mw(
        "msc-gunn-oscillator", "Gunn oscillator: I-V characteristic, threshold and power",
        "Measure the current of a Gunn diode against its bias, find the threshold voltage where the current peaks, "
        "and note the power and frequency of the oscillation above it.",
        0, {"V": 8.0, "Lg": 10.5e-6, "vd": 1.0e5, "Eth": 3.2e5, "R0": 20.0, "r": 0.7, "Vk": 1.0, "R1": 250.0, "Pm": 15.0, "k": 2.7},
        "In n-type GaAs the conduction electrons are scattered into a heavier, slower valley when the field passes the "
        "threshold of about 3.2 kV/cm. The current then falls as the voltage rises (negative differential resistance), "
        "a domain of high field forms and crosses the active length L at the drift velocity vd, and the diode oscillates "
        "at f ≈ vd/L. The current is a maximum at the threshold voltage Vth = Eth L; above it the microwave power rises, "
        "passes a maximum and falls.",
        ["Switch the supply on; the bias starts at zero.",
         "Raise the bias in steps of 0.5 V and write down the current and the power at each.",
         "Near the maximum of the current take readings every 0.1 V.",
         "Plot the current against the bias. The peak of the curve is the threshold voltage.",
         "Note the bias at which the power is greatest and the frequency of the oscillation."],
        [{"q": "Above the threshold the current of the Gunn diode", "options": ["Falls as the bias rises", "Keeps rising", "Stays exactly constant"],
          "answer": 0, "why": "Electrons in the slow valley carry less current: negative differential resistance."},
         {"q": "A transit-time Gunn oscillator of active length 10 µm and drift velocity 10⁵ m/s oscillates at about", "options": [
             "10 GHz", "1 GHz", "100 GHz"], "answer": 0, "why": "f = vd / L = 10⁵ / 10⁻⁵ = 10¹⁰ Hz."}],
        {"reading": "vth_m", "textbook": "msc_gu_vth", "tol": 0.01}, [DU, LIAO, {"title": "S. M. Sze, Physics of Semiconductor Devices, 3rd ed.: GaAs threshold field 3.2 kV/cm, peak drift velocity ~10^7 cm/s"}, LAB_MODEL],
        kernel="msc_gunn",
        knobs=[knob("V", "Bias voltage", "V", 0, 12, 0.1, 8.0, "V"),
               knob("Lg", "This diode (active length is hidden)", "Lg", 3.0, 30.0, 0.1, 10.5, "µm", 0.000001, hidden=True)],
        instruments=[inst("I", "readout", "Current", "I_mA", unit="mA", digits=1), inst("P", "readout", "Output power", "P", unit="mW", digits=2),
                     inst("f", "readout", "Frequency", "f_GHz", unit="GHz", digits=2)],
        tour=[{"say": "A Gunn oscillator in its waveguide mount with the bias supply, a power meter and a wavemeter."}])


BUILDERS = BUILDERS + (mw_vswr, mw_dielectric, klystron, gunn)


# ============================================================================================ GM counting benches at M.Sc. depth
# The GM bench rigs (gm-statistics-bench, gm-halflife-bench) read everything from the lab's own params, so a lab
# at M.Sc. depth is the B.Sc. bench with its own conditions and samples: the lab is copied from its builder and given
# its own id, aim, conditions and sources.
import copy as _copy


def _gm_base(builder, **over):
    from . import modern_ug as _mu
    d = _copy.deepcopy(getattr(_mu, builder)())
    params = over.pop("params", {})
    d["params"] = {**d["params"], **params}
    for kn in d.get("knobs") or []:
        if kn.get("param") in params:
            kn["value"] = round(params[kn["param"]] / float(kn.get("k", 1.0)), 9)
            kn["min"] = min(kn["min"], kn["value"])
            kn["max"] = max(kn["max"], kn["value"])
    d.update(over)
    d["level"] = "M.Sc. Physics"
    d["topic"] = "Nuclear physics"
    d["chapter"] = "Nuclear physics"
    return d


def gm_poisson() -> dict:
    return _gm_base(
        "gm_statistics", id="msc-gm-poisson",
        title="Counting statistics with a GM counter: Poisson and Gaussian scatter",
        aim="Take fifty repeated counts of the same Cs-137 source and show that their scatter is Poisson: the standard "
            "deviation equals the square root of the mean, at a low and at a high count rate.",
        sources=[DU, RAD_SAFE, KNOLL, SIM, {"title": "G. F. Knoll, Radiation Detection and Measurement, ch. 3: Poisson "
                                                    "statistics, sigma = sqrt(N), and the Gaussian limit for a mean above about 20"}],
        params={"N0": 9.5, "t": 10.0, "seed": 61.0})


def short_lived() -> dict:
    return _gm_base(
        "half_life", id="msc-short-lived-lifetime",
        title="Half-life of a short-lived source: Ba-137m from a Cs-137 generator",
        aim="Elute barium-137m from a caesium-137 isotope generator, count it at short intervals, and find its "
            "half-life from the slope of the logarithm of the net count rate against time.",
        sources=[DU, RAD_SAFE, NNDC, SIM],
        params={"T": 153.12, "tc": 30.0, "N0": 150.0, "seed": 63.0})


def neutron_activation() -> dict:
    return _gm_base(
        "half_life", id="msc-neutron-activation",
        title="Thermal-neutron activation of an indium foil: half-life of the product",
        aim="Count a foil that has been activated in a thermal-neutron field as it decays, and find the half-life of the "
            "radioactive product from the slope of ln(net rate) against time.",
        sources=[DU, RAD_SAFE, NNDC, SIM],
        params={"T": 3257.4, "tc": 120.0, "N0": 130.0, "seed": 65.0})


BUILDERS = BUILDERS + (gm_poisson, short_lived, neutron_activation)


# ============================================================================================ electronics
IEC = {"title": "IEC 60063 preferred values (E12 series) for the resistors, capacitors and inductors"}
MILLMAN = {"title": "J. Millman and C. C. Halkias, Integrated Electronics, and R. A. Gayakwad, Op-Amp and Linear ICs: "
                    "oscillator and active-filter design, f = 1/(2 pi RC), Barkhausen criterion"}
GROUP_E = "Physics · Electronics"


def _eb() -> list[dict]:
    return [
        board(1.0, 0.6),
        B("bb", "box", name="Solderless breadboard", info="The circuit is built on it.", size=[0.42, 0.018, 0.26],
          pos=[-0.1, 0.009, -0.16], color="white"),
        B("gen", "box", name="Generator or supply", info="Function generator or dual supply.", size=[0.26, 0.1, 0.22],
          pos=[-0.62, 0.05, -0.26], color="#cdc9bf"),
        B("scope", "box", name="Oscilloscope", info="Two-channel oscilloscope.", size=[0.32, 0.22, 0.26], pos=[0.38, 0.11, -0.26],
          color="#cdc9bf"),
    ]


def _osc(id, title, aim, kind, params, theory, steps, questions, sources):
    base = {"kind": float(kind), "R": 10000.0, "C": 1.0e-8, "L": 1.0e-3, "C2": 1.0e-8, "L2": 1.0e-3, "M": 0.0, "A": 1.0,
            "Vsat": 12.0, "t": 0.0, "task": 0.0}
    base.update(params)
    return lab(
        id=id, rig="msc-signal-bench", title=title, group=GROUP_E, level="M.Sc. Physics", topic="Electronics",
        chapter="Electronics", aim=aim, kernel="msc_osc", params=base, autorun=True,
        camera={"pos": [-0.08, 0.62, 1.22], "look": [-0.08, 0.05, -0.2]}, floor=-0.03, bodies=_eb(),
        knobs=[knob("A", "Amplifier gain", "A", 1, 60, 0.05, 1.0)],
        instruments=[inst("f", "readout", "Frequency of oscillation", "f_kHz", unit="kHz", digits=3),
                     inst("am", "readout", "Minimum gain needed", "amin", digits=2),
                     inst("vo", "readout", "Output amplitude", "vo", unit="V", digits=2)],
        steps=steps, theory=theory,
        safety="Low voltages only. Check the polarity of the supply before switching on: a reversed op-amp or transistor "
               "supply destroys the device. Never exceed the rated supply.",
        tour=[{"say": "The oscillator is built on the breadboard; the supply is on the left and the oscilloscope on the right."}],
        questions=questions, sources=sources, check={"reading": "f", "textbook": "msc_osc_f", "tol": 0.01})


OSC_STEPS = ["Check the component values printed beside the parts and the polarity of the supply, then switch the supply on.",
             "Turn the gain up slowly from 1 until a steady sine wave appears on the scope: that is the minimum gain.",
             "Raise the gain a little more and measure the period on the scope from successive zero crossings.",
             "Repeat at a second gain. The frequency should not change with the gain.",
             "Compare the frequency with the formula and the minimum gain with the theory."]


def wien() -> dict:
    return _osc("msc-wien-bridge", "Wien-bridge oscillator: frequency and minimum gain",
                "Build a Wien-bridge oscillator with an op-amp, find the gain at which it starts, and measure its frequency.", 1,
                {"R": 15000.0, "C": 1.0e-8},
                "The Wien network has zero phase shift at one frequency, ω = 1/RC for equal resistors and capacitors, where it "
                "passes one third of the signal. A non-inverting amplifier of gain 3 or a little more closes the loop and the "
                "circuit oscillates at f = 1/(2πRC). At exactly 3 the amplitude is undefined; slightly above, it grows until the "
                "output saturates, and the waveform distorts, so a practical circuit limits the gain with a lamp or diode.",
                OSC_STEPS,
                [{"q": "In a Wien-bridge oscillator the amplifier must have a gain of at least", "options": ["3", "29", "1"], "answer": 0,
                  "why": "The network passes one third of the signal at its zero-phase frequency."},
                 {"q": "If R is doubled the frequency", "options": ["Halves", "Doubles", "Is unchanged"], "answer": 0, "why": "f = 1/(2πRC)."}],
                [DU, MILLMAN, IEC, SIM])


def rc_phase() -> dict:
    return _osc("msc-rc-phase-shift", "RC phase-shift oscillator: frequency and the gain of 29",
                "Build an op-amp RC phase-shift oscillator, find the gain at which it starts, and measure its frequency.", 0,
                {"R": 10000.0, "C": 1.0e-8},
                "Three identical RC sections in the feedback path of an inverting amplifier give a phase shift of 180° at one "
                "frequency, f = 1/(2π√6 RC), where the network attenuates the signal by a factor of 29. The inverting amplifier "
                "supplies the other 180° and must have a gain of at least 29 to make up that loss. Below a gain of 29 nothing "
                "oscillates.",
                OSC_STEPS,
                [{"q": "At the oscillation frequency the three-section RC network attenuates the signal by", "options": ["29", "3", "10"], "answer": 0,
                  "why": "β = 1/29 at the frequency where the phase is 180°."},
                 {"q": "Why must the amplifier invert?", "options": ["The network supplies only 180° of the 360° needed", "To reduce noise", "To increase the gain"],
                  "answer": 0, "why": "The loop phase must total 360°."}],
                [DU, MILLMAN, IEC, SIM])


def colpitts() -> dict:
    return _osc("msc-colpitts", "Colpitts oscillator: frequency against the tank values",
                "Build a transistor Colpitts oscillator, find the minimum gain, and measure its frequency against the tank values.", 2,
                {"L": 0.01, "C": 1.0e-8, "C2": 4.7e-8},
                "A Colpitts oscillator uses an inductor L with two capacitors C₁ and C₂ in series as its tank, and the junction of "
                "the capacitors feeds a fraction of the output back. The loop phase is right at the resonance of L with the series "
                "capacitance, f = 1/(2π√(L C₁C₂/(C₁ + C₂))), and the amplifier gain must be at least C₂/C₁.",
                OSC_STEPS,
                [{"q": "The capacitance that resonates with L in a Colpitts tank is", "options": ["C₁C₂/(C₁ + C₂)", "C₁ + C₂", "C₁ − C₂"], "answer": 0,
                  "why": "The two capacitors are in series around the loop."},
                 {"q": "Doubling both C₁ and C₂ changes the frequency by", "options": ["1/√2", "2", "1/2"], "answer": 0, "why": "f ∝ 1/√C."}],
                [DU, MILLMAN, IEC, SIM])


def hartley() -> dict:
    return _osc("msc-hartley", "Hartley oscillator: frequency against the tank values",
                "Build a transistor Hartley oscillator, find the minimum gain, and measure its frequency against the tank values.", 3,
                {"L": 0.001, "L2": 0.0047, "C": 1.0e-8},
                "A Hartley oscillator is the dual of the Colpitts: a capacitor C across two inductors L₁ and L₂ in series, with the "
                "feedback taken from their junction. It oscillates at f = 1/(2π√((L₁ + L₂ + 2M) C)) with M the mutual inductance "
                "(zero for separate coils), and the amplifier gain must be at least L₂/L₁.",
                OSC_STEPS,
                [{"q": "The inductance in a Hartley tank is", "options": ["L₁ + L₂ (+ 2M)", "L₁L₂/(L₁ + L₂)", "L₁ − L₂"], "answer": 0,
                  "why": "The two coils are in series around the capacitor."},
                 {"q": "Doubling C changes the frequency by", "options": ["1/√2", "2", "1/2"], "answer": 0, "why": "f ∝ 1/√C."}],
                [DU, MILLMAN, IEC, SIM])


def rf_osc() -> dict:
    return _osc("msc-rf-oscillator", "RF oscillator: a Colpitts tank at a few megahertz",
                "Build a Colpitts oscillator with a small inductor and picofarad capacitors, and measure its radio-frequency "
                "output frequency and amplitude.", 2,
                {"L": 1.0e-5, "C": 1.0e-10, "C2": 4.7e-10},
                "At radio frequencies the same Colpitts tank is used with microhenry inductors and picofarad capacitors. The "
                "frequency is f = 1/(2π√(L C₁C₂/(C₁ + C₂))); stray capacitance of the wiring adds to C₁ and C₂ and must be kept small. "
                "The output amplitude settles where the transistor saturates.",
                OSC_STEPS,
                [{"q": "Why are short leads used in an RF oscillator?", "options": ["Stray capacitance and inductance shift the frequency", "To save wire", "To reduce the gain"],
                  "answer": 0, "why": "At megahertz a few picofarads is a large part of the tank."},
                 {"q": "A 10 µH inductor with about 82 pF in the tank oscillates at about", "options": ["5.5 MHz", "55 kHz", "550 MHz"], "answer": 0,
                  "why": "f = 1/(2π√(10⁻⁵ × 8.2×10⁻¹¹)) ≈ 5.6 MHz."}],
                [DU, MILLMAN, IEC, SIM])


def _filt(id, title, aim, kind, params, theory, steps, questions, sources):
    base = {"kind": float(kind), "R": 10000.0, "C": 1.0e-8, "K": 1.5858, "R2": 1000.0, "C2": 1.0e-8, "f": 1000.0, "task": 0.0}
    base.update(params)
    return lab(
        id=id, rig="msc-signal-bench", title=title, group=GROUP_E, level="M.Sc. Physics", topic="Electronics",
        chapter="Electronics", aim=aim, kernel="msc_filt", params=base, autorun=True,
        camera={"pos": [-0.08, 0.62, 1.22], "look": [-0.08, 0.05, -0.2]}, floor=-0.03, bodies=_eb(),
        knobs=[knob("f", "Generator frequency", "f", 1, 1000000, 1, 1000, "Hz")],
        instruments=[inst("g", "readout", "Gain (output / input)", "gain", digits=3), inst("db", "readout", "Gain", "gain_db", unit="dB", digits=2),
                     inst("ph", "readout", "Phase of the output", "phase", unit="°", digits=1)],
        steps=steps, theory=theory,
        safety="Low voltages only. Keep the generator output within the rated input of the circuit and check the supply polarity.",
        tour=[{"say": "The filter is on the breadboard; the generator is on the left and the oscilloscope on the right."}],
        questions=questions, sources=sources, check={"reading": "fc", "textbook": "msc_filt_fc", "tol": 0.01})


FILT_STEPS = ["Switch the generator on and set its output to 1 V peak to peak.",
              "Set a frequency, measure the input and output on the scope, and write the readings down.",
              "Take at least eight frequencies on both sides of the expected corner, closer together near it.",
              "Plot gain in dB against log frequency (and phase against log frequency).",
              "Read the −3 dB frequency and the roll-off in dB per decade from the graph."]


def active_filters() -> dict:
    return _filt("msc-active-filters", "Active filters with Bode plots: second-order low-pass",
                 "Measure the gain and phase of a second-order active low-pass filter over several decades, draw its Bode plot, and find "
                 "its cut-off frequency and roll-off.", 0, {"R": 10000.0, "C": 1.0e-8, "K": 1.5858},
                 "An active filter puts the frequency-dependent network around an op-amp, so it can have gain, a high input "
                 "impedance and a low output impedance. A Sallen-Key stage with equal R and C and a gain of 3 − √2 is a "
                 "second-order Butterworth filter: flat in the pass band, −3 dB at f₀ = 1/(2πRC) and falling at 40 dB per decade "
                 "beyond. The phase goes from 0 to −180°.",
                 FILT_STEPS,
                 [{"q": "A second-order filter falls beyond its cut-off at", "options": ["40 dB per decade", "20 dB per decade", "60 dB per decade"], "answer": 0,
                   "why": "Each order adds 20 dB per decade."},
                  {"q": "At the cut-off frequency the gain is", "options": ["0.707 of the pass band value", "half", "zero"], "answer": 0, "why": "−3 dB."}],
                 [DU, MILLMAN, IEC, SIM])


def passive_filters() -> dict:
    return _filt("msc-passive-filters", "Passive RC filters with Bode plots: low-pass",
                 "Measure the gain and phase of a passive RC low-pass filter over several decades and find its cut-off frequency and roll-off.", 4,
                 {"R": 10000.0, "C": 1.0e-8},
                 "A resistor and a capacitor make the simplest filter. In the low-pass the output is taken across the capacitor: the gain is 1/√(1 + (f/f_c)²) "
                 "with f_c = 1/(2πRC), −3 dB at f_c and falling at 20 dB per decade above it; the phase goes from 0 to −90°. A passive filter has "
                 "no gain and is loaded by whatever follows it.",
                 FILT_STEPS,
                 [{"q": "The phase of an RC low-pass at its cut-off frequency is", "options": ["−45°", "−90°", "0°"], "answer": 0, "why": "tan φ = f/f_c = 1."},
                  {"q": "Doubling C changes the cut-off frequency by", "options": ["Halving it", "Doubling it", "Nothing"], "answer": 0, "why": "f_c = 1/(2πRC)."}],
                 [DU, MILLMAN, IEC, SIM])


BUILDERS = BUILDERS + (wien, rc_phase, colpitts, hartley, rf_osc, active_filters, passive_filters)
