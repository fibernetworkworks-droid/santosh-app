"""Prayogshala lab pack: M.Sc. "Computational physics" and "Materials synthesis and characterisation", wave 9.

One rig serves every lab - `app/static/prayog/exp/pc9-workstation.js`, a real workstation (desk mat, monitor,
keyboard with a live Enter key, mouse, tower, printed method card) and, for a characterisation lab, the instrument
that recorded the trace standing beside it.

Two kinds of lab:
  * the photon-attenuation lab is COMPUTATIONAL: the mixture rule over NIST's elemental tables against NIST's compound
    table. The tables were fetched from physics.nist.gov for this pack (see packs/pg_comp_w9.py).
  * every other lab ANALYSES SIMULATED DATA. A synthesis is not a physics measurement, so these labs are claimed only
    for the characterisation result each syllabus row names (a size from the Brus equation, a BET area, a Tg, a mass
    loss, a Williamson-Hall size ...). The trace comes from the kernel with a hidden sample value and seeded noise; the
    lab says SIMULATED DATA in its aim. Sample values (a dot radius, a crystallite size, a Tg) are illustrative,
    not measured; material constants that the analysis needs carry their source, or "from memory - verify".

Physics: the `pg_comp_w9` kernel pack (never catalog.py / kernels.py). Each check compares the analysed answer with
the kernel's reference within 1 %. English only.
"""
from __future__ import annotations

from ..catalog import B, col, inst, lab

SIM = {"title": "Hoola Prayogshala kernel", "note": "the trace and the numbers come from the simulation code; checked "
                                                    "against the hidden value in Hoola's tests"}
SIMDATA = {"title": "SIMULATED DATA", "note": "the instrument trace is generated from a hidden, illustrative sample value "
                                              "with seeded noise; the analysis is real, the measurement is not"}
DU = {"title": "M.Sc. Physics syllabus 2025, Department of Physics and Astrophysics, University of Delhi",
      "note": "PH-DSE5112 Nanomaterials / characterisation and the computational electives"}
MLSU = {"title": "M.Sc. Physics semester III syllabus, Mohanlal Sukhadia University, Udaipur",
        "note": "Nanoscience, Materials Characterization and Radiation Physics laboratories"}
NIST = {"title": "J. H. Hubbell and S. M. Seltzer, Tables of X-Ray Mass Attenuation Coefficients and Mass Energy-Absorption "
                 "Coefficients, NISTIR 5632 (NIST, Standard Reference Database 126)",
        "note": "physics.nist.gov/PhysRefData/XrayMassCoef: tables 1 and 2 (densities, compositions), the element pages "
                "ElemTab/z01 ... z82 and the compound pages ComTab/water, bone, tissue, a150 - fetched 11 Nov 2026"}
XCOM = {"title": "M. J. Berger et al., XCOM: Photon Cross Sections Database (NIST Standard Reference Database 8)",
        "note": "XCOM is a web program that applies the same mixture rule to the same elemental cross-sections; it was not "
                "run for this lab - the tabulated values above were used"}
BRUS = {"title": "L. E. Brus, J. Chem. Phys. 80 (1984) 4403; Y. Kayanuma, Phys. Rev. B 38 (1988) 9797",
        "note": "the effective-mass confinement energy and the 1.786 e^2 / (4 pi eps0 eps R) Coulomb term; cited, not re-fetched"}
TAUC = {"title": "J. Tauc, R. Grigorovici and A. Vancu, Phys. Status Solidi 15 (1966) 627",
        "note": "the (alpha h nu)^2 plot of a direct allowed transition; cited, not re-fetched"}
QDCONST = {"title": "Bulk band gaps, effective masses and dielectric constants of CdS, ZnSe, PbS and CdSe",
           "note": "from memory - verify against a semiconductor data handbook (e.g. O. Madelung, Semiconductors: Data "
                   "Handbook, Springer); typical room-temperature values"}
BET = {"title": "S. Brunauer, P. H. Emmett and E. Teller, J. Am. Chem. Soc. 60 (1938) 309; K. S. W. Sing et al., "
                "Pure Appl. Chem. 57 (1985) 603 (IUPAC)",
       "note": "the BET equation, the 0.05 - 0.30 range and the N2 cross-section 0.162 nm^2; cited, not re-fetched"}
GREGG = {"title": "S. J. Gregg and K. S. W. Sing, Adsorption, Surface Area and Porosity, 2nd ed. (Academic Press, 1982)",
         "note": "the Gurvich total pore volume and d = 4 V / S for cylindrical pores; liquid N2 density 0.808 g/cm3 "
                 "(from memory - verify)"}
