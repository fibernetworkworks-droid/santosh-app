"""Lab pack `ph2_films`: thin-film, vacuum, X-ray and semiconductor-characterisation benches (see `labs/__init__.py`).
Physics: `packs/ph2_films.py` (+ JS twin). Rigs: `ph2-xrd-bench`, `ph2-film-chamber`, `ph2-semi-bench`.

Honesty, said in the labs that need it: an X-ray diffractometer and a reflectometer are shared facility instruments,
so these are SIMULATED BENCHES that show the measurement, not the operation. The XRD lab refines the lattice
parameter and the phase fractions of a FIXED structure model (atomic positions are not refined), so it is a
Rietveld-style scale-factor refinement, not a full Rietveld refinement. Material numbers marked "unsourced /
illustrative" were not looked up.
"""
from __future__ import annotations

from ..catalog import B, SIM, board, inst, knob, lab

MATS = "Physics · Materials Physics"
VAC = "Physics · Vacuum and Plasma Physics"
SEMI = "Physics · Semiconductor Physics"
CH_XE = "X-ray and electron methods"
CH_TV = "Thin films and vacuum"
CH_SS = "Solid state and materials"
CH_OD = "Optoelectronic and semiconductor devices"

CODATA = {"title": "SI 2019 defining constants (k, e) and CODATA 2018 (classical electron radius, Avogadro constant)"}
CULLITY = {"title": "B. D. Cullity and S. R. Stock, Elements of X-ray Diffraction, 3rd ed. (Prentice Hall, 2001)"}
HILL = {"title": "R. J. Hill and C. J. Howard, J. Appl. Cryst. 20 (1987) 467: quantitative phase analysis from Rietveld scale factors"}
PARRATT = {"title": "L. G. Parratt, Phys. Rev. 95 (1954) 359: surface studies of solids by total reflection of X-rays"}
NEVOT = {"title": "L. Nevot and P. Croce, Rev. Phys. Appl. 15 (1980) 761: roughness in X-ray reflection"}
SAUER = {"title": "G. Sauerbrey, Z. Phys. 155 (1959) 206: the use of quartz crystals for weighing thin layers"}
OHANLON = {"title": "J. F. O'Hanlon, A User's Guide to Vacuum Technology, 3rd ed. (Wiley, 2003): molecular-flow conductance of a long tube"}
SCHRODER = {"title": "D. K. Schroder, Semiconductor Material and Device Characterization, 3rd ed. (Wiley, 2006)"}
VDP = {"title": "L. J. van der Pauw, Philips Res. Reports 13 (1958) 1: a method of measuring specific resistivity and Hall effect of discs of arbitrary shape"}
HS = {"title": "J. R. Haynes and W. Shockley, Phys. Rev. 81 (1951) 835: the mobility and life of injected holes and electrons in germanium"}
SZE = {"title": "S. M. Sze and K. K. Ng, Physics of Semiconductor Devices, 3rd ed. (Wiley, 2007)"}
ILLUS = {"title": "Unsourced / illustrative sample constants",
         "note": "the material numbers of this sample are chosen for the lab, not looked up in a table"}
SIMI = {"title": "SIMULATED BENCH",
        "note": "a shared facility instrument: this bench shows the measurement and its analysis, not the operation of the real machine"}


def _bench() -> list[dict]:
    return [board(1.0, 0.6),
            B("ctl", "box", name="Control unit", info="Sets and reads the control variable of the run.",
              size=[0.2, 0.07, 0.13], pos=[0.3, 0.035, 0.12], color="#2b2f36"),
            B("rd", "box", name="Readout unit", info="Reads the response of the sample.",
              size=[0.2, 0.07, 0.13], pos=[0.3, 0.035, -0.1], color="#2b2f36")]


def _q(q, opts, ans, why):
    return {"q": q, "options": opts, "answer": ans, "why": why}


