"""Prayogshala lab pack: Ph.D. research techniques, wave 10 - X-ray and electron methods, thin films and vacuum, plasma
diagnostics.

One rig serves every lab - `app/static/prayog/exp/px10-workstation.js`: a real workstation (desk mat, monitor,
keyboard with a live Enter key, mouse, tower, printed method card) and, beside it, the research instrument that
recorded the data. These are research instruments a student cannot handle at a bench, so every lab ANALYSES SIMULATED
DATA and says so in its aim: the record comes from the kernel with a hidden sample value and seeded noise, and the
analysis is the real one. Sample values (a film's stress, a crystal's mosaic spread, a cantilever's spring constant)
are illustrative unless a source is named; every material constant the analysis uses carries its source, or
"from memory - verify".

Physics: the `phd_xfilm_w10` kernel pack (never catalog.py / kernels.py). Each check compares the analysed answer
with the kernel's hidden value within 1 %. English only.
"""
from __future__ import annotations

from ..catalog import B, col, inst, lab

SIM = {"title": "Hoola Prayogshala kernel", "note": "the record and the numbers come from the simulation code; checked "
                                                    "against the hidden value in Hoola's tests"}
SIMDATA = {"title": "SIMULATED DATA", "note": "the instrument record is generated from a hidden, illustrative sample value "
                                              "with seeded noise; the analysis is real, the measurement is not"}
CODATA = {"title": "SI 2019 exact constants (h, e, c, kB, NA) and CODATA 2018 (electron mass, eps0, classical electron "
                   "radius)", "note": "used for electron wavelengths, cross-sections, cut-off densities and kB T"}
ILLUS = {"title": "Unsourced / illustrative sample values", "note": "the sample's own numbers are chosen for the lab, "
                                                                   "not looked up in a table"}
MIT = {"title": "MIT Junior Lab (8.13 / 8.14) experiment guides: X-Ray Physics; Rutherford Scattering",
       "note": "the research-technique list of the syllabus row; cited, not re-fetched"}
NIST_X = {"title": "R. D. Deslattes et al., X-ray transition energies, Rev. Mod. Phys. 75 (2003) 35 (NIST X-ray Transition "
                   "Energies Database)",
          "note": "K-alpha1 and K-edge energies of Cu, Zn, Zr, Mo, Ag used here: from memory - verify against the database"}
MOSELEY = {"title": "H. G. J. Moseley, Phil. Mag. 26 (1913) 1024 and 27 (1914) 703", "note": "the law sqrt(E) ~ (Z - sigma)"}
RUTH = {"title": "E. Rutherford, Phil. Mag. 21 (1911) 669; H. Geiger and E. Marsden, Phil. Mag. 25 (1913) 604",
        "note": "the point-Coulomb cross-section, (z Z e^2 / (16 pi eps0 E))^2 / sin^4(theta/2)"}
AM241 = {"title": "Am-241 main alpha energy 5.486 MeV; gold 19.32 g/cm3, 196.967 g/mol; aluminium 2.699 g/cm3, 26.982 g/mol",
         "note": "from memory - verify against NNDC (alpha energy) and the CRC Handbook (densities, IUPAC molar masses)"}
HUTCH = {"title": "I. H. Hutchinson, Principles of Plasma Diagnostics, 2nd ed. (Cambridge University Press, 2002)",
         "note": "refractive-index measurements: the cut-off density, the phase of a slab and the line-integral form"}
OHRING = {"title": "M. Ohring, Materials Science of Thin Films, 2nd ed. (Academic Press, 2002)",
          "note": "film-thickness measurement, Stoney's equation, spin coating, evaporation; cited, not re-fetched"}
ISO_STEP = {"title": "ISO 5436-1 (step-height measurement standards) and ISO 4287 (Rq)",
            "note": "the two-level step evaluation and the rms roughness; cited, not re-fetched"}
STONEY = {"title": "G. G. Stoney, Proc. R. Soc. London A 82 (1909) 172", "note": "film stress from substrate curvature"}
SI_MOD = {"title": "Si(100) biaxial modulus E/(1 - nu) = 180.5 GPa; aluminium E = 70 GPa, nu = 0.35, alpha = 23.1e-6 /K; "
                   "silicon alpha = 2.6e-6 /K; SiO2 E = 72 GPa, nu = 0.17, alpha = 0.55e-6 /K",
          "note": "from memory - verify against W. A. Brantley, J. Appl. Phys. 44 (1973) 534 and the CRC Handbook"}
MEYER = {"title": "D. Meyerhofer, J. Appl. Phys. 49 (1978) 3993; A. G. Emslie, F. T. Bonner and L. G. Peck, J. Appl. Phys. "
                  "29 (1958) 858", "note": "spin coating with evaporation (h ~ w^-1/2) and the flow stage; cited, not re-fetched"}
BARS = {"title": "E. Barsoukov and J. R. Macdonald (eds.), Impedance Spectroscopy, 2nd ed. (Wiley, 2005)",
        "note": "parallel RC arcs, the brick-layer picture of grains and boundaries, Arrhenius analysis; cited, not re-fetched"}
CULLITY = {"title": "B. D. Cullity and S. R. Stock, Elements of X-ray Diffraction, 3rd ed. (Prentice Hall, 2001)",
           "note": "Bragg's law, single-crystal methods, rocking curves; cited, not re-fetched"}