ASTM_DSC = {"title": "ASTM E1356 (glass transition by DSC) and ASTM E793 / E794 (enthalpy, melting by DSC)",
            "note": "the half-height midpoint Tg and peak-area enthalpies; cited, not re-fetched"}
WUND = {"title": "B. Wunderlich, Thermal Analysis of Polymeric Materials (Springer, 2005)",
        "note": "heats of fusion of 100 % crystalline polymers: polyethylene 293 J/g, PET 140 J/g - from memory - verify"}
IUPAC_M = {"title": "IUPAC standard atomic weights (abridged): H 1.008, C 12.011, O 15.999, S 32.06, Cl 35.45, Cu 63.546",
           "note": "from memory - verify against the current IUPAC table; the stoichiometric mass losses are computed from them"}
CULLITY = {"title": "B. D. Cullity and S. R. Stock, Elements of X-ray Diffraction, 3rd ed. (Prentice Hall, 2001)",
           "note": "Bragg's law, cubic and hexagonal d-spacings, extinction rules, the Scherrer equation; cited, not re-fetched"}
WH = {"title": "G. K. Williamson and W. H. Hall, Acta Metall. 1 (1953) 22", "note": "size and strain broadening separated"}
CUKA = {"title": "Cu K-alpha1 wavelength 0.154056 nm (G. Hoelzer et al., Phys. Rev. A 56 (1997) 4554)",
        "note": "from memory - verify; rounded to 0.15406 nm in the lab"}
LATT = {"title": "Lattice parameters: Ni 0.35238 nm (ICDD 04-0850), alpha-Fe 0.28665 nm (ICDD 06-0696), Cu 0.36149 nm "
                 "(ICDD 04-0836), ZnO a 0.32498 / c 0.52066 nm (ICDD 36-1451)", "note": "from memory - verify against the ICDD cards"}

LEVEL = "M.Sc."
G_COMP = "Physics · Computational"
G_MAT = "Physics · Materials Physics"
CH_COMP = "Computational physics"
CH_MAT = "Materials synthesis and characterisation"


def _station(caption: str, instrument: str = "", sample: str = "") -> list[dict]:
    b = [
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
    ]
    if sample:
        b.append(B("smp", "text", text=sample, size=0.012, pos=[-0.13, 0.004, 0.2]))
    if instrument:
        b.append(B("inst", "box", name=instrument, info="The instrument that recorded the trace (SIMULATED DATA).",
                   size=[0.36, 0.24, 0.32], pos=[-0.6, 0.12, -0.47], color="#e7e9ec"))
    return b


def _q(q: str, options: list[str], why: str) -> dict:
    return {"q": q, "options": options, "answer": 0, "why": why}


def _pc(lab_id: str, title: str, topic: str, aim: str, kernel: str, params: dict, check_n: float, theory: str,
        steps: list[str], questions: list[dict], sources: list[dict], caption: str, unit: str, digits: int,
        hidden: bool = True, instrument: str = "", group: str = G_MAT, chapter: str = CH_MAT, sample: str = "") -> dict:
    chk = {"params": {"n": check_n}, "reading": "val", "textbook": kernel + "_v"}
    d = lab(
        id=lab_id, rig="pc9-workstation", title=title, group=group, level=LEVEL, topic=topic, chapter=chapter,
        aim=aim, kernel=kernel, params=params, speed=1, speeds=[1],
        camera={"pos": [0.72, 0.68, 1.08], "look": [0.06, 0.12, -0.3]}, floor=-0.02,
        bodies=_station(caption, instrument, sample),
        instruments=[inst("val", "readout", "Answer of the run", "val", unit=unit, digits=digits),
                     inst("used", "readout", "Points used", "nused", digits=0)],
        table={"columns": [col("n", "n (points / energy)", "manual", digits=0),
                           col("val", "Answer", "manual", unit=unit, digits=digits)]
               + ([] if hidden else [col("err", "Relative difference from NIST", "manual", digits=6)]),
               "calc": "pc9_finest" if hidden else "pc9_best", "rows_min": 4, "result_digits": digits,
               "hint": "Analyse the trace with more and more of its points; report the answer from the finest data."
               if hidden else "Scan the energies; report the value at the lab's energy."},
        steps=steps, theory=theory,
        safety="Write down the setting and the answer of every run before changing anything, and report no more digits "
               "than the runs agree to." + (" The trace is SIMULATED DATA: the analysis is real, the measurement is not."
                                           if hidden else ""),
        questions=questions, sources=sources, check=chk,
    )
    return d


def _steps(read: str, last: str) -> list[str]:
    return [read, "Switch the workstation on.", "Choose how many points of the trace the analysis uses and press Enter.",
            "Write down the answer; use more points and run again, at four settings or more.", last]


