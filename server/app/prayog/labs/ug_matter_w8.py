"""Lab pack `ug_matter_w8`: B.Sc. nuclear and radiation physics, solid state physics and nanomaterials, wave 8.

Four studio rigs (`app/static/prayog/exp/`) serve the set-ups of `syllabus/physics/ug.json`:
    um8-gm-bench          the GM counting bench: beta absorption in aluminium, K-40 in a potassium salt
    um8-ion-workstation   a stopping-power program (Bethe-Bloch): energy loss, proton range, projectile z, Bragg curve
    um8-xrd-bench         a powder diffractometer: unit cell + Scherrer size, nanoparticle crystallite size
    um8-junction-oven     a germanium junction in a heated bath: band gap from the reverse saturation current
Physics: the `ug_matter_w8` kernel pack (never catalog.py / kernels.py). Every lab carries its own check: the kernel's
reading against the textbook relation, within 1 %. Count data is SIMULATED DATA from the lab's own seed. The stopping
power labs use the Bethe-Bloch formula, not the SRIM / TRIM program: no nuclear stopping, no shell or density-effect
corrections, no Monte Carlo straggling - the labs say so. Constants written from memory are labelled "from memory -
verify". English only.
"""
from __future__ import annotations

from ..catalog import B, board, inst, knob, lab

SIM = {"title": "Hoola Prayogshala kernel",
       "note": "SIMULATED DATA: readings come from the simulation code; checked against the textbook relation in Hoola's tests"}
DU = {"title": "University of Delhi B.Sc. (Hons.) Physics practical lists (LOCF 2019 / UGCF 2022): Radiation Safety, "
               "Solid State Physics and Nano Materials labs"}
KATZ = {"title": "L. Katz and A. S. Penfold, Rev. Mod. Phys. 24, 28 (1952): range-energy relation for beta particles in "
                 "aluminium, R = 0.412 E^(1.265 - 0.0954 ln E) g/cm^2 (0.01 - 2.5 MeV)",
        "note": "the mass absorption coefficient mu_m = 17 E^-1.14 cm^2/g is the empirical rule quoted in B.Sc. texts - "
                "from memory - verify"}
NNDC_TL = {"title": "NNDC / ENSDF: Tl-204 beta end-point energy 763.7 keV, half-life 3.78 y",
           "note": "from memory - verify"}
NNDC_K = {"title": "NNDC / NUBASE: K-40 half-life 1.248e9 y, beta-minus branch 89.28 %; IUPAC isotopic abundance of "
                   "K-40 0.0117 %; IUPAC standard atomic weights (K 39.0983, Cl 35.453, S 32.06, O 15.999, C 12.011)",
          "note": "from memory - verify"}
PDG = {"title": "Particle Data Group, Review of Particle Physics, 'Passage of particles through matter': the Bethe "
                "equation, K = 0.307075 MeV cm^2/mol, Tmax; CODATA 2018 m_e c^2 = 0.51099895 MeV, u = 931.49410242 MeV"}
PDG_MAT = {"title": "PDG 'Atomic and nuclear properties of materials' / ICRU Reports 37 and 49: Z/A, mean excitation energy I and density",
           "note": "water 0.55509, 75.0 eV, 1.00; graphite 0.49955, 78.0 eV, 2.21; Mylar 0.52037, 78.7 eV, 1.40; silver 0.43577, "
                   "470 eV, 10.5; gold 0.40108, 790 eV, 19.32; lead 0.39575, 823 eV, 11.35 g/cm3 - from memory - verify"}
BARKAS = {"title": "W. H. Barkas, Nuclear Research Emulsions (1963): effective charge z_eff = z (1 - exp(-125 beta z^-2/3))"}
NOT_SRIM = {"title": "J. F. Ziegler, J. P. Biersack, M. D. Ziegler, SRIM - The Stopping and Range of Ions in Matter",
            "note": "the program the syllabus names; this lab computes the Bethe-Bloch curve itself and is NOT SRIM"}
CULLITY = {"title": "B. D. Cullity and S. R. Stock, Elements of X-Ray Diffraction",
           "note": "Bragg's law, the extinction rules of cubic, hexagonal and tetragonal lattices, and the Scherrer "
                   "equation L = K lambda / (beta cos theta) with K = 0.9"}
LATT = {"title": "Lattice parameters, ICDD powder diffraction file / Wyckoff, Crystal Structures; Cu K-alpha1 1.5406 A",
        "note": "Cu 3.6149 A, Si 5.4309 A, W 3.1652 A; zinc blende CdS 5.818 A; wurtzite ZnO a 3.2498, c 5.2066 A; anatase "
                "TiO2 a 3.7852, c 9.5139 A; hematite Fe2O3 a 5.0356, c 13.749 A (hexagonal axes) - from memory - verify"}
SZE = {"title": "S. M. Sze, Physics of Semiconductor Devices / CRC Handbook: germanium band gap 0.66 eV at 300 K; the "
                "diode saturation current I_s proportional to T^3 exp(-Eg / kT)"}
RAD_SAFE = {"title": "AERB / IAEA teaching-laboratory practice: sealed sources only, tongs, shielding, distance, locked store"}

GM_SAFE = ("Sealed source only. Move it with the tongs, from behind the lead shield, never with your fingers; keep it at "
           "arm's length, return it to its locked store as soon as the readings are done, and wash your hands afterwards.")