SI_LAT = {"title": "Silicon lattice parameter 0.5431020 nm (CODATA); Cu K-alpha1 0.1540562 nm",
          "note": "from memory - verify against CODATA and G. Hoelzer et al., Phys. Rev. A 56 (1997) 4554"}
SAUER = {"title": "G. Sauerbrey, Z. Phys. 155 (1959) 206", "note": "the quartz-crystal mass sensitivity 2 f0^2 / sqrt(rho_q mu_q)"}
QUARTZ = {"title": "AT-cut quartz: density 2648 kg/m3, shear modulus 2.947e10 Pa",
          "note": "from memory - verify against the QCM maker's data (the values in the Sauerbrey constant)"}
FILMRHO = {"title": "Bulk densities: titanium 4.506 g/cm3, fused silica 2.20 g/cm3, rutile TiO2 4.23 g/cm3",
           "note": "from memory - verify against the CRC Handbook; evaporated oxide films are usually less dense than bulk"}
HUTTER = {"title": "J. L. Hutter and J. Bechhoefer, Rev. Sci. Instrum. 64 (1993) 1868; H.-J. Butt and M. Jaschke, "
                   "Nanotechnology 6 (1995) 1", "note": "the thermal-noise spring constant; the 0.817 first-mode correction is "
                                                         "named, not applied"}
DU = {"title": "M.Sc. / research physics syllabus 2025, Department of Physics and Astrophysics, University of Delhi",
      "note": "PH-DSE5112 AFM; research techniques"}
MOS2 = {"title": "MoS2 monolayer thickness about 0.65 nm; MoS2 in-plane lattice a = 0.3160 nm",
        "note": "from memory - verify (e.g. K. F. Mak et al., Phys. Rev. Lett. 105 (2010) 136805; ICDD)"}
WILLIAMS = {"title": "D. B. Williams and C. B. Carter, Transmission Electron Microscopy, 2nd ed. (Springer, 2009)",
            "note": "the relativistic electron wavelength, the camera equation R d = lambda L, ring and spot indexing"}
FCC = {"title": "Lattice parameters: gold 0.40782 nm, aluminium 0.40495 nm (fcc)", "note": "from memory - verify against ICDD "
                                                                                          "cards 04-0784 and 04-0787"}
CHEN = {"title": "C. J. Chen, Introduction to Scanning Tunneling Microscopy, 2nd ed. (Oxford University Press, 2008)",
        "note": "the tunnelling decay constant, apparent barrier heights and dI/dV spectroscopy; cited, not re-fetched"}
STMDATA = {"title": "Au(111) nearest-neighbour spacing 0.2884 nm (= a / sqrt 2); HOPG surface lattice 0.246 nm; Au(111) "
                    "Shockley surface-state onset about -0.487 eV",
           "note": "from memory - verify (e.g. J. Kliewer et al., Science 288 (2000) 1399 for the surface state)"}

LEVEL = "Ph.D."
G_X = "Physics · X-ray and Electron Methods"
G_F = "Physics · Thin Films and Vacuum"
G_P = "Physics · Plasma Diagnostics"
CH_X = "X-ray and electron methods"
CH_F = "Thin films and vacuum"
CH_P = "Plasma diagnostics"


def _station(caption: str, instrument: str, sample: str) -> list[dict]:
    return [
        B("mat", "box", name="Desk mat", size=[0.9, 0.004, 0.45], pos=[0.12, 0.002, -0.14], color="black", cut=False),
        B("bezel", "box", name="Monitor", info="The data, the fit and the run log appear here.",
          size=[0.36, 0.235, 0.016], pos=[0.15, 0.228, -0.45], color="#17181b"),
        B("kbd", "box", name="Keyboard", info="Enter runs the analysis at the settings you chose.",
          size=[0.33, 0.014, 0.12], pos=[0.15, 0.007, -0.1], color="#1b1b1d"),
        B("tower", "box", name="Workstation", info="The computer that runs the analysis.",
          size=[0.18, 0.36, 0.38], pos=[0.66, 0.18, -0.5], color="#2b2f36"),
        B("card", "plane", name="Method card", info="The printed card: the problem and the formulas.",
          size=[0.21, 0.297], pos=[-0.13, 0.002, 0.03], rot=[-1.5708, 0, 0], color="white"),
        B("cap", "text", text=caption, size=0.018, pos=[0.15, 0.37, -0.45]),
        B("smp", "text", text=sample, size=0.012, pos=[-0.13, 0.004, 0.2]),
        B("inst", "box", name=instrument, info="The instrument that recorded the data (SIMULATED DATA).",
          size=[0.36, 0.24, 0.32], pos=[-0.6, 0.12, -0.47], color="#e7e9ec"),
    ]


def _q(q: str, options: list[str], why: str) -> dict:
    return {"q": q, "options": options, "answer": 0, "why": why}