# ============================================================================================ photon attenuation
def xcom_attenuation() -> dict:
    return _pc("pc9-xcom-attenuation", "Mass attenuation coefficient of water, tissue, bone and lead from NIST's tables",
               "Radiation physics",
               "Build the photon mass attenuation coefficient of a material against energy from NIST's elemental tables by "
               "the mixture rule (what XCOM does), read it at the energy of a source by log-log interpolation, and compare "
               "it with NIST's own table for the material.", "pc9_xcom", {"mat": 0.0, "n": 662.0, "method": 0.0}, 662,
               "A narrow beam of photons is attenuated as I = I0 exp(-(mu/rho) rho x). The mass attenuation coefficient mu/rho "
               "is the sum of the cross-sections of every process - coherent and incoherent (Compton) scattering, the "
               "photoelectric effect and pair production - per gram of material. NIST tabulates it for every element; for a "
               "compound, a tissue or a plastic the mixture rule adds the elements' values weighted by their fractions by "
               "weight, mu/rho = sum w_i (mu/rho)_i, which ignores chemical binding (it matters only near absorption edges). "
               "XCOM is the web program that does this sum. Between tabulated energies log(mu/rho) is close to a straight line "
               "in log E, so values are read by log-log interpolation, never across an absorption edge. The tables used here "
               "were fetched from NIST (NISTIR 5632) for this lab. For lead the material is a single element, so the mixture "
               "has one term and the answer is NIST's elemental table itself; its K edge near 88 keV shows as a jump.",
               ["Read the material, its composition source and the rule from the method card.", "Switch the workstation on.",
                "Choose a photon energy and press Enter; scan from 15 keV to 10 MeV.",
                "Write down the mixture-rule value, NIST's value and their difference at every energy.",
                "Report mu/rho at the source energy (662 keV for Cs-137) and the half-value layer."],
               [_q("The mixture rule weights each element's mu/rho by", ["its fraction by weight", "its atomic number", "its fraction by number of atoms"],
                   "mu/rho is per gram, so each element contributes in proportion to its mass."),
                _q("Above about 100 keV water and bone have nearly the same mu/rho because", ["Compton scattering depends on electrons per gram, nearly equal for them", "they have the same density", "the photoelectric effect dominates"],
                   "Compton scattering is per electron; Z/A is close to 0.5 for both.")],
               [MLSU, NIST, XCOM, SIM], "MIXTURE RULE: mu/rho", "cm2/g", 5, hidden=False, group=G_COMP, chapter=CH_COMP,
               sample="water, liquid (NIST)")


# ============================================================================================ quantum dots
_QD_THEORY = ("A semiconductor crystal only a few nanometres across confines its electron and hole, so its first absorption "
              "moves above the bulk gap. In the effective-mass (Brus) model the first transition is E1 = Eg + h^2/(8 R^2) "
              "(1/me* + 1/mh*) - 1.786 e^2/(4 pi eps0 epsr R): a confinement term rising as 1/R^2 and an electron-hole "
              "attraction falling as 1/R. A UV-Vis spectrum of the dots gives E1 from a Tauc plot: for a direct, allowed "
              "transition (alpha E)^2 rises linearly with E above E1, so a straight line through the middle of the edge "
              "meets the energy axis at E1. Solving the Brus equation for R gives the dot size. The model overestimates the "
              "shift for very small dots, and the constants are bulk values; both limits are part of the discussion. "
              "SIMULATED DATA: the spectrum is generated from a hidden dot radius with seeded detector noise.")
_QD_Q = [_q("In the Brus equation the confinement energy grows as", ["1/R^2", "1/R", "R"],
            "A particle in a box of size R has kinetic energy ~ h^2/(8 m R^2)."),
         _q("A Tauc plot for a direct allowed transition plots", ["(alpha E)^2 against E", "alpha against 1/E", "log alpha against E"],
            "alpha E is proportional to (E - Eg)^(1/2), so its square is linear in E.")]
_QD_STEPS = _steps("Read the bulk constants and the Brus equation from the method card.",
                   "Report the dot radius (or the shift, or the gap) from the finest spectrum and compare it with the bulk value.")


def qd_bandgap() -> dict:
    return _pc("pc9-qd-bandgap", "Quantum dot band gap and size from the absorption edge (Brus model)", "Nanomaterials",
               "Find the optical band gap of CdS quantum dots from a Tauc plot of their absorption spectrum and the dot radius "
               "from the Brus effective-mass equation. SIMULATED DATA: the spectrum is generated from a hidden dot radius.",
               "pc9_qd", {"Eg": 2.42, "me": 0.19, "mh": 0.8, "eps": 8.9, "R": 2.0, "what": 0.0, "n": 160.0}, 640,
               _QD_THEORY, _QD_STEPS, _QD_Q, [MLSU, BRUS, TAUC, QDCONST, SIMDATA, SIM], "BRUS: dot radius", "nm", 3,
               instrument="UV-Vis spectrophotometer", sample="CdS quantum dots")