COMP_SAFE = ("A computational practical still has a discipline: write down the settings of every run before changing "
             "anything, and never report a number whose convergence you have not seen.")


def _gm_bodies() -> list[dict]:
    return [board(1.0, 0.6),
            B("castle", "box", name="Lead castle", info="Lead bricks round the GM tube and the shelf stand.",
              size=[0.26, 0.18, 0.22], pos=[-0.26, 0.09, -0.14], color="#53565c"),
            B("tube", "cylinder", name="End-window GM tube", r=0.0135, h=0.05, pos=[-0.26, 0.16, -0.09], color="steel"),
            B("unit", "box", name="Scaler-timer", size=[0.36, 0.13, 0.24], pos=[0.3, 0.065, -0.1], color="#d7d3c9")]


# =============================================================================================== beta absorption
def beta_absorption() -> dict:
    return lab(
        id="um8-beta-absorption", rig="um8-gm-bench",
        title="Absorption of beta particles in aluminium", group="Physics · Nuclear Physics", level="B.Sc.",
        topic="Radiation Safety and Nuclear Physics", chapter="Nuclear and radiation physics",
        aim="Count a sealed Tl-204 beta source through aluminium foils of known areal density, find the mass "
            "absorption coefficient from the slope of ln(net rate), and the range where the beta counts end. "
            "SIMULATED DATA.",
        kernel="um8_beta", params={"x": 0.0, "E": 0.7637, "N0": 400.0, "brem": 0.4, "bg": 0.5, "t": 100.0, "seed": 17.0},
        autorun=True, camera={"pos": [0.05, 0.8, 0.9], "look": [0.05, 0.1, -0.1]}, floor=-0.03,
        bodies=_gm_bodies(),
        knobs=[knob("x", "Aluminium in the beam", "x", 0, 500, 1, 0, "mg/cm²", 0.001),
               knob("t", "Counting time", "t", 30, 600, 10, 100, "s"),
               knob("E", "This source (its end-point energy is hidden)", "E", 0.1, 2.5, 0.0001, 0.7637, "MeV",
                    hidden=True)],
        instruments=[inst("r", "readout", "Count rate", "rate", unit="counts/s", lc=0.01, digits=2),
                     inst("gr", "graph", "Count rate against areal density", "rate", x="p.x", xk=1000.0,
                          xlabel="x (mg/cm²)", dots=True)],
        steps=["Count the background with the source in its store.",
               "Put the source on its shelf with the tongs and count with no absorber.",
               "Add aluminium foils of known areal density (mg/cm²) and count at each.",
               "Far behind the range only the bremsstrahlung tail is left: count it, and take tail and background off.",
               "Plot ln(net rate) against areal density: the slope is −μ_m. The range is where the beta counts end."],
        theory="Beta particles are emitted with every energy up to an end point E. In a light absorber they are "
               "scattered and slowed, and for most of their path the count rate falls almost exponentially with the "
               "areal density x (mass per unit area): N = N₀ exp(−μ_m x). Unlike gamma rays, betas have a RANGE: "
               "beyond a definite thickness none get through, and only the weak bremsstrahlung X-rays they make in "
               "the source and the foils are left, with the background. The range of the most energetic betas fixes "
               "the end-point energy through the Katz-Penfold relation R = 0.412 E^(1.265 − 0.0954 ln E) g/cm². "
               "In this model the beta curve is cut off sharply at R; a real curve rounds off into the tail just "
               "before it.",
        safety=GM_SAFE,
        tour=[{"say": "The sealed beta source on its shelf under the end-window GM tube, and a box of aluminium foils."},
              {"set": {"x": 0}, "say": "With no absorber, the full beta count."},
              {"set": {"x": 150}, "say": "A hundred and fifty milligrams per square centimetre: the count has fallen to a few per cent."},
              {"set": {"x": 400}, "say": "Behind the range only the bremsstrahlung tail and the background are left."}],
        questions=[{"q": "Beta particles, unlike gamma rays, have", "options": [
            "A definite range in an absorber", "No interaction with matter", "A half-value thickness only"],
            "answer": 0, "why": "Each beta loses energy continuously and stops; a photon is removed all at once or not at all."},
            {"q": "The counts behind the range come from", "options": [
                "Bremsstrahlung X-rays and the background", "Betas that tunnel through", "The tube's dead time"],
             "answer": 0, "why": "Betas slowing in matter radiate X-rays, which are only weakly absorbed by aluminium."}],
        sources=[DU, KATZ, NNDC_TL, RAD_SAFE, SIM],
        check={"reading": "R", "textbook": "um8_beta_range"},
    )