def _mk(id, rig, title, aim, kernel, params, knobs, insts, steps, theory, safety, tour, questions, sources, check,
        group, chapter, level, topic):
    return lab(id=id, rig=rig, title=title, group=group, level=level, topic=topic, chapter=chapter, aim=aim,
               kernel=kernel, params=params, autorun=True, camera={"pos": [0.0, 0.7, 0.9], "look": [0, 0.04, -0.05]},
               floor=-0.03, bodies=_bench(), knobs=knobs, instruments=insts, steps=steps, theory=theory,
               safety=safety, tour=tour, questions=questions, sources=sources + [SIM], check=check)


XSAFE = ("The X-ray tube is interlocked: never bypass the cabinet door switch. Radiation badges must be worn and the "
         "shutter is opened only from outside the cabinet. In this simulation no beam is live.")


def xrd_refine() -> dict:
    return _mk(
        "ph2-xrd-refine", "ph2-xrd-bench", "Powder XRD: lattice-parameter refinement of silicon",
        "Scan a cubic powder with Cu K-alpha1 X-rays, index every line from the structure model, refine the lattice "
        "parameter by least squares on sin²θ and, for a two-phase mixture, the phase fractions from the refined scale factors.",
        "ph2_xrd", {"tth": 28.0, "lam": 1.5406e-10, "a1": 5.43102e-10, "t1": 1.0, "a2": 0.0, "t2": 0.0, "w1": 1.0,
                    "Lx": 5.0e-8, "binst": 0.08, "bg": 30.0, "I0": 60.0, "seed": 7.0, "tmin": 20.0, "tmax": 100.0},
        [knob("tth", "Detector angle 2θ", "tth", 20, 100, 0.02, 28, "°"),
         knob("a1", "This sample (its lattice parameter is hidden)", "a1", 2.0, 10.0, 0.00001, 5.43102, "Å", 1e-10, hidden=True)],
        [inst("I", "readout", "Counts", "I", digits=0),
         inst("gr", "graph", "Counts against 2θ", "I", x="p.tth", xlabel="2θ (°)", dots=True)],
        ["Load the powder on the stage, close the cabinet door and open the shutter.",
         "Scan 2θ from 20° to 100° in 0.02° steps and let the program find every line (position, width, area).",
         "Choose the structure model from the sample's data card; the program indexes each line with the allowed reflections.",
         "Refine a by least squares on sin²θ = (λ²/4a²) N, and, for a mixture, repeat for the second phase.",
         "For a mixture refine the scale factor S of each phase and take its weight fraction W = S(ZMV) / Σ S(ZMV)."],
        "Bragg's law 2d sinθ = λ with d = a/√N, N = h²+k²+l², puts every line of a cubic powder at sin²θ = (λ²/4a²) N. "
        "The structure factor of the cell decides which N appear (silicon, diamond cubic: 3, 8, 11, 16, 19...; perovskite: "
        "every N; spinel: face-centred with extra absences). Least squares on all lines gives a far better a than any one line. "
        "In a mixture the line areas of a phase scale with S, and the Hill-Howard relation W = S(ZMV)/Σ S(ZMV) turns the "
        "refined scale factors into weight fractions (Z formula units, M formula mass, V cell volume). This bench keeps the "
        "atomic positions fixed at their literature values, so it is a Rietveld-style scale-factor and lattice refinement, "
        "not a full Rietveld refinement; line heights use a simple model scattering factor.",
        XSAFE,
        [{"say": "A powder diffractometer: tube, powder holder on the goniometer, and a detector. This is a simulated bench."},
         {"set": {"tth": 28.44}, "say": "At 28.44° the detector sits on the first (111) line of silicon."}],
        [_q("Why is a least-squares value of a better than one from a single line?",
            ["Every line carries a little angle error and the fit averages them", "It uses a larger wavelength", "It needs no indexing"], 0,
            "Each line's angle has its own small error; the fit over all lines weighs them together."),
         _q("In a two-phase powder the phase with the larger scale factor S has", ["More of the sample, once Z M V is allowed for", "A larger cell", "A longer wavelength"], 0,
            "W = S(ZMV) / Σ S(ZMV): S alone is not the weight fraction.")],
        [CULLITY, HILL, CODATA, SIMI,
         {"title": "Cu K-alpha1 wavelength 1.5406 Å", "note": "standard X-ray wavelength tables; value as supplied in the build brief, not re-looked-up here"}],
        {"reading": "a", "textbook": "ph2_a", "tol": 0.002}, MATS, CH_XE, "Ph.D.", "Powder diffraction")