def qd_glass() -> dict:
    return _pc("pc9-qd-glass", "Size of quantum dots in a glass or polymer matrix from the absorption edge",
               "Nanomaterials",
               "Find the size of CdS dots grown in a glass from the edge of the glass's absorption spectrum: Tauc plot for the "
               "optical gap, then the Brus equation for the radius. SIMULATED DATA: the spectrum is generated from a hidden "
               "dot radius.", "pc9_qd", {"Eg": 2.42, "me": 0.19, "mh": 0.8, "eps": 8.9, "R": 2.8, "what": 0.0, "n": 160.0,
                                         "seed": 23.0}, 640,
               _QD_THEORY + " In a doped glass or polymer film the matrix itself is transparent across the edge, so the "
               "absorption edge is that of the dots.", _QD_STEPS, _QD_Q, [DU, BRUS, TAUC, QDCONST, SIMDATA, SIM],
               "DOTS IN GLASS: radius", "nm", 3, instrument="UV-Vis spectrophotometer", sample="CdS dots in a silicate glass")


def qd_evap() -> dict:
    return _pc("pc9-qd-evap", "Quantum dots by thermal evaporation: dot size and the blue shift of the gap",
               "Nanomaterials",
               "Find the size of CdS quantum dots in a thermally evaporated film and the blue shift of their gap from the bulk "
               "value, from the film's absorption edge (Tauc plot) and the Brus equation. SIMULATED DATA: the spectrum is "
               "generated from a hidden dot radius.", "pc9_qd", {"Eg": 2.42, "me": 0.19, "mh": 0.8, "eps": 8.9, "R": 2.4,
                                                                 "what": 0.0, "n": 160.0, "seed": 31.0}, 640,
               _QD_THEORY + " An evaporated film deposited at a low rate on a cold substrate grows as separate small "
               "crystallites; their size depends on the deposition, and the blue shift E1 - Eg measures it.",
               _QD_STEPS, _QD_Q, [DU, BRUS, TAUC, QDCONST, SIMDATA, SIM], "EVAPORATED DOTS: radius", "nm", 3,
               instrument="UV-Vis spectrophotometer", sample="CdS dots in an evaporated film")


# ============================================================================================ BET
def bet_surface() -> dict:
    return _pc("pc9-bet-surface", "Specific surface area and pore size of a mesoporous powder by BET", "Surface area",
               "Find the specific surface area of a mesoporous powder from its nitrogen adsorption isotherm at 77 K (BET plot) "
               "and its mean pore diameter from the total pore volume (Gurvich, d = 4 V / S). SIMULATED DATA: the isotherm is "
               "generated from a hidden surface area and pore size.", "pc9_bet",
               {"S": 250.0, "C": 100.0, "d": 6.0, "what": 0.0, "n": 48.0}, 192,
               "Nitrogen at 77 K adsorbs on a powder in layers. Brunauer, Emmett and Teller showed that over p/p0 = 0.05 to "
               "0.30 the adsorbed volume v obeys x / (v (1 - x)) = 1/(vm C) + (C - 1) x / (vm C), x = p/p0, so a straight line "
               "through those points gives the monolayer volume vm = 1/(slope + intercept) and the constant C. Each N2 "
               "molecule covers 0.162 nm^2, so the specific surface area is S = vm NA sigma / 22414 (vm in cm3 STP per gram). "
               "Near saturation the pores are full of liquid nitrogen: the uptake at p/p0 = 0.99, turned into a liquid volume "
               "(0.808 g/cm3), is the total pore volume Vp (Gurvich), and for cylindrical pores the mean diameter is 4 Vp / S. "
               "SIMULATED DATA: the isotherm comes from the BET equation up to p/p0 = 0.35 and a pore-filling rise to a "
               "plateau, from a hidden S and pore size, with seeded noise.",
               _steps("Read the BET equation, the N2 cross-section and the pore-size formula from the method card.",
                      "Report the surface area and the pore size from the finest isotherm."),
               [_q("The BET plot gives the monolayer volume as", ["1/(slope + intercept)", "slope/intercept", "intercept/slope"],
                   "slope + intercept = 1/vm."),
                _q("The Gurvich rule assumes the pores are full of", ["liquid nitrogen at its normal density", "gas at STP", "nothing"],
                   "At p/p0 near 1 the pores are filled by capillary condensation.")],
               [DU, BET, GREGG, SIMDATA, SIM], "BET: surface area", "m2/g", 1, instrument="Surface area and pore analyser",
               sample="mesoporous powder")