# =============================================================================================== K-40 in a salt
def k40_salt() -> dict:
    return lab(
        id="um8-k40-salt", rig="um8-gm-bench",
        title="Radioactivity of potassium chloride with a GM counter", group="Physics · Nuclear Physics",
        level="B.Sc.", topic="Radiation Safety and Nuclear Physics", chapter="Nuclear and radiation physics",
        aim="Count an empty tray and then a tray of potassium chloride under a GM tube, and find the count rate "
            "above background that comes from the natural K-40 in it. SIMULATED DATA.",
        kernel="um8_k40", params={"m": 0.1, "fK": 0.52445, "eff": 0.002, "bg": 0.45, "t": 600.0, "seed": 29.0, "on": 1.0},
        autorun=True, camera={"pos": [0.05, 0.8, 0.9], "look": [0.05, 0.1, -0.1]}, floor=-0.03,
        bodies=_gm_bodies(),
        knobs=[knob("m", "Salt in the tray", "m", 20, 200, 10, 100, "g", 0.001),
               knob("t", "Counting time", "t", 100, 3600, 50, 600, "s"),
               knob("on", "Tray filled (1) or empty (0)", "on", 0, 1, 1, 1)],
        instruments=[inst("r", "readout", "Count rate", "rate", unit="counts/s", lc=0.001, digits=3),
                     inst("n", "readout", "Net rate from the salt", "net", unit="counts/s", digits=3, hint=True)],
        steps=["Count the empty tray under the tube for ten minutes: this is the background.",
               "Fill the tray with a weighed amount of the salt, level it, and put it back in exactly the same place.",
               "Count for ten minutes, three times.",
               "Take the background off each count rate and average.",
               "Compare with the activity expected from the potassium in the salt and the K-40 data."],
        theory="Natural potassium contains 0.0117 % of the radioactive isotope K-40, half-life 1.248 × 10⁹ years. "
               "Every gram of potassium therefore holds about 1.8 × 10¹⁸ K-40 nuclei and gives about 31 decays a "
               "second, 89 % of them beta decays. A tray of a potassium salt is a weak but real source: the GM "
               "tube sees only a small fraction of those betas (the tray efficiency, set by the geometry and the "
               "self-absorption in the salt), so the signal is a few counts a second over a background of about "
               "half a count a second. Long counts are needed: the error of N counts is √N.",
        safety="Potassium chloride is the ordinary salt substitute; it is not hazardous, but keep it off your hands "
               "and away from the electronics, and sweep up any spilt salt.",
        tour=[{"say": "The GM tube in its lead castle over a shallow tray, and the scaler-timer."},
              {"set": {"on": 0}, "say": "The empty tray: only the background."},
              {"set": {"on": 1}, "say": "With a hundred grams of potassium chloride the rate goes up by a few counts a second."}],
        questions=[{"q": "The activity of potassium comes from", "options": [
            "The isotope K-40", "The chlorine", "Cosmic rays caught in the salt"], "answer": 0,
            "why": "K-40 is a primordial radioisotope present in all natural potassium."},
            {"q": "To halve the fractional error of a count you must count", "options": [
                "Four times as long", "Twice as long", "Half as long"], "answer": 0, "why": "The fractional error is 1/√N."}],
        sources=[DU, NNDC_K, SIM,
                 {"title": "Tray efficiency eps = 0.002",
                  "note": "a design value of this tube and tray (geometry and self-absorption), illustrative - not a measured constant"}],
        check={"reading": "net", "textbook": "um8_k40_net"},
    )


# =============================================================================================== stopping power (Bethe-Bloch)
def _ion(lab_id: str, title: str, aim: str, params: dict, check: dict, theory: str, steps: list[str],
         questions: list[dict]) -> dict:
    return lab(
        id=lab_id, rig="um8-ion-workstation", title=title, group="Physics · Nuclear Physics", level="B.Sc.",
        topic="Radiation Safety and Nuclear Physics", chapter="Nuclear and radiation physics",
        aim=aim, kernel="um8_ion", params=params, speed=1, speeds=[1],
        camera={"pos": [0.45, 0.42, 0.78], "look": [0.08, 0.17, -0.3]}, floor=-0.02,
        bodies=[B("mat", "box", name="Desk mat", size=[0.9, 0.004, 0.45], pos=[0.05, 0.002, -0.12], color="black", cut=False),
                B("bezel", "box", name="Monitor", info="The stopping-power program draws its curves here.",
                  size=[0.36, 0.235, 0.016], pos=[0.08, 0.225, -0.4], color="#17181b"),
                B("kbd", "box", name="Keyboard", size=[0.33, 0.014, 0.12], pos=[0.08, 0.007, -0.1], color="#1b1b1d"),
                B("tower", "box", name="Workstation", size=[0.17, 0.34, 0.36], pos=[-0.56, 0.17, -0.45], color="#2b2f36")],
        knobs=[knob("n", "Energy (or depth) steps", "n", 4, 1000, 1, params.get("n", 20), ""),
               knob("E", "Energy per nucleon", "E", 1, 1000, 0.1, params.get("E", 10), "MeV")],
        instruments=[inst("S", "readout", "Mass stopping power", "S", unit="MeV cm²/g", digits=4),
                     inst("R", "readout", "Range at these steps", "R", unit="g/cm²", digits=5),
                     inst("z", "readout", "Effective charge", "zeff", digits=3)],
        steps=steps, theory=theory, safety=COMP_SAFE, questions=questions,
        sources=[DU, PDG, PDG_MAT, BARKAS, NOT_SRIM, SIM], check=check)


BETHE = ("A fast charged particle loses energy mainly to the electrons of the medium. The Bethe-Bloch formula gives "
         "the mass stopping power −dE/dx = K z² (Z/A) (1/β²) [½ ln(2mₑc²β²γ²T_max / I²) − β²], with K = 0.307075 "
         "MeV cm²/mol, Z/A the electrons per gram, I the mean excitation energy of the medium and T_max the largest "
         "energy one collision can give an electron. It falls as 1/β² at low speed, has a broad minimum near βγ ≈ 3 "
         "and rises slowly beyond. This program evaluates the formula without the shell, Barkas-Andersen, Bloch and "
         "density-effect corrections and without nuclear stopping, so it is good from a few MeV per nucleon to a few "
         "GeV; SRIM, which the syllabus names, adds those corrections and fitted data and also runs a Monte Carlo "
         "(TRIM) of the ion's path.")