def xrr_film() -> dict:
    return _mk(
        "ph2-xrr-film", "ph2-xrd-bench", "X-ray reflectivity: thickness of a gold film on silicon",
        "Record the X-ray reflectivity of a film on silicon, locate the Kiessig fringe maxima numerically and find the film "
        "thickness and density from the fringe positions.",
        "ph2_xrr", {"tth": 2.0, "lam": 1.5406e-10, "kind": 1.0, "d1": 4.0e-8, "fa": 0.4, "nrep": 10.0, "rho_f": 19300.0,
                    "ze_f": 0.40106, "rho_b": 2329.0, "ze_b": 0.49848, "rho_s": 2329.0, "ze_s": 0.49848, "sig": 4.0e-10,
                    "bfrac": 0.05, "bgr": 1.0e-8, "seed": 11.0, "tmin": 0.1, "tmax": 5.0},
        [knob("tth", "Detector angle 2θ", "tth", 0.1, 5.0, 0.01, 2.0, "°"),
         knob("d1", "This film (its thickness is hidden)", "d1", 5, 120, 0.01, 40, "nm", 1e-9, hidden=True)],
        [inst("R", "readout", "Reflectivity", "R", digits=5),
         inst("gr", "graph", "Reflectivity against 2θ", "logR", x="p.tth", xlabel="2θ (°)", dots=True)],
        ["Align the sample so that the beam grazes the film surface.",
         "Scan 2θ from 0.1° to 5° in 0.01° steps; the reflectivity falls over four decades and oscillates.",
         "Mark the maxima of the Kiessig fringes above the critical angle.",
         "Number the maxima with consecutive orders m, m+1, ... and plot sin²θ against order².",
         "The slope is (λ/2d)² and the intercept is 2δ; find the thickness d and the density."],
        "Below the critical angle θc = √(2δ) an X-ray beam is totally reflected from a surface; above it the beam enters "
        "the film and the reflections from the top and bottom surfaces interfere. The maxima (Kiessig fringes) follow the "
        "modified Bragg law sin²θm = (mλ/2d)² + 2δ: a plot of sin²θ against m² is a straight line whose slope gives the "
        "thickness d and whose intercept gives δ, hence the electron density. The small-angle form d = λ/(2Δθ) is only "
        "right far above θc, where refraction can be ignored. The curve is the exact Parratt recursion with Névot-Croce "
        "roughness; absorption is a fixed small fraction of δ (illustrative). This is a simulated facility bench.",
        XSAFE,
        [{"say": "A reflectometer: the film on silicon at the centre of the goniometer and a detector arm."},
         {"set": {"tth": 0.8}, "say": "Below the critical angle the beam is totally reflected: the reflectivity is near 1."}],
        [_q("Fringes that are closer together mean a film that is", ["Thicker", "Thinner", "Denser"], 0,
            "The spacing in sinθ is λ/2d."),
         _q("The intercept of sin²θ against m² gives", ["2δ, the refraction term", "The roughness", "The wavelength"], 0,
            "sin²θm = (mλ/2d)² + 2δ.")],
        [PARRATT, NEVOT, CODATA, SIMI, ILLUS,
         {"title": "Gold film on silicon: density 19300 kg/m³ (unsourced / illustrative)", "note": "handbook value entered from memory, not re-checked"}],
        {"reading": "d", "textbook": "ph2_d", "tol": 0.01}, MATS, CH_XE, "Ph.D.", "X-ray reflectivity")