def _px(lab_id: str, title: str, topic: str, aim: str, kernel: str, params: dict, check_n: float, theory: str,
        steps: list[str], questions: list[dict], sources: list[dict], caption: str, unit: str, digits: int,
        instrument: str, sample: str, group: str, chapter: str) -> dict:
    return lab(
        id=lab_id, rig="px10-workstation", title=title, group=group, level=LEVEL, topic=topic, chapter=chapter,
        aim=aim, kernel=kernel, params=params, speed=1, speeds=[1],
        camera={"pos": [0.72, 0.68, 1.08], "look": [0.06, 0.12, -0.3]}, floor=-0.02,
        bodies=_station(caption, instrument, sample),
        instruments=[inst("val", "readout", "Answer of the run", "val", unit=unit, digits=digits),
                     inst("used", "readout", "Data used", "nused", digits=0)],
        table={"columns": [col("n", "n (amount of data)", "manual", digits=0),
                           col("val", "Answer", "manual", unit=unit, digits=digits)],
               "calc": "px10_finest", "rows_min": 4, "result_digits": digits,
               "hint": "Analyse the record with more and more of its data; report the answer from the most data."},
        steps=steps, theory=theory,
        safety="Write down the setting and the answer of every run before changing anything, and report no more digits "
               "than the runs agree to. The record is SIMULATED DATA: the analysis is real, the measurement is not.",
        questions=questions, sources=sources + [SIMDATA, SIM],
        check={"params": {"n": check_n}, "reading": "val", "textbook": kernel + "_v"},
    )


def _steps(read: str, last: str) -> list[str]:
    return [read, "Switch the workstation on.", "Choose how much of the record the analysis uses and press Enter.",
            "Write down the answer; use more data and run again, at four settings or more.", last]


# ============================================================================================ X-ray and electron methods
def moseley() -> dict:
    return _px("px10-moseley", "Moseley's law from X-ray fluorescence lines and absorption edges", "X-ray physics",
               "Locate the K-alpha lines (or K edges) of Cu, Zn, Zr, Mo and Ag in X-ray spectra, fit Moseley's law and find the "
               "screening constant, the Rydberg energy or a K-edge energy. SIMULATED DATA from the tabulated energies.",
               "px10_moseley", {"what": 0.0, "method": 0.0, "n": 1024.0}, 4096,
               "An inner-shell vacancy in an atom of atomic number Z is filled by an outer electron, which emits a "
               "characteristic X-ray. Moseley found that the square root of the line energy grows linearly with Z: for the "
               "K-alpha line (an L electron dropping into the K shell) E = (3/4) R (Z - sigma)^2, Bohr's formula for n = 2 "
               "to 1 with the nuclear charge screened by sigma, close to 1. The K absorption edge - the least energy that "
               "ejects a K electron - follows E_K = R (Z - sigma)^2 with its own sigma. A straight line through sqrt(E) "
               "against Z gives sqrt(c R) as its slope (c = 3/4 for the line, 1 for the edge) and sigma = -intercept / slope. "
               "Lines are found as the peak of a fluorescence spectrum; an edge as the steepest rise of mu t = -ln(I / I0) in "
               "a transmission spectrum. The fitted R is not exactly the Rydberg energy 13.606 eV: real inner-shell energies "
               "carry relativistic and screening corrections that a straight line absorbs. SIMULATED DATA: the spectra are "
               "made from the tabulated energies (NIST) with a detector resolution and seeded noise; the reference is the "
               "same fit applied to the tabulated energies.",
               _steps("Read the elements, the detector and the fit from the method card.",
                      "Report sigma and R (or the edge energy) from the finest spectra; compare R with 13.606 eV."),
               [_q("In Moseley's law the quantity that is linear in Z is", ["the square root of the line energy", "the line energy", "the wavelength"],
                   "E = (3/4) R (Z - sigma)^2, so sqrt(E) is linear in Z."),
                _q("An absorption edge is", ["the least photon energy that can eject an electron from that shell", "a fluorescence line", "a detector artefact"],
                   "Above the edge a new photoelectric channel opens and absorption jumps.")],
               [MIT, NIST_X, MOSELEY, CODATA], "MOSELEY: screening sigma", "", 4,
               "X-ray tube and energy-dispersive detector", "Cu, Zn, Zr, Mo, Ag targets", G_X, CH_X)


def rutherford() -> dict:
    return _px("px10-rutherford", "Rutherford scattering of alpha particles: angular law and nuclear charge",
               "Nuclear scattering",
               "Count alphas scattered by gold (and aluminium) foil at eight angles; find the exponent of N ~ sin^-m(theta/2) "
               "and aluminium's nuclear charge against gold. SIMULATED DATA: Rutherford cross-section, Poisson counts.",
               "px10_ruth", {"what": 0.0, "n": 16.0}, 64,
               "An alpha particle (z = 2) of kinetic energy E passing a nucleus of charge Z e is deflected by the Coulomb "
               "force alone. Rutherford's cross-section for a fixed point nucleus is d sigma / d Omega = (z Z e^2 / "
               "(16 pi eps0 E))^2 / sin^4(theta / 2): the count rate at angle theta, N = N0 nt dOmega T d sigma / d Omega, "
               "falls as the fourth power of sin(theta/2), and at a fixed angle grows as Z^2. A straight line through ln N "
               "against ln sin(theta/2) has slope -4. Comparing two foils in the same beam and geometry, (N / nt) / (N_Au / "
               "nt_Au) = (Z / 79)^2 gives the unknown Z. The counts are Poisson: a rate of N counts carries sqrt(N), so long "
               "counting matters most at the large angles where the rate is lowest. Simplifications, said plainly: the "
               "target recoil (small for gold, a few per cent of the angle for aluminium), the energy the alphas lose in the "
               "foil and multiple scattering are left out of the data and the analysis alike. SIMULATED DATA.",
               _steps("Read the source, the foils and the cross-section from the method card.",
                      "Report the exponent (and the nuclear charge of aluminium) from the longest counts."),
               [_q("Rutherford's law predicts the rate falls with angle as", ["1/sin^4(theta/2)", "1/theta^2", "exp(-theta)"],
                   "The point-Coulomb cross-section has sin^4(theta/2) in its denominator."),
                _q("Why are the large-angle counts the least precise?", ["The rate there is lowest, so the Poisson spread is largest relative to the counts", "The detector is farther", "The foil is thinner there"],
                   "A count N has an uncertainty sqrt(N); few counts mean a large relative spread.")],
               [MIT, RUTH, AM241, CODATA], "RUTHERFORD: exponent", "", 4,
               "Vacuum scattering chamber with a silicon detector", "gold foil, 2 um", G_X, CH_X)