def ion_energy_loss() -> dict:
    return _ion("um8-ion-energy-loss", "Stopping power of protons in water against energy (Bethe-Bloch)",
                "Compute the mass stopping power of protons in water from 1 MeV to 50 GeV with the Bethe-Bloch "
                "formula, plot it against energy, and find the minimum-ionising value.",
                {"mode": 0.0, "z": 1.0, "Mu": 1.007276, "E": 10.0, "ZA": 0.55509, "I": 75.0, "rho": 1.0, "n": 20.0},
                {"reading": "S", "textbook": "um8_bethe_S"},
                BETHE + " The curve's minimum is the energy loss of a minimum-ionising particle, about 2 MeV cm²/g in "
                        "water; a cosmic-ray muon crossing a detector loses close to this value.",
                ["Read the card: the formula, the medium's Z/A and I.", "Choose the energies to compute (at least ten, "
                 "spread over the decades).", "Run the program and record S at each energy.",
                 "Plot S against E on log-log axes.", "Read the minimum of the curve and the energy where it lies."],
                [{"q": "At low speed the stopping power varies roughly as", "options": ["1/β²", "β²", "a constant"],
                  "answer": 0, "why": "The 1/β² in front dominates: slower particles spend longer near each electron."},
                 {"q": "The minimum of the curve lies near", "options": ["βγ ≈ 3", "β ≈ 0.01", "the rest energy of the electron"],
                  "answer": 0, "why": "That is the minimum-ionising region, about 2 GeV for a proton."}])


def ion_proton_range() -> dict:
    return _ion("um8-ion-proton-range", "CSDA range of 100 MeV protons in carbon (Bethe-Bloch)",
                "Integrate dE/S(E) from 1 MeV up to 100 MeV with the Bethe-Bloch stopping power of carbon, with "
                "fewer and more energy steps, and find the converged CSDA range of the protons.",
                {"mode": 1.0, "z": 1.0, "Mu": 1.007276, "E": 100.0, "ZA": 0.49955, "I": 78.0, "rho": 2.21, "n": 10.0},
                {"reading": "R", "textbook": "um8_csda"},
                BETHE + " The continuous-slowing-down (CSDA) range is the path length to stop, R = ∫ dE / S(E), "
                        "worked out here by the midpoint rule on equal steps of ln E. Below 1 MeV the formula is not "
                        "valid; the range left there is a few tens of micrometres of water and is left out.",
                ["Read the card: the formula and the medium.", "Run the range integration with 5 energy steps.",
                 "Run again with 10, 20, 50 and 200 steps and record each range.",
                 "See the range settle: the converged value is your result.",
                 "Divide by the density for the range in centimetres."],
                [{"q": "The range of a proton is found from", "options": ["R = ∫ dE / S(E)", "R = S × E", "R = E / I"],
                  "answer": 0, "why": "Each thin slice dx takes away dE = S dx."},
                 {"q": "In a denser material of the same Z/A the range in cm is", "options": ["Shorter", "Longer", "The same"],
                  "answer": 0, "why": "The range in g/cm² is nearly the same; dividing by a larger density gives fewer cm."}])


def ion_projectile_z() -> dict:
    return _ion("um8-ion-projectile-z", "Stopping power against projectile charge Z = 1 to 92 in Mylar",
                "Compute the Bethe-Bloch stopping power in Mylar of ions from hydrogen to uranium at 10 MeV per "
                "nucleon and find, from the ratio to the proton's, the effective charge of the uranium ion.",
                {"mode": 2.0, "z": 92.0, "Mu": 238.0289, "E": 10.0, "ZA": 0.52037, "I": 78.7, "rho": 1.40, "n": 20.0},
                {"reading": "zeff", "textbook": "um8_zeff"},
                BETHE + " At the SAME speed every ion sees the same electrons, so its stopping power is the proton's "
                        "times z². A heavy ion is not fully stripped: it carries some of its electrons with it, and "
                        "its effective charge, given by Barkas' rule z_eff = z (1 − exp(−125 β z^−2/3)), is less than z. "
                        "So √(S_ion / S_proton) measures the effective charge.",
                ["Read the card: the formula, the medium and the speed.",
                 "Compute S for the proton and for each listed ion at 10 MeV per nucleon.",
                 "Plot S against z on log-log axes; compare with the z² line.",
                 "Work out √(S / S_proton) for each ion.",
                 "The value for uranium is its effective charge at this speed."],
                [{"q": "At the same speed, an alpha particle loses energy", "options": ["Four times as fast as a proton",
                  "As fast as a proton", "Twice as fast"], "answer": 0, "why": "z² = 4."},
                 {"q": "A uranium ion at 10 MeV per nucleon has an effective charge", "options": ["Well below 92", "Exactly 92", "Above 92"],
                  "answer": 0, "why": "It is only partly stripped at that speed."}])