def qcm_evap() -> dict:
    return _mk(
        "ph2-qcm-evap", "ph2-film-chamber", "Thermal evaporation with a quartz crystal monitor: gold",
        "Evaporate a metal under high vacuum, read the quartz crystal's frequency against time, find the deposition rate "
        "from the Sauerbrey relation and the tooling factor from the measured step height.",
        "ph2_qcm", {"t": 0.0, "f0": 6.0e6, "rho_f": 19300.0, "rate": 2.0e-10, "tool": 0.8, "Tdep": 300.0, "rho_q": 2648.0,
                    "mu_q": 2.947e10, "seed": 5.0},
        [knob("t", "Time since the shutter opened", "t", 0, 300, 1, 0, "s"),
         knob("rate", "This source (its rate is hidden)", "rate", 0.01, 2.0, 0.001, 0.2, "nm/s", 1e-9, hidden=True)],
        [inst("f", "readout", "Crystal frequency", "f", unit="Hz", lc=1.0, digits=0),
         inst("gr", "graph", "Frequency against time", "f", x="p.t", xlabel="t (s)", dots=True)],
        ["Pump the chamber to better than 10⁻³ Pa and zero the crystal monitor with the shutter closed.",
         "Raise the source current until the metal glows, open the shutter and start the clock.",
         "Read the crystal frequency every 10 s for 80 s.",
         "Plot f against t: the slope is −C ρf (dh/dt) with C = 2f0²/√(ρq μq).",
         "Close the shutter at 300 s, measure the film step on the substrate and compare it with the monitor's thickness: that ratio is the tooling factor."],
        "A quartz crystal vibrating in thickness-shear mode lowers its frequency when mass is added: Δf = −2 f0² Δm / "
        "(A √(ρq μq)). For a film of density ρf and thickness h, Δm/A = ρf h, so h = −Δf √(ρq μq) / (2 f0² ρf). The "
        "slope of f against time therefore gives the deposition rate on the crystal. The substrate sits at a different "
        "distance and angle from the source, so its film is thinner by the tooling factor, found by comparing the "
        "thickness the monitor reports with a measured step height. The relation is linear only while the loaded "
        "frequency is within about 2 % of f0. Quartz: ρq = 2648 kg/m³, μq = 2.947×10¹⁰ Pa.",
        "The source runs at a high current and is hot. Use the shutter, never reach into the chamber, and vent only when the source has cooled. The chamber is evacuated: keep the bell jar guard in place.",
        [{"say": "A bell-jar evaporator: a boat with the metal, a shutter, the substrate and a quartz crystal beside it."},
         {"set": {"t": 120}, "say": "After two minutes the crystal frequency has dropped by several kilohertz."}],
        [_q("A thicker film on the crystal makes its frequency", ["Fall", "Rise", "Stay the same"], 0, "Mass added lowers the resonance."),
         _q("The tooling factor corrects for", ["The substrate being at a different place from the crystal", "The crystal's density", "The vacuum level"], 0,
            "Substrate thickness = tooling factor × monitor thickness.")],
        [SAUER, CODATA, ILLUS,
         {"title": "Quartz ρq = 2648 kg/m³ and μq = 2.947×10¹⁰ Pa (as given in the build brief)",
          "note": "unsourced here: not re-looked-up in a handbook in this build"},
         {"title": "Gold density 19300 kg/m³ (unsourced / illustrative)", "note": "handbook value entered from memory, not re-checked"}],
        {"reading": "rate", "textbook": "ph2_rate", "tol": 0.01}, MATS, CH_TV, "Ph.D.", "Thin-film deposition")