def rocking_curve() -> dict:
    return _px("px10-rocking-curve", "High-resolution XRD rocking curve: film strain and mosaic spread", "X-ray diffraction",
               "From the Si 004 omega rocking curve of an epitaxial film find its perpendicular strain (peak splitting) and "
               "mosaic spread (width); for bare silicon, the rocking-curve width. SIMULATED DATA from hidden values.",
               "px10_rock", {"what": 0.0, "n": 2400.0}, 9600,
               "In a high-resolution diffractometer a monochromated, collimated beam meets a single crystal at its Bragg angle "
               "theta_B (lambda = 2 d sin theta) and the sample is rocked through omega. A perfect crystal reflects over only "
               "a few arcseconds (its intrinsic Darwin width, broadened by the instrument). An epitaxial film strained to "
               "its substrate has a different out-of-plane spacing, so its peak sits at a different omega: for the symmetric "
               "004 reflection the perpendicular strain is eps = (d_film - d_sub) / d_sub = -delta_theta cot theta_B. A film "
               "made of slightly tilted mosaic blocks reflects over a wider range: with Gaussian profiles the measured width "
               "is sqrt(w_f^2 + mosaic^2), w_f being the width the film would have without tilts (from its thickness and the "
               "instrument). Each peak is fitted as a Gaussian - a parabola through the logarithm of the counts of its top "
               "half - for its centre and width. SIMULATED DATA: the curve is generated from hidden values with seeded "
               "counting noise.",
               _steps("Read the reflection, the wavelength and the strain and mosaic formulas from the method card.",
                      "Report the strain and the mosaic spread (or the crystal's width) from the finest scan."),
               [_q("A film peak at lower omega than the substrate peak means the film's out-of-plane spacing is", ["larger", "smaller", "the same"],
                   "A lower Bragg angle means a larger d."),
                _q("Mosaic spread broadens a rocking curve because", ["tilted blocks reflect at slightly different omega", "the wavelength spreads", "the film is thinner"],
                   "Each block meets the Bragg condition at its own tilt.")],
               [CULLITY, SI_LAT, ILLUS, CODATA], "ROCKING CURVE: strain", "", 6,
               "High-resolution diffractometer", "Si(0.8)Ge(0.2)-type film on Si(001)", G_X, CH_X)


def tem_saed() -> dict:
    return _px("px10-tem-saed", "TEM: camera constant, ring and spot d-spacings, and particle size", "Electron microscopy",
               "Calibrate the TEM camera constant on gold rings, then find d-spacings of an aluminium film's rings and a "
               "flake's spots, and the size of gold nanoparticles in bright field. SIMULATED DATA from lattice values.",
               "px10_saed", {"what": 0.0, "n": 2048.0}, 4096,
               "In selected-area electron diffraction an electron of wavelength lambda, scattered by lattice planes of "
               "spacing d, reaches the detector at a radius R = lambda L / d (the camera equation; L is the effective camera "
               "length). At 200 kV the electron is relativistic: lambda = h / sqrt(2 m e V (1 + e V / (2 m c^2))) = 2.508 pm. "
               "The camera constant lambda L changes with the lens settings, so it is calibrated with a standard of known "
               "spacings: gold (fcc) gives rings 111, 200, 220, 311 at d = a / sqrt(h^2 + k^2 + l^2), and lambda L = R d "
               "averaged over them. Then any other pattern taken at the same settings gives d = lambda L / R: a "
               "polycrystalline film gives rings, a single-crystal flake a spot pattern (for a hexagonal flake viewed along "
               "[001] six first-order spots at the 100 spacing a sqrt(3)/2). A bright-field image shows nanoparticles as dark "
               "discs; measuring every diameter gives the size distribution and its mean. Every length is read to the "
               "nearest pixel. SIMULATED DATA.",
               _steps("Read the voltage, the standard's lattice and the camera equation from the method card.",
                      "Report the camera constant, the d-spacings and the particle size from the finest images."),
               [_q("The camera equation of electron diffraction is", ["R d = lambda L", "R = d / lambda", "d = 2 R sin theta"],
                   "For small angles the radius is L times the scattering angle lambda / d."),
                _q("A polycrystalline film gives rings and a single crystal gives", ["spots", "rings too", "nothing"],
                   "One orientation diffracts into discrete directions.")],
               [WILLIAMS, FCC, MOS2, CODATA], "SAED: camera constant", "nm mm", 4,
               "Transmission electron microscope", "gold standard (polycrystalline)", G_X, CH_X)