def ion_bragg() -> dict:
    return _ion("um8-ion-bragg", "Bragg curve of argon ions in gold (Bethe-Bloch)",
                "Step argon ions of 10 MeV per nucleon through gold in small depth steps, plot the energy loss "
                "against depth (the Bragg curve), and find the depth at which they stop.",
                {"mode": 3.0, "z": 18.0, "Mu": 39.9624, "E": 10.0, "ZA": 0.40108, "I": 790.0, "rho": 19.32, "n": 40.0,
                 "Ec": 0.5},
                {"params": {"n": 400.0}, "reading": "depth", "textbook": "um8_csda"},
                BETHE + " Stepping the ion slice by slice, the energy loss per slice GROWS as it slows - the 1/β² "
                        "rise - until it peaks just before the ion stops: that peak is the Bragg peak, which is why "
                        "ion beams treat deep tumours while sparing the skin. Near the very end the effective charge "
                        "falls and the uncorrected formula is poor; the march stops at 0.5 MeV per nucleon.",
                ["Read the card: the ion, the target and the energy.",
                 "Choose the number of depth steps and run the march.",
                 "Record the energy loss at each depth and the depth where the ion stops.",
                 "Run again with more steps until the stopping depth settles.",
                 "Plot the Bragg curve and read the depth of its peak."],
                [{"q": "The energy loss per unit depth is largest", "options": ["Just before the ion stops", "At the surface",
                  "Half-way in"], "answer": 0, "why": "Slower ions lose energy faster; this is the Bragg peak."},
                 {"q": "Using more depth steps", "options": ["Makes the stopping depth converge", "Changes the physics",
                  "Always lowers the range"], "answer": 0, "why": "It only reduces the numerical error of the march."}])


# =============================================================================================== X-ray diffraction
def _xrd(lab_id: str, title: str, aim: str, params: dict, check: dict, theory: str, steps: list[str],
         questions: list[dict], sample: str) -> dict:
    return lab(
        id=lab_id, rig="um8-xrd-bench", title=title, group="Physics · Solid State Physics", level="B.Sc.",
        topic="Solid State Physics", chapter="Solid state physics and materials",
        aim=aim, kernel="um8_xrd", params=params, autorun=True,
        camera={"pos": [0.0, 0.7, 0.9], "look": [0.0, 0.1, -0.1]}, floor=-0.03,
        bodies=[board(1.0, 0.6),
                B("gonio", "cylinder", name="Goniometer", info="The theta-2theta circle: tube arm and detector arm.",
                  r=0.12, h=0.04, pos=[-0.15, 0.1, -0.15], rot=[1.5708, 0, 0], color="#c9ccd2"),
                B("tube", "box", name="X-ray tube (Cu K-alpha)", size=[0.12, 0.05, 0.05], pos=[-0.3, 0.12, -0.15], color="#2b2f36"),
                B("det", "box", name="Detector", size=[0.08, 0.04, 0.04], pos=[0.0, 0.12, -0.15], color="#3a4f6e"),
                B("pc", "box", name="Control computer", info="Shows the diffractogram.", size=[0.3, 0.2, 0.02],
                  pos=[0.3, 0.12, -0.2], color="#17181b")],
        knobs=[knob("tth", "Detector angle 2θ", "tth", 15, 100, 0.01, 30, "°")],
        instruments=[inst("I", "readout", "Counts per second", "I", unit="counts/s", digits=0),
                     inst("gr", "graph", "Intensity against 2θ", "I", x="p.tth", xlabel="2θ (°)")],
        steps=steps, theory=theory,
        safety="X-rays: the diffractometer is interlocked. Never open the enclosure with the shutter open, and wear "
               "the film badge. Load the powder only with the tube shutter closed.",
        tour=[{"say": "The X-ray tube on one arm of the goniometer, the detector on the other, and " + sample + " in the holder at the centre."}],
        questions=questions, sources=[DU, CULLITY, LATT, SIM], check=check)


XRD_TH = ("X-rays of wavelength λ reflect strongly from the lattice planes of spacing d only when 2d sin θ = λ (Bragg). "
          "A powder holds crystallites in every orientation, so a θ-2θ scan shows one line for every allowed set of "
          "planes. Small crystallites broaden the lines: the Scherrer equation L = Kλ / (β cos θ) gives the size L from "
          "the line width β (in radians of 2θ) after the instrument's own width has been taken off, β² = β_m² − β_i² "
          "(both Gaussian), with K = 0.9. Line positions here are exact Bragg angles; relative heights come from a "
          "simple model, not structure factors.")


def xrd_analysis() -> dict:
    return _xrd("um8-xrd-analysis", "XRD of copper powder: lattice parameter and crystallite size",
                "Record the powder pattern of nanocrystalline copper with Cu K-alpha X-rays, index the lines to find "
                "the lattice type and the cubic lattice parameter, and find the crystallite size from the (111) width.",
                {"lat": 2.0, "a": 3.6149e-10, "L": 3.5e-8, "binst": 0.08, "ph": 1.0, "pk": 1.0, "pl": 1.0},
                {"reading": "L", "textbook": "um8_scherrer"},
                XRD_TH + " For a cubic lattice 1/d² = (h² + k² + l²)/a², so the ratios of sin²θ of the lines are the "
                         "ratios of the integers N = h² + k² + l²: 3, 4, 8, 11, 12 is face-centred, 2, 4, 6, 8 body-"
                         "centred, 3, 8, 11, 16 diamond. Each indexed line then gives a = λ√N / (2 sin θ).",
                ["Load the powder and scan 2θ from 20° to 100°.", "Read the angle of every line.",
                 "Work out sin²θ, divide by the first, and find the integers N: they name the lattice.",
                 "a = λ√N / (2 sin θ) for each line; take the mean.",
                 "Scan the first line slowly, read its full width at half maximum, take off the instrument width, and use Scherrer."],
                [{"q": "Lines with N = 3, 4, 8, 11, 12 mean the lattice is", "options": ["Face-centred cubic", "Body-centred cubic",
                  "Simple cubic"], "answer": 0, "why": "Only unmixed h, k, l (all odd or all even) survive in fcc."},
                 {"q": "Smaller crystallites give", "options": ["Broader lines", "Sharper lines", "Lines at new angles"],
                  "answer": 0, "why": "Fewer planes interfere, so the reflection is less sharp: β ∝ 1/L."}],
                "the copper powder")