def vac_research() -> dict:
    return _mk(
        "ph2-vac-research", "ph2-film-chamber", "High-vacuum system: pumping speed, conductance and leak rate",
        "Rough a chamber with a rotary pump, open it to a turbomolecular pump through a pipe, find the pumping speed and the "
        "pipe's conductance from the pump-down, and the leak and outgassing rates from rate-of-rise tests.",
        "ph2_vac", {"t": 0.0, "stage": 1.0, "V": 0.05, "Sr": 0.0028, "Sp": 0.20, "dt": 0.04, "Lt": 0.30, "T": 293.0,
                    "Mgas": 28.96, "Pat": 101325.0, "Px": 10.0, "Pur": 1.0, "QL": 5.0e-6, "QO": 1.0e-4, "tauo": 120.0, "tc": 900.0},
        [knob("t", "Time", "t", 0, 2000, 1, 0, "s"),
         knob("dt", "This pumping line (its bore is hidden)", "dt", 10, 100, 0.1, 40, "mm", 1e-3, hidden=True)],
        [inst("P", "readout", "Gauge pressure", "P", unit="Pa", digits=4),
         inst("gr", "graph", "log10 pressure against time", "logP", x="p.t", xlabel="t (s)", dots=True)],
        ["Close the vent valve and rough the chamber with the rotary pump to 10 Pa.",
         "Open the gate valve to the high-vacuum pump and read the gauge every second for 6 s while the pressure is far above the ultimate pressure.",
         "Plot ln P against t: the slope is −S/V; find the effective speed S and the conductance C from 1/S = 1/Sp + 1/C.",
         "Wait for the pressure to settle, close the gate valve and record the pressure rise: the slope times V is the gas load.",
         "Repeat the rise test late, when the outgassing has died away, to find the leak; the extra load early on is outgassing."],
        "In molecular flow the chamber obeys V dP/dt = −S P + Q. The pump of speed Sp is joined to the chamber by a pipe "
        "of conductance C, so the effective speed is 1/S = 1/Sp + 1/C. Far above the ultimate pressure the gas load is "
        "negligible and P falls as exp(−St/V), which gives S from the slope of ln P. For a long straight pipe of bore d "
        "and length L the conductance is C = (π/12) v̄ d³/L with v̄ = √(8kT/πm), about 12.1 d³/L litres per second for air at "
        "20 °C (d, L in cm). With the pump valved off the pressure rises at (QL + Qout)/V: the leak QL is constant while "
        "outgassing Qout fades with time. Pump speeds here are illustrative nameplate values; this is a simulated system.",
        "The chamber is evacuated: keep guards on glass. Turbomolecular pumps spin at tens of thousands of revolutions per minute; never vent one suddenly. Hot-cathode gauges may be switched on only below 0.1 Pa.",
        [{"say": "A stainless chamber, a gate valve, a pipe to a turbomolecular pump with a rotary backing pump, and a gauge controller."},
         {"set": {"t": 3}, "say": "A few seconds after the gate valve opens the pressure has fallen by a factor of ten."}],
        [_q("Why is the effective pumping speed less than the pump's own speed?", ["The pipe limits the flow", "The gauge reads wrongly", "The gas is heavier"], 0,
            "1/S = 1/Sp + 1/C: the pipe is in series with the pump."),
         _q("A leak and outgassing are told apart by", ["The leak rate staying constant while outgassing fades", "Their colour", "The pump type"], 0,
            "Rate-of-rise late in the run is the leak alone.")],
        [OHANLON, CODATA, ILLUS,
         {"title": "Pump speeds (rotary 10 m³/h, turbomolecular 200 L/s, diffusion 400 L/s) are illustrative nameplate values", "note": "unsourced / illustrative"}],
        {"reading": "C", "textbook": "ph2_C", "tol": 0.01}, VAC, CH_TV, "Ph.D.", "Vacuum technology")