def afm() -> dict:
    return _px("px10-afm", "AFM: thermal-noise spring constant, adhesion, roughness and step height", "Scanning probe microscopy",
               "Find a cantilever's spring constant from its thermal noise, the adhesion on a polymer from a force curve, the "
               "polymer's roughness (tapping) and the step of a grating (contact) and a 2D flake. SIMULATED DATA.",
               "px10_afm", {"what": 0.0, "n": 32768.0}, 262144,
               "An AFM senses the surface with a sharp tip on a cantilever; a laser reflected off the cantilever's back onto a "
               "split photodiode turns its deflection into a voltage. Pressing on a hard surface the deflection equals the "
               "piezo travel, so the inverse slope of that contact line is the optical-lever sensitivity InvOLS (nm per volt). "
               "The free cantilever is a harmonic oscillator in thermal equilibrium: by equipartition (1/2) k <z^2> = "
               "(1/2) kB T, so k = kB T / <z^2>, z = InvOLS x the deflection signal (Hutter and Bechhoefer; Butt and Jaschke's "
               "0.817 correction for the first mode seen by an optical lever is not applied here). On withdrawing from a "
               "sticky surface the tip holds on until the cantilever's pull balances adhesion, then jumps free: the adhesion "
               "force is F = k x InvOLS x the pull-off jump in volts. Images: contact mode drags the tip at constant force "
               "(fine for a hard grating); tapping mode touches only at the bottom of each oscillation (kinder to a polymer "
               "or a flake). A line is levelled and fitted as two levels (the step) or one plane (roughness Rq = rms of "
               "what is left). SIMULATED DATA.",
               _steps("Read how InvOLS, k, the adhesion and the image analysis are done from the method card.",
                      "Report k, the adhesion force, Rq and the step heights from the most data."),
               [_q("The thermal method uses", ["equipartition: (1/2) k <z^2> = (1/2) kB T", "a known weight", "the speed of sound"],
                   "The cantilever's mode carries kB T / 2 of energy."),
                _q("InvOLS is measured on a hard surface because", ["there the deflection equals the piezo travel", "it is flat", "it does not stick"],
                   "Only then is every nanometre of travel a nanometre of bending.")],
               [DU, HUTTER, MOS2, ILLUS, CODATA], "AFM: spring constant", "N/m", 4,
               "Atomic force microscope", "silicon cantilever, nominal 2 N/m", G_X, CH_X)


def stm() -> dict:
    return _px("px10-stm", "STM: atomic lattice, tunnel barrier and surface-state spectroscopy", "Scanning probe microscopy",
               "Find the lattice spacing of Au(111) and HOPG from constant-current line profiles, the tunnel barrier from I(z) "
               "and the Au(111) surface-state onset from dI/dV. SIMULATED DATA from hidden values.", "px10_stm", {"what": 0.0, "n": 600.0}, 1200,
               "Electrons tunnel from a sharp tip to a conducting surface across a vacuum gap of a few angstroms. The current "
               "falls as I ~ exp(-2 kappa z) with kappa = sqrt(2 m phi) / hbar, phi the apparent barrier (an average of the "
               "work functions): about a factor of ten for every 0.1 nm, which is why the topmost atom of the tip carries "
               "the current and atoms can be seen. In constant-current imaging the feedback moves the tip to keep I fixed, "
               "so its height traces the surface: along a close-packed row the atoms are spaced by the lattice spacing "
               "(Au(111) a / sqrt 2, HOPG 0.246 nm). Recording I against z with the feedback off gives ln I linear in z and "
               "phi from its slope. At fixed height, dI/dV at bias V is proportional to the sample's local density of states "
               "at E_F + eV: on Au(111) a two-dimensional Shockley surface-state band adds a step to the LDOS at its band "
               "bottom, about half an electronvolt below E_F. The derivative is taken as the slope of a least-squares line "
               "over +-40 mV of bias (what a lock-in does in a real STM). SIMULATED DATA.",
               _steps("Read the three measurements and their formulas from the method card.",
                      "Report the lattice spacing, the barrier and the surface-state onset from the most data."),
               [_q("The tunnel current changes by about a factor of 10 for", ["each 0.1 nm of tip height", "each 1 nm", "each 1 um"],
                   "2 kappa is about 22 per nm for phi = 4.5 eV."),
                _q("dI/dV at bias V measures", ["the sample's local density of states at E_F + eV", "the tip height", "the lattice spacing"],
                   "For a tip with a flat density of states, the differential conductance follows the sample LDOS.")],
               [CHEN, STMDATA, ILLUS, CODATA], "STM: lattice spacing", "nm", 4,
               "Ultra-high-vacuum STM", "gold (111)", G_X, CH_X)