# ============================================================================================ DSC
def dsc_polymer() -> dict:
    return _pc("pc9-dsc-polymer", "Glass transition, melting and crystallinity of a polymer by DSC", "Thermal analysis",
               "Find the glass transition, the melting point and the degree of crystallinity of PET from a DSC heating scan. "
               "SIMULATED DATA: the scan is generated from hidden sample values.", "pc9_dsc",
               {"what": 0.0, "n": 400.0}, 1600,
               "A differential scanning calorimeter heats a sample and an empty pan at the same rate beta and records the extra "
               "heat flow the sample needs. Divided by beta it is the sample's apparent specific heat. At the glass "
               "transition the specific heat steps up: Tg is taken where the trace is half way between the baselines extended "
               "from below and above the step (the half-height midpoint). Melting is an endothermic peak; its maximum is the "
               "melting point and its area, divided by beta, is the heat of fusion dHm in J/g. A polymer quenched from the "
               "melt, such as PET, also crystallises on heating (cold crystallisation, an exothermic peak of area dHcc), so "
               "the crystallinity it had is Xc = (dHm - dHcc) / dH100, where dH100 is the heat of fusion of a fully "
               "crystalline sample. SIMULATED DATA: the trace is generated from hidden Tg, Tm and enthalpies with seeded "
               "noise; the sample values are illustrative.",
               _steps("Read the analysis windows and dH100 from the method card.",
                      "Report Tg, Tm and the crystallinity from the finest trace."),
               [_q("Why is dHcc subtracted for a quenched PET sample?", ["That crystallinity formed during the scan itself", "It is the glass transition", "It is noise"],
                   "Only the crystals present before the scan describe the sample."),
                _q("Tg by the half-height method is where the trace", ["is midway between the two extrapolated baselines", "is highest", "starts to rise"],
                   "ASTM E1356 midpoint.")],
               [DU, ASTM_DSC, WUND, SIMDATA, SIM], "DSC: Tg", "C", 2, instrument="Differential scanning calorimeter",
               sample="PET, quenched film")


# ============================================================================================ TGA
_MW = {"H": 1.008, "C": 12.011, "O": 15.999, "S": 32.06, "Cl": 35.45, "Cu": 63.546}
_H2O = 2 * _MW["H"] + _MW["O"]
_CUSO4_5H2O = _MW["Cu"] + _MW["S"] + 4 * _MW["O"] + 5 * _H2O
_D_2W = round(100.0 * 2 * _H2O / _CUSO4_5H2O, 4)          # two waters, % of the starting mass
_D_1W = round(100.0 * _H2O / _CUSO4_5H2O, 4)
_PVC = 2 * _MW["C"] + 3 * _MW["H"] + _MW["Cl"]
_D_HCL = round(100.0 * (_MW["H"] + _MW["Cl"]) / _PVC, 4)   # dehydrochlorination of PVC


def tga() -> dict:
    return _pc("pc9-tga", "Decomposition steps and mass loss by thermogravimetry (TGA)", "Thermal analysis",
               "Count the decomposition steps of copper sulphate pentahydrate from its TGA curve, find the mass lost in each "
               "and compare it with the stoichiometry. SIMULATED DATA: the curve is generated from the stoichiometric losses "
               "at illustrative temperatures.", "pc9_tga",
               {"D1": _D_2W, "D2": _D_2W, "D3": _D_1W, "k": 1.0, "what": 0.0, "n": 640.0}, 1280,
               "A thermobalance weighs a sample while it is heated at a constant rate. Each decomposition step - a loss of "
               "water, of HCl, of CO2 - shows as a fall in mass; the derivative curve DTG = -dm/dT has a peak at each step, "
               "which counts the steps and gives the temperature of fastest loss. The mass lost in a step, as a percentage "
               "of the starting mass, identifies what left: copper sulphate pentahydrate CuSO4.5H2O loses two waters, two "
               "more, then the last one, i.e. 100 x 2 M(H2O) / M(CuSO4.5H2O) = %.2f %%, %.2f %% and %.2f %%; PVC first loses "
               "all its HCl, %.2f %% of its mass (dehydrochlorination), and then the remaining polyene breaks down. "
               "SIMULATED DATA: the steps are placed at illustrative temperatures; the masses lost are the stoichiometric "
               "ones (and an illustrative second step for PVC)." % (_D_2W, _D_2W, _D_1W, _D_HCL),
               _steps("Read how the steps are found and measured from the method card.",
                      "Report the number of steps, each mass loss and compare it with the stoichiometric value."),
               [_q("The DTG peak marks", ["the temperature of the fastest mass loss in a step", "the end of the experiment", "the melting point"],
                   "DTG is -dm/dT; it is largest where the mass falls fastest."),
                _q("Losing 14.4 % of CuSO4.5H2O corresponds to", ["two molecules of water", "one molecule of water", "SO3"],
                   "2 x 18.015 / 249.68 = 14.43 %.")],
               [MLSU, IUPAC_M, SIMDATA, SIM], "TGA: mass loss", "%", 3, instrument="Thermogravimetric analyser",
               sample="copper sulphate pentahydrate")