def vdp_sheet() -> dict:
    return _mk(
        "ph2-vdp-sheet", "ph2-semi-bench", "Van der Pauw: sheet resistance and resistivity of a silicon wafer",
        "Make four contacts at the edge of a flat sample of any shape, measure the two resistances R_AB,CD and R_BC,DA with "
        "current reversal and solve the van der Pauw equation numerically for the sheet resistance and resistivity.",
        "ph2_sheet", {"mode": 0.0, "sel": 0.0, "Rs": 95.0, "t": 5.25e-4, "r": 1.18, "I": 1.0e-3, "Voff": 3.5e-6},
        [knob("I", "Source current", "I", 0.1, 5, 0.1, 1.0, "mA", 1e-3),
         knob("Rs", "This sample (its sheet resistance is hidden)", "Rs", 0.5, 2000, 0.01, 95, "Ω/□", hidden=True)],
        [inst("R", "readout", "Resistance (V forward − V reverse) / 2I", "R", unit="Ω", digits=4)],
        ["Place the sample on the probe stage and lower four needles on its edge, labelled A, B, C, D in order.",
         "Pass the current in at A and out at B; read the voltage across D and C, forward and reversed. R_AB,CD = (V − V_rev) / 2I.",
         "Repeat for the other pair: current in B, out C, voltage across A and D: R_BC,DA.",
         "Solve exp(−πR_AB,CD/Rs) + exp(−πR_BC,DA/Rs) = 1 numerically for Rs.",
         "Multiply Rs by the thickness to get the resistivity."],
        "For a flat sample of uniform thickness t and any shape, with four small contacts on its edge, van der Pauw "
        "showed that exp(−πR_AB,CD/Rs) + exp(−πR_BC,DA/Rs) = 1, where Rs = ρ/t is the sheet resistance. When the two "
        "resistances are equal, Rs = π R / ln 2 = 4.532 R. Otherwise the equation is solved numerically. Reversing the "
        "current and halving the difference cancels the thermoelectric voltage at the contacts. The wafer is 525 µm thick "
        "(the standard 100 mm silicon wafer); its resistivity is chosen for the lab (illustrative).",
        "Probe needles are sharp and the sample is brittle: lower them with the micrometer, never by hand. Keep the source current in the milliampere range so the sample does not heat.",
        [{"say": "A probe station: the wafer on the stage, four needles on its edge and a source-measure unit."},
         {"set": {"I": 2.0}, "say": "At 2 mA the voltage across the second pair is a few hundred millivolts."}],
        [_q("Reversing the current cancels", ["The thermoelectric offset at the contacts", "The sample's resistance", "The thickness"], 0,
            "(V − V_rev)/2 keeps only the part that flips with the current."),
         _q("When R_AB,CD = R_BC,DA, the sheet resistance is", ["π R / ln 2", "R / π", "2 R"], 0, "exp(−πR/Rs) = 1/2.")],
        [VDP, SCHRODER, ILLUS,
         {"title": "Wafer thickness 525 µm: standard 100 mm silicon wafer (SEMI M1; unsourced here, entered from memory)", "note": "resistivity is illustrative"}],
        {"reading": "Rs", "textbook": "ph2_Rs", "tol": 0.01}, SEMI, CH_SS, "M.Sc.", "Electrical characterisation")


def fpp_film() -> dict:
    return _mk(
        "ph2-fpp-film", "ph2-semi-bench", "Four-point probe: sheet resistance and resistivity of a thin film",
        "Press a collinear four-point probe on a film, pass several currents through the outer pins, read the voltage on the "
        "inner pins and find the sheet resistance from the slope.",
        "ph2_sheet", {"mode": 1.0, "sel": 0.0, "Rs": 3.0, "t": 5.0e-8, "r": 1.0, "I": 1.0e-3, "Voff": 3.5e-6},
        [knob("I", "Source current", "I", 0.5, 5, 0.1, 1.0, "mA", 1e-3),
         knob("Rs", "This film (its sheet resistance is hidden)", "Rs", 0.1, 500, 0.001, 3.0, "Ω/□", hidden=True)],
        [inst("R", "readout", "Resistance (V forward − V reverse) / 2I", "R", unit="Ω", digits=5)],
        ["Place the film on the stage and lower the four-point head so all four pins touch.",
         "Pass currents of 1 to 5 mA through the outer pins and read the inner-pin voltage with the current forward and reversed.",
         "Plot V against I: the slope is the resistance of the probe arrangement.",
         "Multiply the slope by π / ln 2 = 4.532 for the sheet resistance of a film much larger than the pin spacing.",
         "Multiply by the film thickness (measured by stylus) for the resistivity."],
        "Four collinear pins at equal spacing on a thin film that extends far beyond them give V/I = (ln 2 / π) Rs, so "
        "Rs = (π/ln 2)(V/I) = 4.532 V/I. Separate current and voltage pins remove the contact and lead resistance. "
        "Several currents give a slope, which averages out the voltmeter offset; reversing the current removes the "
        "thermoelectric voltage. For a small or thick sample, correction factors apply; here the film is large and thin. "
        "The film resistivity is a lab value, higher than bulk as thin films are (illustrative).",
        "The pins are sharp and press on a thin film: lower them with the screw. Keep the current low so the film does not heat.",
        [{"say": "A source-measure unit and a four-point head lowered on a thin film."},
         {"set": {"I": 4.0}, "say": "At 4 mA the inner-pin voltage is a few millivolts."}],
        [_q("Separate current and voltage pins are used because", ["The voltage pins carry almost no current, so contact resistance drops out", "They are cheaper", "They cool the film"], 0,
            "A voltmeter draws almost no current through its contacts."),
         _q("The factor π/ln 2 is", ["4.532", "0.221", "2.718"], 0, "π / 0.6931 = 4.532.")],
        [SCHRODER, ILLUS,
         {"title": "Thin-film resistivities and thicknesses are lab values (unsourced / illustrative)", "note": "chosen for the lab, not looked up"}],
        {"reading": "Rs", "textbook": "ph2_Rs", "tol": 0.01}, SEMI, CH_SS, "M.Sc.", "Electrical characterisation")