# ============================================================================================ thin films and vacuum
def ebeam() -> dict:
    return _px("px10-ebeam-qcm", "Electron-beam evaporation: rate against beam power by a quartz crystal monitor",
               "Thin-film deposition",
               "Evaporate titanium, SiO2 or TiO2 by electron beam at five powers; find the rate at each power and the film's "
               "thickness from a quartz crystal monitor by Sauerbrey's equation. SIMULATED DATA from hidden rates.",
               "px10_qcm", {"what": 0.0, "n": 60.0}, 240,
               "An electron beam of a few kilowatts, bent by a magnet onto a crucible, melts and evaporates the source; the "
               "vapour travels in high vacuum and condenses on the substrate and on a quartz crystal beside it. The crystal is "
               "an AT-cut resonator at f0 (6 MHz here): a thin rigid film of mass dm on its area A lowers its frequency by "
               "df = -2 f0^2 dm / (A sqrt(rho_q mu_q)) (Sauerbrey). With the film's density rho, the thickness on the crystal "
               "is dm / (A rho); the tooling factor (the substrate's thickness over the crystal's, found once by measuring a "
               "film) turns it into the substrate's. Holding the power steady, the frequency falls in a straight line; its "
               "slope is the rate. The rate rises steeply with beam power because the source's vapour pressure rises "
               "steeply with its temperature. Sauerbrey's equation needs a thin, rigid film; the acoustic-impedance "
               "correction for thicker films (the z-ratio) is not applied. SIMULATED DATA: the rate at each power is an "
               "illustrative source model; the analysis is Sauerbrey's.",
               _steps("Read the QCM constants, the film density and the tooling factor from the method card.",
                      "Report the rate at each power and the final thickness from the most readings."),
               [_q("A 6 MHz crystal coated with 1 nm of titanium lowers its frequency by about", ["37 Hz", "0.04 Hz", "37 kHz"],
                   "2 f0^2 rho t / sqrt(rho_q mu_q) = 8.15e6 x 4.506e-6 = 36.7 Hz."),
                _q("The tooling factor is needed because", ["the crystal and the substrate see different parts of the vapour plume", "quartz is denser", "the beam is pulsed"],
                   "Flux varies with direction and distance from the source.")],
               [OHRING, SAUER, QUARTZ, FILMRHO, ILLUS], "QCM: deposition rate", "nm/s", 4,
               "Electron-beam evaporator with a QCM", "titanium (e-beam source)", G_F, CH_F)


def spin_coating() -> dict:
    return _px("px10-spin-coating", "Spin coating: film thickness against spin speed and its uniformity", "Thin-film deposition",
               "Spin-coat a polymer (or sol-gel) solution at six speeds, find the law h ~ w^-beta and the thickness at the "
               "working speed, and the film's centre-to-edge uniformity. SIMULATED DATA from hidden values.",
               "px10_spin", {"what": 0.0, "n": 80.0}, 320,
               "A puddle of solution on a spinning wafer thins by two processes. First the liquid flows outward: Emslie, "
               "Bonner and Peck showed that for a Newtonian liquid dh/dt = -(rho w^2 / 3 eta)(1/r) d(r^2 h^3)/dr, whose "
               "solution follows each fluid element outward as r = r0 (1 + 4 K h0^2 t)^(3/4) while it thins as h = h0 / "
               "sqrt(1 + 4 K h0^2 t), K = rho w^2 / (3 eta): a thicker region thins faster, so the film levels itself. Then "
               "the solvent evaporates; Meyerhofer's model, with the evaporation rate rising as w^(1/2), gives a final "
               "thickness h = (1 - c)(3 eta m / (2 rho w^2))^(1/3), i.e. h ~ w^(-1/2) - the law a straight line through ln h "
               "against ln w tests. The prefactor depends on the solution's viscosity and solids, the sample's hidden value. "
               "Uniformity is reported as (h_max - h_min) / h_mean over the wafer, 0 to 0.9 R. SIMULATED DATA.",
               _steps("Read the speeds, the thickness measurement and the two models from the method card.",
                      "Report the exponent, the thickness at the working speed and the uniformity from the most data."),
               [_q("Meyerhofer's model predicts the final thickness goes as", ["w^-1/2", "w^-2", "w"],
                   "Evaporation at a rate ~ w^1/2 with outward flow gives h ~ w^-1/2."),
                _q("Spinning makes a film level because", ["the outward flow grows as h^3, so thick regions thin fastest", "the edge is heated", "the solvent is pushed in"],
                   "Emslie, Bonner and Peck's flow term.")],
               [OHRING, MEYER, ILLUS], "SPIN COATING: thickness", "nm", 2,
               "Spin coater and stylus profilometer", "PMMA solution in anisole", G_F, CH_F)