# ============================================================================================ XRD
_XRD_THEORY = ("A powder of crystallites smaller than about 100 nm gives broadened diffraction lines. The Scherrer equation "
               "L = K lambda / (beta cos theta) turns the width beta (FWHM in radians, after the instrument's own width is "
               "taken off) into the crystallite size L, with K = 0.9. Lattice strain also broadens a line, as 4 eps tan "
               "theta, so Williamson and Hall plot beta cos theta against 4 sin theta: the intercept is K lambda / L and the "
               "slope is the microstrain eps. The line positions give the phase: Bragg's law lambda = 2 d sin theta and the "
               "lattice's own sequence of h^2 + k^2 + l^2 (fcc 3, 4, 8, 11, 12; bcc 2, 4, 6, 8) index the lines and give "
               "the lattice parameter a = d sqrt(h^2 + k^2 + l^2). SIMULATED DATA: the diffractogram is generated with Cu "
               "K-alpha1 radiation from a hidden crystallite size and strain, with seeded counting noise.")
_XRD_Q = [_q("In a Williamson-Hall plot the intercept gives", ["the crystallite size", "the strain", "the lattice parameter"],
             "Intercept = K lambda / L."),
          _q("A line that is wider at high angle than Scherrer predicts points to", ["lattice strain", "a larger crystallite", "a shorter wavelength"],
             "Strain broadening grows as tan theta, faster than the size term's 1/cos theta.")]


def xrd_milling() -> dict:
    return _pc("pc9-xrd-milling", "Crystallite size and strain of a ball-milled powder by XRD (Williamson-Hall)",
               "Nanomaterials",
               "Find the crystallite size and lattice strain of a ball-milled iron powder from the widths of its diffraction "
               "lines (Williamson-Hall), and follow the size with milling time. SIMULATED DATA: hidden sizes and strains; "
               "the trend with time is illustrative.", "pc9_xrd",
               {"lat": 1.0, "a": 0.28665, "L": 25.0, "eps": 0.002, "what": 0.0, "n": 4000.0}, 8000,
               _XRD_THEORY + " Milling breaks the grains and strains the lattice, so the size falls and the strain rises "
                             "with milling time.",
               _steps("Read the wavelength, the instrument width and the Williamson-Hall equation from the method card.",
                      "Report the crystallite size and the strain from the finest scan; compare the milling times."),
               _XRD_Q, [MLSU, DU, CULLITY, WH, CUKA, LATT, SIMDATA, SIM], "W-H: crystallite size", "nm", 2,
               instrument="Powder X-ray diffractometer", sample="alpha-iron powder, milled 5 h")


def xrd_nickel() -> dict:
    return _pc("pc9-xrd-nickel", "Nickel nanoparticles: particle size and phase by XRD", "Nanomaterials",
               "Find the crystallite size of nickel nanoparticles made by urea decomposition from the width of their first "
               "diffraction line (Scherrer), and identify the phase by indexing the lines and finding the lattice parameter. "
               "SIMULATED DATA: the diffractogram is generated from a hidden size.", "pc9_xrd",
               {"lat": 0.0, "a": 0.35238, "L": 18.0, "eps": 0.0, "what": 3.0, "n": 4000.0}, 8000,
               _XRD_THEORY + " Nickel nanoparticles that come out as face-centred cubic metal show lines at 44.5, 51.8 and "
                             "76.4 degrees (111, 200, 220); an oxide or hydroxide would show a different sequence.",
               _steps("Read the wavelength, the instrument width and the Scherrer equation from the method card.",
                      "Report the particle size and the lattice parameter, and name the phase."),
               _XRD_Q, [MLSU, CULLITY, CUKA, LATT, SIMDATA, SIM], "SCHERRER: Ni size", "nm", 2,
               instrument="Powder X-ray diffractometer", sample="nickel nanoparticles (urea decomposition)")


# ============================================================================================ TEM
WILLIAMS = {"title": "D. B. Williams and C. B. Carter, Transmission Electron Microscopy, 2nd ed. (Springer, 2009)",
            "note": "the relativistic electron wavelength, the camera equation R d = lambda L and ring indexing; cited, not re-fetched"}