def nano_xrd() -> dict:
    return _xrd("um8-nano-xrd", "Crystallite size of CdS nanoparticles by XRD (Scherrer)",
                "Scan the strongest diffraction line of a CdS nanopowder slowly, measure its width, take off the "
                "instrument's width, and find the crystallite size with the Scherrer equation.",
                {"lat": 2.0, "a": 5.818e-10, "L": 6.0e-9, "binst": 0.08, "ph": 1.0, "pk": 1.0, "pl": 1.0},
                {"reading": "L", "textbook": "um8_scherrer"},
                XRD_TH + " The powder is the product of a wet-chemical synthesis; that synthesis is NOT simulated here. "
                         "What is measured is the diffraction line width of the dried powder and the size it gives.",
                ["Load the dried nanopowder and scan 2θ from 20° to 70° to find the strongest line.",
                 "Scan that line slowly in small steps of 2θ.", "Read its full width at half maximum β_m.",
                 "Take off the instrument's width (from a coarse-grained standard): β² = β_m² − β_i².",
                 "L = 0.9 λ / (β cos θ), with β in radians."],
                [{"q": "The Scherrer equation gives", "options": ["The crystallite size", "The lattice parameter",
                  "The particle's mass"], "answer": 0, "why": "L = Kλ/(β cos θ) is a size from a width."},
                 {"q": "The instrument width must be taken off because", "options": ["It broadens every line even for big crystals",
                  "It shifts the lines", "It is zero"], "answer": 0, "why": "Without it the size comes out too small."}],
                "the nanopowder")


# =============================================================================================== band gap from I_s(T)
def diode_band_gap() -> dict:
    return lab(
        id="um8-diode-band-gap", rig="um8-junction-oven",
        title="Band gap of germanium from a reverse-biased p-n junction", group="Physics · Solid State Physics",
        level="B.Sc.", topic="Solid State Physics", chapter="Solid state physics and materials",
        aim="Hold a germanium junction diode at a small reverse bias in a heated bath, read the reverse saturation "
            "current from room temperature to about 80 °C, and find the band gap from the slope of ln(I_s/T³) "
            "against 1/T.",
        kernel="um8_revsat", params={"Eg": 0.66, "I300": 2.0e-6, "Vr": 1.0, "T0": 27.0, "Tset": 27.0, "tau": 120.0},
        speeds=[1, 5, 10, 30], autorun=True, camera={"pos": [0.0, 0.6, 0.85], "look": [0, 0.08, -0.08]}, floor=-0.03,
        bodies=[board(1.0, 0.6),
                B("beaker", "cylinder", name="Oil bath", r=0.06, h=0.12, open=True, pos=[-0.25, 0.08, -0.1], color="glass", opacity=0.4),
                B("plate", "box", name="Hot plate", size=[0.18, 0.03, 0.18], pos=[-0.25, 0.015, -0.1], color="#2b2f36"),
                B("meter", "box", name="Microammeter", size=[0.14, 0.08, 0.1], pos=[0.15, 0.04, -0.1], color="#2b2f36")],
        knobs=[knob("Tset", "Bath set point", "Tset", 25, 85, 1, 27, "°C"),
               knob("Vr", "Reverse bias", "Vr", 0.2, 3, 0.1, 1, "V"),
               knob("Eg", "This crystal (its band gap is hidden)", "Eg", 0.3, 1.5, 0.001, 0.66, "eV", hidden=True)],
        instruments=[inst("T", "readout", "Bath temperature", "T", unit="°C", lc=0.1, digits=1),
                     inst("I", "readout", "Reverse current", "I_uA", unit="µA", lc=0.01, digits=2),
                     inst("gr", "graph", "Reverse current against time", "I_uA", x="t", xlabel="t (s)")],
        steps=["Connect the diode in reverse bias through the microammeter; set about 1 V.",
               "Put the diode and the thermometer side by side in the oil bath.",
               "Raise the set point in steps of 5 to 10 °C; at each, wait for the temperature to settle.",
               "Read the temperature and the reverse current at each step.",
               "Plot ln(I_s/T³) against 1/T: the slope is −Eg/k."],
        theory="In reverse bias a p-n junction passes only the saturation current I_s carried by minority carriers. "
               "Their number grows with the intrinsic carrier density, nᵢ² ∝ T³ exp(−Eg/kT), so I_s = C T³ "
               "exp(−Eg/kT). A plot of ln(I_s/T³) against 1/T is a straight line of slope −Eg/k. A few tenths of a "
               "volt of reverse bias is already enough to saturate the current. The band gap is taken as constant "
               "over the range used; in germanium it falls by about 0.4 meV per kelvin, a small effect here. A "
               "silicon diode is not used: its reverse current at these temperatures is the generation current of "
               "the depletion layer, which grows as exp(−Eg/2kT) and would give half the gap.",
        safety="The oil bath gets hot: never above 90 °C, keep the thermometer and the diode leads clear of the "
               "heater, and let the bath cool before taking the diode out.",
        tour=[{"say": "A germanium diode and a thermometer in an oil bath on a hot plate, with the battery and the microammeter."},
              {"set": {"Tset": 27}, "say": "At room temperature the reverse current is about two microamperes."},
              {"set": {"Tset": 80}, "say": "At 80 °C it is about seventy times larger: the current grows exponentially with temperature."}],
        questions=[{"q": "The slope of ln(I_s/T³) against 1/T is", "options": ["−Eg/k", "−kT", "Eg/e"], "answer": 0,
                    "why": "I_s = C T³ exp(−Eg/kT)."},
                   {"q": "Why does the reverse current rise with temperature?", "options": [
                       "More electron-hole pairs are made across the gap", "The diode expands", "The bias rises"],
                    "answer": 0, "why": "The minority carriers come from thermal generation across Eg."}],
        sources=[DU, SZE, SIM, {"title": "I300 = 2 µA", "note": "the saturation current of this particular diode at 300 K, a design value, illustrative"}],
        check={"reading": "Eg", "textbook": "um8_eg"},
    )