def haynes_shockley() -> dict:
    return _mk(
        "ph2-haynes-shockley", "ph2-semi-bench", "Haynes-Shockley experiment: drift mobility in n-type germanium",
        "Inject a pulse of holes into an n-type germanium bar, watch it drift to the collector on an oscilloscope at several "
        "fields and find the hole drift mobility, the diffusion coefficient and the lifetime.",
        "ph2_hs", {"t": 0.0, "L": 0.01, "E": 2000.0, "mu": 0.19, "T": 300.0, "tau": 1.0e-4, "N": 1.0e-3, "gain": 50.0},
        [knob("E", "Field along the bar", "E", 500, 3500, 10, 2000, "V/m"),
         knob("mu", "This bar (its hole mobility is hidden)", "mu", 0.01, 0.6, 0.0001, 0.19, "m²/V s", hidden=True)],
        [inst("td", "readout", "Expected transit time", "td", unit="s", digits=6)],
        ["Connect the pulse generator to the emitter, the drive supply along the bar and the collector to the oscilloscope.",
         "Set a field E along the bar; inject a pulse and read the collector signal against time.",
         "From the peak time t_d, find the drift velocity v = L / t_d. Repeat for five fields.",
         "Plot v against E: the slope through the origin is the drift mobility μ.",
         "From the width of the pulse find D = σ_t² v² / (2 t_d), and check D = μkT/q; from the area decay find τ."],
        "Holes injected into n-type germanium at an emitter drift with velocity v = μE, spread by diffusion and "
        "recombine with lifetime τ. The density at a collector a distance L away is n(t) = N e^(−t/τ) / √(4πDt) · "
        "exp[−(L − μEt)²/4Dt]. The peak arrives at t_d ≈ L/(μE); its width is σ_t = √(2D t_d)/v; the area falls as "
        "exp(−t_d/τ). The Einstein relation D = μkT/q ties diffusion to drift. The hole mobility of germanium at 300 K "
        "is about 0.19 m²/V s (1900 cm²/V s); the lifetime here is a lab value (illustrative) since it depends on purity "
        "and surface treatment.",
        "The drive supply gives up to a few hundred volts along the bar and the pulse generator is fast: keep leads away from your hands and switch off before changing connections.",
        [{"say": "A germanium bar with an emitter and a collector point contact, a pulse generator and an oscilloscope."},
         {"set": {"E": 3000}, "say": "At a high field the pulse reaches the collector sooner and is narrower."}],
        [_q("A higher field makes the pulse", ["Arrive sooner", "Arrive later", "Arrive at the same time"], 0, "v = μE."),
         _q("The Einstein relation is", ["D = μkT/q", "D = μ/kT", "D = qT/μk"], 0, "Diffusion and drift share the same scattering.")],
        [HS, SZE, ILLUS,
         {"title": "Germanium hole mobility 0.19 m²/V s (1900 cm²/V s at 300 K); lifetime illustrative", "note": "unsourced here: handbook value entered from memory, not re-checked in this build"}],
        {"reading": "mu", "textbook": "ph2_mu", "tol": 0.01}, SEMI, CH_SS, "M.Sc.", "Carrier transport")