CODATA = {"title": "SI 2019 exact constants (h, e, c) and CODATA 2018 electron mass", "note": "used for the electron wavelength"}
AU = {"title": "Gold lattice parameter 0.40782 nm (fcc)", "note": "from memory - verify against ICDD card 04-0784"}


def tem_grain() -> dict:
    return _pc("pc9-tem-grain", "Grain size and d-spacings of a nanopowder by TEM", "Electron microscopy",
               "Find the mean grain size of a gold nanopowder from a bright-field TEM image and the d-spacings of its "
               "selected-area diffraction rings from the camera equation. SIMULATED DATA: the image and the pattern are "
               "generated from hidden grain sizes.", "pc9_tem", {"what": 0.0, "n": 1024.0}, 4096,
               "A bright-field TEM image shows each grain of a nanopowder as a dark particle; measuring every grain's "
               "diameter and averaging gives the grain size, but no finer than the image's pixel. In selected-area electron "
               "diffraction a polycrystalline powder gives rings: an electron of wavelength lambda scattered by planes of "
               "spacing d reaches the detector at a radius R = lambda L / d, L being the camera length, so d = lambda L / R. "
               "At 200 kV the electron wavelength is relativistic, lambda = h / sqrt(2 m e V (1 + e V / (2 m c^2))) = "
               "2.508 pm. For an fcc metal the rings are 111, 200, 220, 311 ... and d = a / sqrt(h^2 + k^2 + l^2). SIMULATED "
               "DATA: the grains are drawn from a hidden log-normal size distribution; each diameter and each ring radius is "
               "read to the nearest pixel, which is what limits the answer.",
               _steps("Read the accelerating voltage, the camera length and the camera equation from the method card.",
                      "Report the mean grain size and the d-spacing of each ring, and index the rings."),
               [_q("The camera equation of electron diffraction is", ["R d = lambda L", "R = d / lambda", "d = 2 R sin theta"],
                   "For small angles the ring radius is L times the scattering angle 2 theta = lambda / d."),
                _q("At 200 kV the electron wavelength is about", ["2.5 pm", "0.15 nm", "500 nm"],
                   "h / sqrt(2 m e V (1 + eV / 2mc^2)) = 2.51e-12 m.")],
               [DU, WILLIAMS, CODATA, AU, SIMDATA, SIM], "TEM: grain size", "nm", 3,
               instrument="Transmission electron microscope", sample="gold nanopowder")


# ============================================================================================ gas sensor
def gas_sensor() -> dict:
    return _pc("pc9-gas-sensor", "Sensitivity, response and recovery time of a nanostructured gas sensor", "Sensors",
               "Find the sensitivity Ra / Rg of a ZnO film sensor to a reducing gas at its operating temperature, and its "
               "response and recovery times (t90), from its resistance transient. SIMULATED DATA: the transient is generated "
               "from hidden, illustrative sensor values.", "pc9_gas", {"what": 0.0, "n": 900.0}, 3600,
               "An n-type metal-oxide film (ZnO, SnO2) held at a few hundred degrees adsorbs oxygen, which traps electrons "
               "and raises its resistance to Ra. A reducing gas reacts with that oxygen and gives the electrons back, so the "
               "resistance falls to Rg; the sensitivity (response) is S = Ra / Rg. The response time is the time to reach "
               "90 % of the change after the gas is let in, the recovery time the time to come back to within 10 % of Ra "
               "after it is shut off; for an exponential change with time constant tau both equal tau ln 10. The operating "
               "temperature sets how fast the surface reactions run, so S and the times are measured at several temperatures. "
               "SIMULATED DATA: the transient is exponential with hidden, illustrative values; the temperature trend in the "
               "variants is illustrative, not a model of the surface chemistry.",
               _steps("Read how Ra, Rg and the t90 times are taken from the transient on the method card.",
                      "Report the sensitivity and both times at each operating temperature."),
               [_q("For an n-type oxide in a reducing gas the resistance", ["falls", "rises", "stays the same"],
                   "The gas removes adsorbed oxygen, releasing trapped electrons into the conduction band."),
                _q("For an exponential response the 90 % time is", ["tau ln 10 = 2.30 tau", "tau", "tau / 2"],
                   "1 - exp(-t/tau) = 0.9 gives t = tau ln 10.")],
               [DU, SIMDATA, SIM], "GAS SENSOR: Ra/Rg", "", 3, instrument="Gas-sensing test chamber",
               sample="ZnO film sensor at 300 C")


# ============================================================================================ sputtered film
PARRATT = {"title": "L. G. Parratt, Phys. Rev. 95 (1954) 359; H. Kiessig, Ann. Phys. 402 (1931) 769",
           "note": "specular reflectivity of a layer and its thickness fringes; cited, not re-fetched"}