# =============================================================================================== piezoelectric coupling
def piezo_coupling() -> dict:
    return lab(
        id="um8-piezo-coupling", rig="um8-piezo-bench",
        title="Electromechanical coupling coefficient of a PZT disc", group="Physics · Solid State Physics",
        level="B.Sc.", topic="Solid State Physics", chapter="Solid state physics and materials",
        aim="Drive a PZT ceramic disc through a sense resistor, sweep the frequency through its radial resonance, find "
            "the resonance (current maximum) and antiresonance (current minimum), and work out the coupling coefficient.",
        kernel="um8_piezo", params={"f": 90000.0, "fs": 100000.0, "C0": 2.0e-9, "k": 0.6, "R1": 4.0, "Rs": 100.0, "V0": 1.0},
        autorun=True, camera={"pos": [0.0, 0.6, 0.85], "look": [0, 0.08, -0.08]}, floor=-0.03,
        bodies=[board(1.0, 0.6),
                B("gen", "box", name="Function generator", size=[0.26, 0.1, 0.2], pos=[-0.28, 0.05, -0.1], color="#2b2f36"),
                B("disc", "cylinder", name="PZT disc in its holder", r=0.02, h=0.002, pos=[0.0, 0.06, -0.1], color="steel"),
                B("mv", "box", name="AC millivoltmeter", size=[0.18, 0.1, 0.16], pos=[0.28, 0.05, -0.1], color="#3a4f6e")],
        knobs=[knob("f", "Generator frequency", "f", 50, 200, 0.01, 90, "kHz", 1000.0),
               knob("k", "This disc (its coupling coefficient is hidden)", "k", 0.05, 0.8, 0.001, 0.6, "", hidden=True)],
        instruments=[inst("v", "readout", "Voltage across the sense resistor", "Vr", k=1000, unit="mV", digits=1),
                     inst("gr", "graph", "Sense voltage against frequency", "Vr", k=1000, x="p.f", xk=0.001, xlabel="f (kHz)")],
        steps=["Connect the disc in series with the 100 ohm sense resistor across the generator; read the voltage across the resistor.",
               "Sweep the frequency coarsely and find the sharp maximum and the sharp minimum of the voltage.",
               "Sweep slowly through each in small steps: the maximum is the resonance fr, the minimum the antiresonance fa.",
               "k_eff^2 = 1 - (fr/fa)^2."],
        theory="A piezoelectric disc turns an alternating voltage into a mechanical vibration and back. Near a "
               "mechanical resonance it behaves like a series R-L-C branch (the moving mass, the compliance and the "
               "losses) in parallel with the disc's own capacitance C0: the Butterworth-Van Dyke circuit. At the "
               "resonance fr the motional branch is a short and the current is largest; a little higher, at the "
               "antiresonance fa, the branch and C0 form a parallel resonance and the current almost vanishes. The "
               "gap between them measures how much of the electrical energy is turned into mechanical energy: "
               "k_eff^2 = 1 - (fr/fa)^2 = C1/(C0 + C1).",
        safety="The generator gives only a few volts. Hold the disc by its edge in the spring holder; the ceramic is brittle.",
        tour=[{"say": "A function generator, the PZT disc in its holder in series with a sense resistor, and an AC millivoltmeter."},
              {"set": {"f": 100}, "say": "At the resonance the disc rings and the current is largest."},
              {"set": {"f": 125}, "say": "At the antiresonance the current almost vanishes."}],
        questions=[{"q": "The coupling coefficient comes from", "options": [
            "k^2 = 1 - (fr/fa)^2", "k = fr/fa", "k = fa - fr"], "answer": 0,
            "why": "In the BVD circuit (fa/fr)^2 = 1 + C1/C0, so 1 - (fr/fa)^2 = C1/(C0 + C1) = k^2."},
            {"q": "A larger coupling coefficient means", "options": [
                "fr and fa further apart", "fr and fa closer", "no resonance"], "answer": 0,
             "why": "More of the energy is mechanical, so the motional capacitance C1 is a larger share."}],
        sources=[DU, {"title": "IEEE Std 176-1987, Standard on Piezoelectricity: the Butterworth-Van Dyke circuit, k_eff^2 = (fa^2 - fr^2)/fa^2"},
                 {"title": "PZT-5A type ceramic: planar coupling k_p about 0.60", "note": "typical manufacturer value - from memory - verify"},
                 {"title": "C0 = 2 nF, fs = 100 kHz, R1 = 4 ohm", "note": "design values of this disc, illustrative"}, SIM],
        check={"reading": "k", "textbook": "um8_keff"},
    )