def profilometry() -> dict:
    return _px("px10-profilometry", "Stylus profilometry: film step height and roughness", "Thin-film metrology",
               "Scan a stylus across the edge of a metal or polymer film on silicon, level the scan and find the step height "
               "and the roughness Rq. SIMULATED DATA from a hidden step and roughness.",
               "px10_profilo", {"what": 0.0, "n": 2000.0}, 8000,
               "A diamond stylus under a few milligrams of force is dragged across the sample while a transducer records its "
               "height. A film that ends at a masked edge leaves a step whose height is the film's thickness. The scan is "
               "tilted (the sample is never perfectly level) and both levels are rough, so the step is evaluated as ISO "
               "5436 does: one common slope and two levels fitted to the regions either side, kept away from the edge itself; "
               "the difference of the levels is the step height. The rms of the residuals is the roughness Rq (ISO 4287). "
               "A real stylus has a tip radius of a few micrometres that smooths short-wavelength roughness; here it is "
               "treated as a point, and the roughness wavelengths are longer than a tip radius. SIMULATED DATA.",
               _steps("Read the scan, the levelling and the roughness definition from the method card.",
                      "Report the step height and Rq of both films from the finest scan."),
               [_q("Why are both levels fitted with one common slope?", ["The sample tilt is the same on both sides of the step", "To remove the roughness", "To make the step larger"],
                   "Levelling with one plane leaves the true height between the levels."),
                _q("Rq is", ["the rms height of the levelled profile", "the step height", "the peak-to-valley height"],
                   "ISO 4287 root-mean-square roughness.")],
               [OHRING, ISO_STEP, ILLUS], "PROFILOMETER: step height", "nm", 3,
               "Stylus profilometer", "aluminium film step on silicon", G_F, CH_F)


def film_stress() -> dict:
    return _px("px10-film-stress", "Film stress by substrate curvature: residual and thermal stress (Stoney)", "Thin-film mechanics",
               "Read a wafer's curvature before and after deposition (laser deflection or profilometer), find the film stress "
               "by Stoney's equation and its slope with temperature. SIMULATED DATA from hidden stresses.",
               "px10_stoney", {"what": 0.0, "method": 0.0, "n": 320.0}, 1280,
               "A stressed film bends its substrate: a film in tension makes the wafer concave, one in compression convex. "
               "For a film much thinner than the substrate, Stoney's equation gives the stress from the change in curvature: "
               "sigma = M_s t_s^2 (1/R - 1/R0) / (6 t_f), M_s = E/(1 - nu) the substrate's biaxial modulus - the film's own "
               "elastic constants are not needed. The curvature can be read with two parallel laser beams d apart reflected "
               "onto a screen L away (the spot separation grows by 2 L d / R) or by scanning the wafer with a profilometer "
               "and fitting a parabola z = x^2 / (2R). The bare wafer is measured first, since no wafer is flat. On heating, "
               "film and substrate expand differently, adding a thermal stress M_f (alpha_s - alpha_f)(T - T0): the slope "
               "of the stress against temperature is -M_f (alpha_f - alpha_s), negative for a metal on silicon, small and "
               "positive for silica. SIMULATED DATA.",
               _steps("Read the wafer, the film and the curvature methods from the method card.",
                      "Report the residual stress and the thermal-stress slope from the most readings."),
               [_q("Stoney's equation needs the elastic constants of", ["the substrate only", "the film only", "both"],
                   "sigma = M_s t_s^2 dk / (6 t_f)."),
                _q("Heating aluminium on silicon makes its stress", ["more compressive", "more tensile", "unchanged"],
                   "Aluminium expands more than silicon but is held to it.")],
               [OHRING, STONEY, SI_MOD, ILLUS], "STONEY: film stress", "MPa", 2,
               "Laser curvature system with a hot stage", "sputtered aluminium film, 0.5 um", G_F, CH_F)


def impedance() -> dict:
    return _px("px10-impedance", "Impedance spectroscopy: grain and boundary resistance, relaxation, activation",
               "Dielectric and ionic materials",
               "From impedance spectra of an ionic pellet, a ceramic capacitor or a polymer film find bulk and grain-boundary "
               "resistance, relaxation times and, from five temperatures, the activation energy. SIMULATED DATA.", "px10_imp", {"what": 0.0, "n": 20.0}, 40,
               "A small AC voltage across a sample gives its impedance Z = Z' + j Z'' at each frequency. A region that both "
               "conducts and stores charge behaves as a resistor R in parallel with a capacitor C: in the Nyquist plane "
               "(-Z'' against Z') it draws a semicircle of diameter R whose top, -Z'' = R/2, is at omega = 1 / (R C). Its "
               "relaxation time tau = R C = eps0 eps_r / sigma is the region's Maxwell relaxation time. In a polycrystalline "
               "ceramic the grains and the thin, resistive grain boundaries are two such regions in series (the brick-layer "
               "picture), giving two arcs far apart in frequency because the boundaries' capacitance is much larger. The "
               "peaks of -Z'' against log f give each R (twice the peak) and tau (1 / 2 pi f_peak). Ionic conduction is "
               "thermally activated, R = R0 exp(Ea / kB T): ln R against 1/T is a straight line of slope Ea / kB. SIMULATED "
               "DATA: the circuit values are illustrative, not a particular material.",
               _steps("Read the equivalent circuit and how the arcs are read from the method card.",
                      "Report Rb, Rgb, the relaxation times and Ea from the most data."),
               [_q("A parallel RC element in a Nyquist plot gives", ["a semicircle of diameter R", "a vertical line", "a point at the origin"],
                   "Z runs from R at low frequency to 0 at high frequency along a semicircle."),
                _q("The grain-boundary arc appears at lower frequency because", ["its R C product is larger", "its R is smaller", "it has no capacitance"],
                   "Thin boundary layers have a large capacitance.")],
               [BARS, ILLUS, CODATA], "IMPEDANCE: bulk resistance", "ohm", 4,
               "Impedance analyser with a sample furnace", "ionic-conductor pellet (YSZ-type)", G_F, CH_F)