def solar_cell() -> dict:
    return _mk(
        "ph2-solar-cell", "ph2-semi-bench", "Solar cell I-V under a solar simulator: silicon cell",
        "Sweep the voltage across an illuminated solar cell at several intensities, read Voc and Isc, find the maximum power "
        "point and compute the fill factor and the efficiency.",
        "ph2_solar", {"V": 0.0, "G": 1000.0, "A": 4.0e-4, "Jsc1": 400.0, "n": 1.2, "J0": 1.0e-7, "rs": 5.0e-5, "rsh": 0.1, "T": 300.0},
        [knob("V", "Cell voltage", "V", 0, 0.9, 0.005, 0.0, "V"),
         knob("G", "Light intensity", "G", 100, 1000, 10, 1000, "W/m²"),
         knob("J0", "This cell (its dark current is hidden)", "J0", 1e-9, 1e-5, 1e-9, 1e-7, "A/m²", hidden=True)],
        [inst("I", "readout", "Cell current", "I", unit="A", digits=4),
         inst("gr", "graph", "Current against voltage", "I", x="p.V", xlabel="V (V)", dots=True)],
        ["Mount the cell under the lamp and set the intensity with the reference cell (1000 W/m² is one sun).",
         "Sweep the voltage from 0 to open circuit and record the current at each step.",
         "Read Isc at V = 0 and Voc where the current is zero.",
         "Find the point of maximum power P = V × I; fill factor FF = Pmax/(Voc Isc), efficiency = Pmax/(G A).",
         "Repeat at 200, 500 and 1000 W/m²: Isc grows in proportion and Voc grows with ln G."],
        "An illuminated cell is a diode in parallel with a current source: I = Iph − I0[exp((V + I Rs)/nVt) − 1] − "
        "(V + I Rs)/Rsh, with Iph proportional to the light intensity. At open circuit, ignoring Rsh, Voc = nVt ln(Iph/I0 + 1), "
        "so Voc rises by about nVt ln 10 per decade of intensity. The fill factor measures how square the curve is, and the "
        "efficiency is the maximum power over the light power on the cell. The cell parameters (n, I0, series and shunt "
        "resistance) are typical lab values, not a particular commercial cell (unsourced / illustrative).",
        "The simulator lamp is intense and warm: never look into it and let the cell cool between runs. Do not touch the cell contacts while the lamp is on.",
        [{"say": "A solar cell under a lamp on a rail, a source-measure unit and a reference cell."},
         {"set": {"V": 0.55}, "say": "Near 0.55 V the cell delivers its maximum power."}],
        [_q("Open-circuit voltage rises with light because", ["Iph/I0 rises and Voc ∝ ln(Iph/I0)", "Isc falls", "Rs rises"], 0, "Voc = nVt ln(Iph/I0 + 1)."),
         _q("The fill factor is", ["Pmax / (Voc Isc)", "Voc / Isc", "Isc / Pmax"], 0, "It compares the real maximum power with the rectangle.")],
        [SZE, CODATA, ILLUS,
         {"title": "Cell parameters (n = 1.2, Jsc = 40 mA/cm² at one sun, J0, Rs, Rsh) are typical lab values (unsourced / illustrative)", "note": "not a particular commercial cell"}],
        {"reading": "Voc", "textbook": "ph2_Voc", "tol": 0.01}, SEMI, CH_OD, "M.Sc.", "Photovoltaics")


BUILDERS = (xrd_refine, xrr_film, qcm_evap, vac_research, vdp_sheet, fpp_film, haynes_shockley, solar_cell)