# =============================================================================================== Gouy balance
def gouy() -> dict:
    return lab(
        id="um8-gouy", rig="um8-gouy-bench",
        title="Magnetic susceptibility of copper sulphate by the Gouy balance", group="Physics · Solid State Physics",
        level="B.Sc.", topic="Solid State Physics", chapter="Solid state physics and materials",
        aim="Hang a tube of powdered copper sulphate from a balance with its lower end between the poles of an "
            "electromagnet, read the pull at several fields, and find the molar susceptibility from the slope of the "
            "mass change against B squared.",
        kernel="um8_gouy", params={"I": 0.0, "chim": 1460.0, "rho": 1.2, "M": 249.68, "A": 5.0e-5},
        autorun=True, camera={"pos": [0.0, 0.7, 0.9], "look": [0, 0.15, -0.1]}, floor=-0.03,
        bodies=[board(1.0, 0.6),
                B("yoke", "box", name="Electromagnet", size=[0.3, 0.16, 0.12], pos=[-0.1, 0.08, -0.12], color="#3b4048"),
                B("bal", "box", name="Analytical balance", size=[0.22, 0.16, 0.18], pos=[-0.1, 0.42, -0.12], color="#d7d3c9"),
                B("tube", "cylinder", name="Gouy tube of powder", r=0.004, h=0.16, pos=[-0.1, 0.22, -0.12], color="glass")],
        knobs=[knob("I", "Magnet current", "I", 0, 5, 0.1, 0, "A"),
               knob("chim", "This salt (its molar susceptibility is hidden)", "chim", 100, 20000, 1, 1460, "1e-6 cm³/mol",
                    hidden=True)],
        instruments=[inst("B", "readout", "Field in the gap", "B", unit="T", lc=0.001, digits=3),
                     inst("m", "readout", "Balance reading", "m", k=1000, unit="g", lc=0.0001, digits=4)],
        steps=["Fill the tube evenly with the powder to a mark, and weigh it with the magnet off.",
               "Raise the magnet current in steps; at each, read the gaussmeter and the balance.",
               "Work out the apparent gain in mass dm at each field.",
               "Plot dm against B^2: the slope is (chi_v - chi_air) A / (2 mu0 g).",
               "Turn chi_v into the molar susceptibility with the packed density and the molar mass."],
        theory="A paramagnetic sample is pulled into a strong field. In the Gouy method a long uniform column of the "
               "sample hangs with its lower end in the field B and its upper end in none, so the force does not depend "
               "on how the field varies in between: F = (chi_v - chi_air) A B^2 / (2 mu0). The balance shows it as an "
               "apparent gain in mass dm = F/g. A copper(II) salt is paramagnetic because each Cu2+ ion carries one "
               "unpaired electron spin. The volume susceptibility of the packed powder becomes the molar one with "
               "chi_m(cgs) = chi_v M / (4 pi rho), with rho the packed density of the powder in the tube.",
        safety="Keep watches, phones and steel tools away from the magnet. Turn the current down slowly before switching "
               "off: the coils have a large inductance.",
        tour=[{"say": "A long glass tube of copper sulphate hangs from the balance, its lower end between the pole pieces."},
              {"set": {"I": 0}, "say": "Magnet off: the true weight of the tube."},
              {"set": {"I": 4}, "say": "With about 0.8 tesla the tube appears a hundred milligrams heavier: it is pulled into the field."}],
        questions=[{"q": "The apparent mass change grows as", "options": ["B squared", "B", "1/B"], "answer": 0,
                    "why": "The induced moment is proportional to B and so is the field acting on it."},
                   {"q": "The upper end of the tube must be", "options": ["Far out of the field", "In the strongest field",
                    "Inside the pole pieces"], "answer": 0, "why": "Then the force depends only on the field at the lower end."}],
        sources=[DU, {"title": "Gouy method: F = (chi_v - chi_air) A B^2 / (2 mu0); CODATA mu0", "note": "standard B.Sc. texts"},
                 {"title": "CRC Handbook of Chemistry and Physics, 'Magnetic susceptibility of the elements and inorganic compounds': CuSO4.5H2O +1460e-6 cm^3/mol",
                  "note": "from memory - verify"},
                 {"title": "Packed density 1.2 g/cm^3, tube cross-section 0.50 cm^2", "note": "values of this tube and filling, illustrative"}, SIM],
        check={"reading": "chim", "textbook": "um8_chim"},
    )


BUILDERS = (beta_absorption, k40_salt, ion_energy_loss, ion_proton_range, ion_projectile_z, ion_bragg,
            xrd_analysis, nano_xrd, diode_band_gap, piezo_coupling, gouy)