PLDREF = {"title": "D. B. Chrisey and G. K. Hubler (eds.), Pulsed Laser Deposition of Thin Films (Wiley, 1994); G. Rijnders "
                  "et al., Appl. Phys. Lett. 70 (1997) 1888 (high-pressure RHEED)", "note": "RHEED oscillations during PLD; cited, not re-fetched"}
CELLS = {"title": "Unit-cell heights: YBa2Cu3O7 c = 1.168 nm, ZnO c / 2 = 0.2604 nm, SrTiO3 a = 0.3905 nm",
         "note": "from memory - verify against ICDD / the original structure papers"}


def pld() -> dict:
    return _px("px10-pld", "Pulsed laser deposition: growth rate per pulse (RHEED) and crystallinity", "Thin-film deposition",
               "Grow YBCO, ZnO or a perovskite oxide by pulsed laser deposition; from the RHEED oscillations find the growth "
               "rate per pulse, and from the film's rocking curve its crystallinity, at several O2 pressures and substrate "
               "temperatures. SIMULATED DATA.", "px10_pld", {"what": 0.0, "n": 10.0}, 50,
               "A nanosecond excimer pulse ablates a ceramic target; the plume of ions and atoms lands on a heated substrate "
               "in a low pressure of oxygen, which keeps the oxide's oxygen content and slows the plume. In layer-by-layer "
               "growth reflection high-energy electron diffraction (RHEED) at grazing incidence sees the specular spot "
               "brightest when a layer is complete and dimmest when it is half full, so its intensity oscillates once per "
               "unit cell. Counting the pulses in one oscillation gives the pulses per unit cell, and the unit-cell height c "
               "over that is the growth rate per pulse - the calibration a PLD grower needs. The oxygen pressure and the "
               "substrate temperature change the rate and the film quality; the crystallinity is judged from the rocking "
               "curve of a film reflection beside the substrate's (its mosaic spread). SIMULATED DATA: the rates and the "
               "mosaic spreads at each condition are illustrative, not a model of the plume or of the growth kinetics.",
               _steps("Read the target, the laser and how the oscillations are counted from the method card.",
                      "Report the growth rate per pulse (and the mosaic spread) at each condition from the most data."),
               [_q("One RHEED intensity oscillation in layer-by-layer growth is", ["one complete unit-cell layer", "one laser pulse", "one oxygen molecule"],
                   "The surface is smoothest each time a layer completes."),
                _q("A narrower film rocking curve means", ["better aligned, more crystalline film", "a thicker substrate", "more oxygen"],
                   "Less mosaic spread = the film's blocks are better aligned.")],
               [OHRING, PLDREF, CELLS, ILLUS], "PLD: rate per pulse", "nm/pulse", 5,
               "PLD chamber with RHEED (KrF laser)", "YBCO target on SrTiO3(001)", G_F, CH_F)


# ============================================================================================ plasma
def mwi() -> dict:
    return _px("px10-mwi-plasma", "Microwave interferometry of an argon discharge: line-integrated electron density",
               "Plasma diagnostics",
               "Record a 35 GHz quadrature interferometer across an argon discharge as it is struck, unwrap the phase and "
               "find the line-integrated electron density. SIMULATED DATA from a hidden density.",
               "px10_mwi", {"n": 1000.0}, 4000,
               "A plasma of electron density n has a refractive index N = sqrt(1 - n / n_c) for a wave of angular frequency "
               "omega, n_c = eps0 m_e omega^2 / e^2 being the cut-off density (1.5 x 10^19 per cubic metre at 35 GHz). A probe "
               "beam crossing a path L of plasma is delayed in phase, relative to a reference arm, by delta phi = (omega/c) "
               "integral (1 - N) dl; for n << n_c this is r_e lambda integral n dl, so the phase measures the line-integrated "
               "density. Here the slab formula is inverted exactly for a uniform slab: integral n dl = n_c L (1 - (1 - delta "
               "phi lambda / 2 pi L)^2). A quadrature detector gives cos phi and sin phi, so the phase is atan2(Q, I), "
               "unwrapped sample by sample - which works only while the phase moves less than half a turn between samples. "
               "SIMULATED DATA: the density rises after the discharge is struck as a hidden, illustrative value.",
               _steps("Read the probe frequency, the path and the inversion from the method card.",
                      "Report the line-integrated density from the record with the most samples."),
               [_q("A microwave interferometer measures", ["the line integral of the electron density along the beam", "the local density at one point", "the electron temperature"],
                   "The phase accumulates along the whole path."),
                _q("Why does a slowly sampled record give a wrong density?", ["The phase jumps more than half a turn between samples and fringes are lost", "The plasma cools", "The horns move"],
                   "Unwrapping cannot tell a jump of phi + 2 pi from phi.")],
               [HUTCH, CODATA, ILLUS], "INTERFEROMETER: n L", "1/m2", 4,
               "35 GHz interferometer", "argon discharge", G_P, CH_P)


BUILDERS = (moseley, rutherford, rocking_curve, tem_saed, afm, stm, ebeam, spin_coating, profilometry, film_stress,
            impedance, mwi, pld)