DELTA = {"title": "X-ray refractive-index decrements at Cu K-alpha: copper about 2.2e-5, ZnO about 1.4e-5, silicon 7.6e-6",
         "note": "from memory - verify against the CXRO / Henke tables"}


def sputter_film() -> dict:
    return _pc("pc9-sputter-film", "Sputtered nanophase film: thickness by X-ray reflectivity and grain size by XRD",
               "Thin films",
               "Find the thickness of a sputtered copper film from the Kiessig fringes of its X-ray reflectivity, follow it "
               "with deposition time, and find its grain size from its first diffraction line (Scherrer). SIMULATED DATA: "
               "the scans are generated from hidden thicknesses and grain sizes.", "pc9_film",
               {"d": 20.0, "what": 0.0, "n": 2000.0}, 8000,
               "X-rays reflected from the top and the bottom of a film interfere; the reflectivity above the critical angle "
               "shows fringes (Kiessig fringes) whose spacing is set by the thickness d: the fringe minima obey sin^2 theta_m = "
               "theta_c^2 + (lambda / 2d)^2 (m0 + j)^2, so sin^2 theta of successive minima, j = 0, 1, 2 ..., is a parabola in "
               "j whose leading coefficient (lambda / 2d)^2 gives d without knowing theta_c or the order m0. Thickness against "
               "deposition time gives the deposition rate. A sputtered film is nanocrystalline, so its diffraction lines are "
               "broadened and the Scherrer equation L = K lambda / (beta cos theta) gives the grain size. SIMULATED DATA: the "
               "reflectivity is computed for one film on silicon (no roughness or absorption) from a hidden thickness, the "
               "diffractogram from a hidden grain size; the thicknesses at the deposition times are illustrative.",
               _steps("Read the wavelength and the fringe analysis from the method card.",
                      "Report the thickness at each deposition time, the rate, and the grain size."),
               [_q("Thicker films give Kiessig fringes that are", ["closer together", "further apart", "the same"],
                   "The spacing is about lambda / (2 d) in angle."),
                _q("Why fit sin^2 theta of the minima as a parabola in their number?", ["It removes the unknown order and the critical angle", "It is faster", "Fringes are parabolic"],
                   "The constant and linear terms absorb theta_c and m0; only the leading term holds d.")],
               [DU, PARRATT, DELTA, CULLITY, CUKA, LATT, SIMDATA, SIM], "XRR: film thickness", "nm", 3,
               instrument="X-ray reflectometer / diffractometer", sample="copper film, sputtered 8 min")


def sem_size() -> dict:
    return _pc("pc9-sem-size", "Particle size distribution of a nanopowder and a thin film by SEM", "Electron microscopy",
               "Find the mean particle size and the spread of the size distribution of a nanopowder from an SEM micrograph, "
               "every particle measured to the nearest pixel. SIMULATED DATA: the micrograph is generated from a hidden "
               "log-normal size distribution.", "pc9_tem",
               {"D0": 40.0, "sg": 0.35, "seed": 67.0, "what": 0.0, "n": 1024.0}, 4096,
               "A scanning electron microscope images the surface with a focused electron beam; secondary electrons show "
               "each particle of a powder, or each grain on a film's surface, as a bright outline. Measuring the diameter of "
               "every particle in the field gives the size distribution: its histogram, its mean d = sum d_i / N and its "
               "spread, the standard deviation sqrt(sum (d_i - d)^2 / N). Nanoparticle sizes usually follow a log-normal "
               "distribution. A diameter can be read no finer than one pixel, so the field of view and the number of pixels "
               "across it limit the answer. SIMULATED DATA: the particles are drawn from a hidden log-normal distribution; "
               "the true mean and spread are those of the same particles before the pixel rounding.",
               _steps("Read how the particles are measured from the method card.",
                      "Report the mean size and the spread, and describe the shape of the histogram."),
               [_q("Halving the pixel size", ["reads each diameter twice as finely", "doubles the particle size", "changes nothing"],
                   "A diameter is rounded to the nearest pixel."),
                _q("A log-normal size distribution has", ["a long tail towards large sizes", "a long tail towards small sizes", "no spread"],
                   "The logarithm of the size is normally distributed, so the distribution is skewed to large sizes.")],
               [DU, SIMDATA, SIM], "SEM: particle size", "nm", 3, instrument="Scanning electron microscope",
               sample="oxide nanopowder")


BUILDERS = (xcom_attenuation, qd_bandgap, qd_glass, qd_evap, bet_surface, dsc_polymer, tga, xrd_milling, xrd_nickel,
            tem_grain, gas_sensor, sputter_film, sem_size)
