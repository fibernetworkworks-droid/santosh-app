"""Lab pack `phd_cond`: research-level benches for low temperature and superconductivity, quantum transport and
magnetic resonance (see `labs/__init__.py`). Physics: `packs/phd_cond.py` (+ JS twin). Rigs: `phd-cryostat-insert`,
`phd-transport-bench`, `phd-resonance-bench`.

Honesty, said in every lab that needs it: a SQUID, a Josephson junction, a quantum Hall sample, a tunnel junction and
a Moessbauer spectrometer are NOT things a student can touch. They are SIMULATED INSTRUMENTS built on a published
model (named in the lab's sources). Material numbers marked "unsourced / illustrative" are not looked up.
"""
from __future__ import annotations

from ..catalog import B, SIM, board, inst, knob, lab

GRP = "Physics · Condensed Matter Research"
CH_LT = "Low temperature and superconductivity"
CH_QT = "Quantum transport"
CH_MR = "Magnetic resonance and hyperfine methods"
CH_PG = "Magnetic resonance"

CODATA = {"title": "SI 2019 defining constants (h, e, k) and CODATA 2018 (muB, muN, m_e, proton gamma)"}
TINKHAM = {"title": "M. Tinkham, Introduction to Superconductivity, 2nd ed. (McGraw-Hill, 1996)"}
POBELL = {"title": "F. Pobell, Matter and Methods at Low Temperatures, 3rd ed. (Springer, 2007)"}
CLARKE = {"title": "J. Clarke and A. I. Braginski (eds.), The SQUID Handbook, vol. I (Wiley-VCH, 2004)"}
IHN = {"title": "T. Ihn, Semiconductor Nanostructures (Oxford University Press, 2010)"}
SLICHTER = {"title": "C. P. Slichter, Principles of Magnetic Resonance, 3rd ed. (Springer, 1990)"}
ILLUS = {"title": "Unsourced / illustrative sample constants",
         "note": "the material numbers of this sample are chosen for the lab, not looked up in a table"}
SIMI = {"title": "SIMULATED INSTRUMENT",
        "note": "this apparatus cannot be handled in a student lab; its numbers come from the published model above"}


def _bench() -> list[dict]:
    return [board(1.0, 0.6),
            B("ctl", "box", name="Control unit", info="Sets and reads the control variable of the run.",
              size=[0.2, 0.07, 0.13], pos=[0.3, 0.035, 0.12], color="#2b2f36"),
            B("rd", "box", name="Readout unit", info="Reads the response of the sample.",
              size=[0.2, 0.07, 0.13], pos=[0.3, 0.035, -0.1], color="#2b2f36")]


def _q(q, opts, ans, why):
    return {"q": q, "options": opts, "answer": ans, "why": why}


def _mk(id, rig, title, aim, kernel, params, knobs, steps, theory, safety, questions, sources, check, chapter,
        cfg=None, topic="Research laboratory", insts=None, tour=None):
    d = dict(id=id, rig=rig, title=title, group=GRP, level="Ph.D.", topic=topic, chapter=chapter, aim=aim,
             kernel=kernel, params=params, autorun=True, camera={"pos": [0.0, 0.7, 0.9], "look": [0, 0.04, -0.05]},
             floor=-0.03, bodies=_bench(), knobs=knobs, instruments=insts or [], steps=steps, theory=theory,
             safety=safety, tour=tour or [], questions=questions, sources=sources + [SIM], check=check)
    if cfg:
        d["cfg"] = cfg
    return lab(**d)


CRYO_SAFE = ("Cryogens (liquid nitrogen at 77 K, liquid helium at 4.2 K) cause cold burns and can displace the air in a "
             "closed room. Only trained staff transfer them, wearing a face shield and cryogenic gloves, in a ventilated "
             "room. Never seal a vessel that holds a cryogen. In this simulation nothing is poured.")
MAG_SAFE = ("A strong magnet attracts steel tools and can disturb pacemakers and other implants: anyone with an implant "
            "stays outside the marked area. Keep watches, cards and phones away. In this simulation no magnet is live.")


def sc_tc() -> dict:
    return _mk(
        "phd-sc-tc", "phd-cryostat-insert", "Superconductor Tc by four-probe resistance against temperature",
        "Warm a superconducting bar in a cryostat insert, measure its resistance by the four-probe method, find Tc at the "
        "midpoint of the transition and the residual resistance ratio, and see the transition move in a magnetic field.",
        "phd_scrt", {"T": 100.0, "B": 0.0, "Tc0": 92.0, "Bc2": 40.0, "w": 0.6, "Rres": 0.02, "a": 0.0004, "I": 0.001},
        [knob("T", "Sample temperature", "T", 70, 130, 0.1, 100, "K"),
         knob("Tc0", "This sample (its Tc is hidden)", "Tc0", 40, 125, 0.1, 92, "K", hidden=True)],
        ["Mount the bar on the insert with four spring contacts and a diode thermometer beside it, and lower the insert into the cryostat.",
         "Pass a steady 1 mA through the outer leads and read the voltage on the inner pair.",
         "Read the resistance at several temperatures above the transition: it is a straight line.",
         "Step through the fall to zero in small steps and record R at each.",
         "Divide R by the straight-line normal-state value; Tc is where the ratio is one half.",
         "Repeat at 10 T: the transition moves down."],
        "Below its critical temperature Tc a superconductor has no electrical resistance. Above it the sample is a poor "
        "metal, R = R0 + aT. The fall takes place over a fraction of a kelvin to a few kelvin, so Tc is quoted where R has "
        "dropped to half of the straight-line normal-state value extrapolated to that temperature. A magnetic field lowers "
        "Tc along the phase boundary, here the parabola Tc(B) = Tc0[1 - (B/Bc2)^2]. The ratio R(300 K)/R(0 K, extrapolated) "
        "is the residual resistance ratio and measures how clean the metal is. The sample is illustrative.",
        CRYO_SAFE,
        [_q("Tc is quoted at the", ["Midpoint of the transition", "Highest temperature of the run", "Start of the cooling"], 0,
            "R has fallen to half its normal-state value."),
         _q("A magnetic field applied to the bar makes Tc", ["Lower", "Higher", "Unchanged"], 0,
            "The field destroys superconductivity, so it only survives at lower temperature.")],
        [TINKHAM, ILLUS, {"title": "Tc(B) = Tc0[1 - (B/Bc2)^2]: the usual parabolic phase boundary (empirical)"}],
        {"reading": "Tc", "textbook": "phd_Tc", "tol": 0.01}, CH_LT)


def sc_ic() -> dict:
    return _mk(
        "phd-sc-ic", "phd-cryostat-insert", "Critical current and Jc of a superconducting bridge (1 uV/cm criterion)",
        "Pass increasing current through a superconducting bridge, record the voltage and find the critical current Ic "
        "where the electric field reaches 1 uV/cm; repeat at another temperature and field and compare Jc.",
        "phd_scic", {"I": 0.5, "T": 20.0, "B": 0.0, "Tc": 92.0, "Ic0": 2.0, "B0": 1.0, "n": 15.0, "Lv": 0.002,
                     "Ec": 1e-4, "area": 1.0e-9},
        [knob("I", "Transport current", "I", 0, 3, 0.005, 0.5, "A"),
         knob("Ic0", "This bridge (its Ic0 is hidden)", "Ic0", 0.2, 6, 0.01, 2, "A", hidden=True)],
        ["Mount the bridge on the insert and fix the current and voltage leads.",
         "Set the temperature and field. Raise the current in steps and read the voltage with the nanovoltmeter.",
         "The voltage stays near zero and then climbs steeply, as a power of the current.",
         "Find the current where the field E = V/L reaches 1 uV/cm: that is Ic.",
         "Divide Ic by the cross-section for Jc. Change the temperature or field and repeat."],
        "A superconductor carries current without loss only up to a critical current. Near Ic the voltage rises as "
        "V = Vc (I/Ic)^n with a large exponent n, so Ic is defined by a voltage criterion, here E = 1 uV/cm, i.e. "
        "Vc = Ec L. The current density Jc = Ic/A is the quantity to compare between samples. Ic falls as the "
        "temperature rises (here with the Ginzburg-Landau-like law (1 - t^2)^1.5) and as the field rises (the Kim "
        "model 1/(1 + B/B0)). The sample and these two laws are illustrative, chosen for the lab.",
        CRYO_SAFE + " Large currents heat the leads: stay within the supply's limit.",
        [_q("Ic is defined by", ["A voltage (electric-field) criterion", "The current at which the sample melts", "Zero voltage exactly"], 0,
            "Near Ic the voltage rises smoothly, so a criterion such as 1 uV/cm is used."),
         _q("Raising the temperature makes Ic", ["Smaller", "Larger", "Unchanged"], 0, "The superconducting state weakens towards Tc.")],
        [TINKHAM, ILLUS, {"title": "E = Ec (J/Jc)^n with Ec = 1 uV/cm; Kim, Hempstead and Strnad, Phys. Rev. 129, 528 (1963) for the field law"}],
        {"reading": "Ic", "textbook": "phd_Ic", "tol": 0.01}, CH_LT)


def acsusc() -> dict:
    return _mk(
        "phd-meissner-acsusc", "phd-cryostat-insert", "Meissner effect by mutual-inductance AC susceptibility",
        "Place a small superconducting sphere between a drive coil and a pick-up coil, record the in-phase and "
        "out-of-phase susceptibility against temperature and find Tc and the London penetration depth.",
        "phd_acsusc", {"T": 50.0, "Tc": 92.0, "w": 0.5, "a": 1.0e-6, "ns": 2.0e28, "chi2": 0.12},
        [knob("T", "Sample temperature", "T", 4, 110, 0.1, 50, "K"),
         knob("a", "Sphere radius", "a", 0.2, 20, 0.01, 1, "µm", k=1e-6)],
        ["Mount the sphere between the coils on the insert and lower the insert into the cryostat.",
         "Read the in-phase signal chi' and the out-of-phase signal chi'' at about 5 K.",
         "Warm in steps; record chi' and chi'' at each step, with small steps near the transition.",
         "Tc is where chi'' (the loss) peaks.",
         "At low temperature chi' is -1 only for a perfect shield; the shortfall gives the penetration depth."],
        "A superconductor expels the field (the Meissner effect) from all but a thin surface layer of depth "
        "lambda, so the sample shields a volume fraction f = 1 - (1 - lambda/a)^3 of a sphere of radius a and the "
        "in-phase susceptibility is chi' = -f. The London depth is lambda_L = sqrt(m/(mu0 ns e^2)), growing as the "
        "temperature rises (here lambda0/sqrt(1 - t^4)). Near Tc the sample dissipates the drive and chi'' shows a peak "
        "at Tc. The sphere size and superfluid density are illustrative values.",
        CRYO_SAFE,
        [_q("The loss signal chi'' peaks", ["At Tc", "At the lowest temperature", "At room temperature"], 0,
            "The sample is changing between shielding and not shielding there."),
         _q("A finite penetration depth makes the shielding", ["Slightly less than perfect", "Greater than perfect", "Zero"], 0,
            "A thin surface layer is not shielded.")],
        [TINKHAM, {"title": "F. London and H. London (1935); lambda_L = sqrt(m/(mu0 ns e^2)); Gorter-Casimir t^4 temperature law"}, ILLUS],
        {"reading": "lam0", "textbook": "phd_lam0", "tol": 0.01}, CH_LT)


def thermo() -> dict:
    return _mk(
        "phd-cryo-thermometry", "phd-cryostat-insert", "Cryogenic thermometry: a silicon diode calibrated in the cryostat",
        "Calibrate a thermometer against the cryostat set-point, find its sensitivity dX/dT at the working temperature "
        "and see the error caused by its own excitation (self-heating).",
        "phd_therm", {"T": 77.0, "sensor": 1.0, "I": 1.0e-5, "G": 1.0e-3},
        [knob("T", "Cryostat temperature", "T", 60, 300, 0.1, 77, "K"),
         knob("G", "Thermal link of the sensor", "G", 1e-4, 1e-2, 1e-5, 1e-3, "W/K")],
        ["Mount the sensor on the insert next to the reference thermometer and lower the insert into the cryostat.",
         "Set the controller to the working temperature and read the sensor.",
         "Read the sensor again at 1 K above and 1 K below: the slope is the sensitivity.",
         "Read at several other temperatures to see how the curve bends.",
         "Raise the excitation by 10x and 100x: the reading shifts because the sensor warms itself."],
        "A thermometer is a sensor whose reading X(T) is calibrated against a reference. Its sensitivity dX/dT tells how "
        "well it resolves a temperature change. A silicon diode at constant current gives V = Eg/e + (kT/e)[ln(I/Is0) - "
        "3 ln T], nearly linear above about 50 K with a slope of about -2 mV/K; this ideal-diode model fails below about "
        "30 K. A platinum RTD follows the IEC 60751 Callendar-Van Dusen law, a RuO2 resistor ln R ~ sqrt(T0/T) (variable-range "
        "hopping) and a thermocouple a Seebeck law. Every excitation heats the sensor by P/G above the bath (self-heating).",
        CRYO_SAFE,
        [_q("A sensor with a larger |dX/dT| at the working temperature", ["Resolves smaller temperature changes", "Is less accurate", "Needs more current"], 0,
            "The same noise in X corresponds to a smaller temperature error."),
         _q("Self-heating makes the sensor read", ["A temperature above the bath", "Below the bath", "Exactly the bath"], 0,
            "The excitation power P is dissipated in the sensor and must flow out through its thermal link G.")],
        [{"title": "Silicon diode: the ideal-diode equation with Is ~ T^3 exp(-Eg/kT) (S. M. Sze); Eg = 1.17 eV extrapolated to 0 K"},
         {"title": "Pt100: IEC 60751 Callendar-Van Dusen coefficients A = 3.9083e-3, B = -5.775e-7, C = -4.183e-12"}, POBELL],
        {"reading": "S", "textbook": "phd_thermS", "tol": 0.01}, CH_LT)


def josephson() -> dict:
    return _mk(
        "phd-josephson", "phd-transport-bench", "Josephson junction I-V and Shapiro steps (simulated instrument)",
        "SIMULATED INSTRUMENT. Sweep the bias current through a shunted Nb-type junction, find Ic, then switch on "
        "microwaves and read the voltage of the first Shapiro step to get 2e/h.",
        "phd_jj", {"I": 0.0, "Delta": 1.4e-3, "Tb": 4.2, "Rn": 2.0, "Rs": 0.04, "f": 16.0e9, "Irf": 4.2e-4, "rf": 0.0},
        [knob("f", "Microwave frequency", "f", 4, 40, 0.1, 16, "GHz", k=1e9),
         knob("Rs", "Shunt resistance (hidden)", "Rs", 0.01, 0.2, 0.001, 0.04, "Ω", hidden=True)],
        ["Read the title card: a Josephson junction at 4.2 K cannot be handled in a teaching lab, so this is a simulation.",
         "Sweep the bias current with the microwaves off: the voltage stays at zero up to Ic and then rises.",
         "Switch the microwaves on at the set frequency and sweep again.",
         "Find the flat steps in the I-V curve: their voltage is V = n h f/(2e).",
         "From the first step and the known frequency, find the Josephson constant 2e/h."],
        "SIMULATED INSTRUMENT. The junction obeys the resistively shunted junction (RSJ) model: the supercurrent Ic sin(phi) "
        "flows in parallel with a shunt Rs, dphi/dt = (2e/hbar) V. Below Ic the voltage is zero. Above it the mean voltage is "
        "Rs sqrt(I^2 - Ic^2). Ic of the tunnel junction follows Ambegaokar and Baratoff, Ic Rn = (pi Delta/2e) tanh(Delta/2kT). "
        "With microwaves of frequency f the phase locks to the drive and the voltage sits on flat Shapiro steps at "
        "V = n h f/(2e), so 2e/h = f/V = 483.5978 MHz per microvolt. The numbers come from integrating the RSJ equation; "
        "the gap and shunt are illustrative.",
        "No cryogen or microwave source exists here. Real microwave work needs shielded cables and a limited output power.",
        [_q("On a Shapiro step the voltage depends only on", ["The frequency and constants h and e", "The bias current", "The junction area"], 0,
            "V = n h f / 2e, which is why it is a voltage standard."),
         _q("The voltage at Ic is", ["Zero until Ic, then non-zero", "Proportional to I always", "Constant"], 0, "Below Ic the current flows as a supercurrent.")],
        [CLARKE, {"title": "RSJ model: W. C. Stewart (1968) and D. E. McCumber (1968); Ambegaokar and Baratoff, Phys. Rev. Lett. 10, 486 (1963); Shapiro, Phys. Rev. Lett. 11, 80 (1963)"},
         CODATA, SIMI, ILLUS],
        {"reading": "f", "textbook": "phd_fJ", "tol": 0.01}, CH_LT, topic="Simulated research instrument")


def dcsquid() -> dict:
    return _mk(
        "phd-dc-squid", "phd-transport-bench", "DC SQUID voltage-flux characteristic (simulated instrument)",
        "SIMULATED INSTRUMENT. Bias a DC SQUID above its critical current, ramp the flux coil current and read the "
        "periodic voltage; the period is one flux quantum.",
        "phd_dcsquid", {"Icoil": 0.0, "I0": 10.0e-6, "Rn": 4.0, "Ib": 24.0e-6, "Mi": 2.0e-10, "Poff": 0.1, "vn": 2.0e-7, "seed": 3.0},
        [knob("Ib", "Bias current", "Ib", 20, 40, 0.1, 24, "µA", k=1e-6),
         knob("Mi", "Coil mutual inductance (hidden)", "Mi", 5e-11, 6e-10, 1e-12, 2e-10, "Wb/A", hidden=True)],
        ["Read the title card: a SQUID works at 4.2 K inside shields and cannot be handled in a teaching lab, so this is a simulation.",
         "Set the bias current above 2 I0.",
         "Sweep the flux coil current over several periods and capture the voltage trace.",
         "Find where the trace crosses its mean level; the spacing is the period in coil current.",
         "The period times the mutual inductance Mi is the flux quantum."],
        "SIMULATED INSTRUMENT. A DC SQUID is a superconducting loop with two Josephson junctions. Its critical current "
        "depends on the flux through the loop, Ic = 2 I0 |cos(pi Phi/Phi0)|, with period Phi0 = h/2e = 2.0678e-15 Wb. "
        "Biased above its critical current, the SQUID voltage is V = (Rn/2) sqrt(Ib^2 - Ic^2), so V repeats every Phi0. "
        "The steepest slope dV/dPhi is the transfer function; dividing the voltage noise by it gives the flux noise. "
        "This is the zero-inductance, overdamped model; the noise is a seeded pseudo-random number, not a measurement.",
        "No cryogen or magnet exists here. A real SQUID is damaged by static discharge and by magnetic-field jumps.",
        [_q("The voltage of a SQUID repeats when the flux changes by", ["h/2e", "h/e^2", "The Bohr magneton"], 0, "One flux quantum Phi0 = h/2e."),
         _q("The best working point of a SQUID is where", ["dV/dPhi is largest", "V is largest", "V is zero"], 0, "A small flux change then gives the largest voltage change.")],
        [CLARKE, {"title": "Clarke and Braginski, The SQUID Handbook vol. I, chapter 2 (the symmetric DC SQUID, beta_L << 1)"}, CODATA, SIMI, ILLUS],
        {"reading": "Phi0", "textbook": "phd_Phi0", "tol": 0.01}, CH_LT, topic="Simulated research instrument")


def qhe() -> dict:
    return _mk(
        "phd-quantum-hall", "phd-transport-bench", "Integer quantum Hall effect (simulated instrument)",
        "SIMULATED INSTRUMENT. Sweep the magnetic field through a two-dimensional electron gas at low temperature, find "
        "the Hall plateaus and show they sit at h/(i e^2).",
        "phd_qhe", {"B": 6.0, "n": 2.5e15, "T": 1.5, "w0": 0.05, "wT": 0.04, "rho0": 5.0, "rhop": 0.4},
        [knob("B", "Magnetic field", "B", 1, 12, 0.01, 6, "T"),
         knob("T", "Sample temperature", "T", 0.1, 4.2, 0.1, 1.5, "K")],
        ["Read the title card: a quantum Hall sample needs a 12 T superconducting magnet and a cryostat, so this is a simulation.",
         "Choose the temperature, then sweep the field from 1 T to 12 T.",
         "Capture the Hall resistance and the longitudinal resistance together.",
         "The Hall resistance has flat steps and the longitudinal resistance nearly vanishes on each.",
         "Number the plateaus from the highest field (i = 1) and multiply each by i to get h/e^2."],
        "SIMULATED INSTRUMENT. In a two-dimensional electron gas of density n the Landau levels are filled to a filling "
        "factor nu = n h/(eB). When an integer number i of levels are full the Hall resistance sits on a plateau "
        "R_xy = h/(i e^2) = 25812.807/i ohm, independent of the sample, while the longitudinal resistance R_xx falls "
        "towards zero. Lower temperature narrows the transitions. Here the plateau VALUES are the exact quantum values, "
        "but their shapes use an illustrative tanh broadening; no real sample was measured. The density is hidden.",
        MAG_SAFE + " High-field magnets quench if misused; only trained staff run them.",
        [_q("On the plateau i = 2 the Hall resistance is", ["h/(2e^2)", "2h/e^2", "h/e^2 exactly"], 0, "R_xy = h/(i e^2)."),
         _q("On a plateau the longitudinal resistance", ["Almost vanishes", "Is largest", "Equals R_xy"], 0, "No dissipation: the current flows in edge states.")],
        [IHN, {"title": "K. von Klitzing, G. Dorda and M. Pepper, Phys. Rev. Lett. 45, 494 (1980); R_K = h/e^2 = 25812.80745 ohm (exact in SI 2019)"}, CODATA, SIMI, ILLUS],
        {"reading": "RK", "textbook": "phd_RK", "tol": 0.01}, CH_QT, topic="Simulated research instrument")


def sdh() -> dict:
    return _mk(
        "phd-sdh", "phd-transport-bench", "Shubnikov-de Haas oscillations of a two-dimensional electron gas",
        "SIMULATED INSTRUMENT. Sweep the field, plot the longitudinal resistance against 1/B and find the carrier density "
        "from the period of the oscillations.",
        "phd_sdh", {"B": 5.0, "n": 3.0e15, "T": 1.5, "mstar": 0.067, "muq": 3.0, "rho0": 50.0},
        [knob("B", "Magnetic field", "B", 0.8, 12, 0.01, 5, "T"),
         knob("T", "Sample temperature", "T", 0.1, 8, 0.1, 1.5, "K")],
        ["Read the title card: the sample sits in a 12 T magnet at 1.5 K, so this is a simulation.",
         "Sweep the field from 0.8 T to 12 T and capture R_xx.",
         "The trace is periodic when plotted against 1/B.",
         "Measure the spacing of the maxima in 1/B.",
         "The density is n = 2e/(h x spacing) for a spin-degenerate gas."],
        "SIMULATED INSTRUMENT. In a magnetic field the resistance of a 2D electron gas oscillates because Landau levels "
        "cross the Fermi level. The oscillations are periodic in 1/B with period Delta(1/B) = 2e/(h n) (spin degenerate). "
        "Lifshitz and Kosevich give the amplitude factor X/sinh X with X = 2 pi^2 kT m*/(hbar e B) and a Dingle factor "
        "exp(-pi/(mu_q B)) which cut the oscillations at high temperature and low field. This lab finds the density from "
        "the period only; it does not extract the effective mass or quantum lifetime.",
        MAG_SAFE,
        [_q("Shubnikov-de Haas oscillations are periodic in", ["1/B", "B", "B^2"], 0, "Each Landau level crosses the Fermi level at a fixed value of 1/B."),
         _q("Raising the temperature makes the oscillations", ["Smaller", "Larger", "Unchanged"], 0, "The Fermi edge smears; the X/sinh X factor falls.")],
        [IHN, {"title": "Lifshitz-Kosevich theory; Shoenberg, Magnetic Oscillations in Metals (Cambridge, 1984)"}, CODATA, SIMI, ILLUS],
        {"reading": "n", "textbook": "phd_sdhn", "tol": 0.01}, CH_QT, topic="Simulated research instrument")


def weakloc() -> dict:
    return _mk(
        "phd-weak-localisation", "phd-transport-bench", "Weak localisation magnetoconductance and the phase coherence length",
        "SIMULATED INSTRUMENT. Measure the small positive magnetoconductance of a thin metal film at low temperature, fit "
        "the Hikami-Larkin-Nagaoka form and find the phase coherence length.",
        "phd_weakloc", {"B": 0.01, "T": 2.0, "L1": 1.0e-6, "pexp": 1.0, "noise": 0.002, "seed": 5.0},
        [knob("B", "Magnetic field", "B", 0.0001, 0.1, 0.0001, 0.01, "T"),
         knob("L1", "This film (its coherence length at 1 K is hidden)", "L1", 2e-7, 5e-6, 1e-8, 1e-6, "m", hidden=True)],
        ["Read the title card: this needs a millikelvin cryostat and a lock-in bridge, so it is a simulation.",
         "Choose the temperature and sweep the field from 0.1 mT to 100 mT.",
         "Capture the change of conductance relative to zero field.",
         "The fit adjusts the dephasing field B_phi until the curve matches.",
         "The phase coherence length is L_phi = sqrt(hbar/(4 e B_phi)). Repeat at another temperature."],
        "SIMULATED INSTRUMENT. Electrons in a disordered thin film interfere with their own time-reversed paths and "
        "localise. A small field breaks the interference, so the conductance rises. The Hikami-Larkin-Nagaoka form for "
        "a 2D film is delta sigma(B) = (e^2/(pi h))[psi(1/2 + B_phi/B) - ln(B_phi/B)], with the dephasing field "
        "B_phi = hbar/(4 e L_phi^2). L_phi shrinks as the film warms (here as T^(-1/2)). The curve is generated from this "
        "formula with 0.2 % seeded noise; spin-orbit and spin-flip terms are left out.",
        "No cryogen or high-frequency source exists here.",
        [_q("A small magnetic field makes the conductance of a weakly localised film", ["Rise", "Fall", "Stay the same"], 0, "It breaks the constructive interference that localises the electrons."),
         _q("The phase coherence length gets shorter when the film is", ["Warmer", "Colder", "Thicker"], 0, "More inelastic scattering destroys the phase sooner.")],
        [IHN, {"title": "S. Hikami, A. I. Larkin and Y. Nagaoka, Prog. Theor. Phys. 63, 707 (1980)"}, CODATA, SIMI, ILLUS],
        {"reading": "Lphi", "textbook": "phd_Lphi", "tol": 0.01}, CH_QT, topic="Simulated research instrument")


def tunnel() -> dict:
    return _mk(
        "phd-tunnel-nis", "phd-transport-bench", "Giaever tunnelling spectroscopy of a superconductor (simulated)",
        "SIMULATED INSTRUMENT. Record the I-V curve of a normal-metal / insulator / superconductor tunnel junction, fit the "
        "BCS density of states to find the gap and follow the gap as the temperature rises.",
        "phd_tunnel", {"V": 0.0, "Tc": 1.2, "T": 0.1, "Gn": 1.0e-3},
        [knob("T", "Junction temperature", "T", 0.05, 1.19, 0.01, 0.1, "K"),
         knob("Tc", "This film (its Tc is hidden)", "Tc", 0.5, 9, 0.01, 1.2, "K", hidden=True)],
        ["Read the title card: this junction is read at 100 mK in a dilution cryostat, so it is a simulation.",
         "Choose the temperature and sweep the bias voltage from 0 to three gap voltages.",
         "At low temperature the current is almost zero below the gap voltage and rises steeply at it.",
         "Fit the BCS tunnelling current to the points; the fit gives the gap.",
         "Repeat at higher temperatures: the gap shrinks towards zero at Tc."],
        "SIMULATED INSTRUMENT. For a normal-metal / insulator / superconductor junction the current is the convolution "
        "of the superconductor's density of states N(E) = E/sqrt(E^2 - Delta^2) with the Fermi functions: "
        "I(V) = (Gn/e) integral from Delta to infinity of N(E)[f(E - eV) - f(E + eV)] dE. At low temperature almost no "
        "current flows below eV = Delta. The BCS gap at zero temperature is Delta(0) = 1.764 k Tc, and it falls with "
        "temperature (here the interpolation Delta(T) = Delta(0) tanh(1.74 sqrt(Tc/T - 1))). The film is illustrative.",
        "No cryogen exists here. Real dilution refrigerators use 3He/4He mixtures and must be handled by trained staff.",
        [_q("Below the gap voltage at low temperature the tunnelling current is", ["Almost zero", "Largest", "Negative"], 0, "There are no states inside the gap."),
         _q("The zero-temperature BCS gap is about", ["1.76 k Tc", "k Tc / 2", "10 k Tc"], 0, "Delta(0) = 1.764 k Tc.")],
        [TINKHAM, {"title": "I. Giaever, Phys. Rev. Lett. 5, 147 (1960); BCS theory, Phys. Rev. 108, 1175 (1957)"}, CODATA, SIMI, ILLUS],
        {"reading": "Delta", "textbook": "phd_gap", "tol": 0.01}, CH_QT, topic="Simulated research instrument")


def pulsed_nmr() -> dict:
    return _mk(
        "phd-pulsed-nmr", "phd-resonance-bench", "Pulsed NMR: Larmor frequency, inversion-recovery T1 and spin-echo T2",
        "Tune the probe to the Larmor frequency of the protons in a sample, measure T1 by inversion recovery and read the "
        "gyromagnetic ratio from the resonance.",
        "phd_bloch", {"B": 0.5, "gamma": 2.6752218744e8, "T1": 1.5, "T2": 0.4, "M0": 1.0, "fq": 2000.0, "noise": 0.002,
                      "seed": 7.0, "G": 0.0, "Dm": 2.3e-9},
        [knob("B", "Magnet field", "B", 0.3, 1.0, 0.001, 0.5, "T"),
         knob("T1", "This sample (its T1 is hidden)", "T1", 0.01, 5, 0.001, 1.5, "s", hidden=True),
         knob("T2", "This sample (its T2 is hidden)", "T2", 0.005, 4, 0.001, 0.4, "s", hidden=True)],
        ["Load the sample in the probe, centre it in the gap of the permanent magnet and switch the spectrometer on.",
         "Tune: step the RF frequency across the resonance and note the signal; the peak is at the Larmor frequency.",
         "Inversion recovery: a pi pulse inverts the magnetisation; a pi/2 pulse after a delay tau reads it. Record the signal for delays up to 5 T1.",
         "T1 is the time constant of the recovery to M0.",
         "Spin echo: a pi/2 pulse, a delay tau, a pi pulse; the echo at 2 tau shrinks with T2."],
        "Nuclei with spin 1/2 precess at the Larmor frequency, omega = gamma B, so f = gamma B/2 pi (42.58 MHz per tesla "
        "for protons). A pi pulse inverts the magnetisation M; after a delay tau a pi/2 pulse reads it: "
        "M(tau) = M0[1 - 2 exp(-tau/T1)]. A Hahn echo (pi/2 - tau - pi) refocuses the dephasing of an inhomogeneous "
        "field and its height decays as M0 exp(-2 tau/T2). In a field gradient diffusion adds a loss exp(-(2/3) gamma^2 "
        "G^2 D tau^3); the CPMG train, with many closely spaced pi pulses, removes it. The Bloch equations are "
        "evaluated as formulas with 0.2 % seeded noise; sample T1 and T2 are illustrative.",
        MAG_SAFE + " Radio-frequency power can heat tissue: keep the probe shielded.",
        [_q("The Larmor frequency is proportional to", ["B", "B^2", "1/B"], 0, "omega = gamma B."),
         _q("After a pi pulse the magnetisation is", ["Reversed, then recovers with T1", "Zero", "Unchanged"], 0, "M = -M0 at tau = 0 and relaxes back.")],
        [SLICHTER, {"title": "F. Bloch, Phys. Rev. 70, 460 (1946); E. L. Hahn, Phys. Rev. 80, 580 (1950); Carr and Purcell, Phys. Rev. 94, 630 (1954)"},
         CODATA, ILLUS],
        {"reading": "gamma", "textbook": "phd_gamma", "tol": 0.01}, CH_MR, cfg={"measure": "t1"})


def nmr_pfg() -> dict:
    return _mk(
        "phd-nmr-pfg", "phd-resonance-bench", "Self-diffusion by pulsed-field-gradient NMR (Stejskal-Tanner)",
        "Measure the spin-echo height of a liquid as the gradient pulse strength is raised and find its self-diffusion "
        "coefficient from the slope of ln(echo) against b.",
        "phd_pfg", {"g": 0.1, "gamma": 2.6752218744e8, "delta": 2.0e-3, "Dl": 0.02, "D": 2.3e-9, "noise": 0.002, "seed": 9.0},
        [knob("g", "Gradient pulse strength", "g", 0.0, 0.6, 0.005, 0.1, "T/m"),
         knob("D", "This liquid (its diffusion coefficient is hidden)", "D", 1e-11, 5e-9, 1e-12, 2.3e-9, "m^2/s", hidden=True)],
        ["Place the liquid in the probe and switch the spectrometer on.",
         "Set the gradient pulse length delta and the diffusion time Delta (both fixed in this run).",
         "Raise the gradient strength g in steps and record the echo height each time.",
         "Plot ln(echo) against b = (gamma g delta)^2 (Delta - delta/3).",
         "The slope of the straight line is -D."],
        "Molecules that diffuse between two gradient pulses are not refocused, so the spin-echo height falls: "
        "E = exp(-gamma^2 g^2 delta^2 D (Delta - delta/3)) (Stejskal and Tanner). A plot of ln E against "
        "b = gamma^2 g^2 delta^2 (Delta - delta/3) is a straight line of slope -D. Here the echo heights are the "
        "formula with 0.2 % seeded noise; the liquid's D is illustrative (water near 25 C is of order 2e-9 m^2/s, quoted "
        "from memory and unsourced).",
        MAG_SAFE,
        [_q("The echo height falls with gradient strength because", ["Diffusing spins are not refocused", "T1 is shorter", "The magnet weakens"], 0, "They move to a place with a different precession rate."),
         _q("The slope of ln E against b is", ["-D", "+D", "-1/D"], 0, "E = exp(-D b).")],
        [SLICHTER, {"title": "E. O. Stejskal and J. E. Tanner, J. Chem. Phys. 42, 288 (1965)"}, CODATA, ILLUS],
        {"reading": "D", "textbook": "phd_D", "tol": 0.01}, CH_MR)


def esr() -> dict:
    return _mk(
        "phd-esr", "phd-resonance-bench", "Electron spin resonance of DPPH: g-factor and line width",
        "Sweep the magnetic field through the ESR line of DPPH at several radio frequencies with field-modulated "
        "detection, find the resonance field from the zero crossing of the derivative line and get the g-factor.",
        "phd_esr", {"B": 0.0005, "f": 1.4e7, "g": 2.0036, "dB": 3.0e-5, "amp": 1.0},
        [knob("f", "RF frequency", "f", 5, 30, 0.1, 14, "MHz", k=1e6),
         knob("g", "This sample (its g-factor is hidden)", "g", 1.9, 2.2, 0.0001, 2.0036, "", hidden=True)],
        ["Place the DPPH sample in the RF coil between the Helmholtz coils and switch on the oscillator and the modulation.",
         "Set the oscillator to the first frequency and sweep the coil current (the field).",
         "Capture the derivative signal: the resonance is where it crosses zero.",
         "Read the peak-to-peak width of the derivative line.",
         "Repeat at two more frequencies; the resonance field is proportional to the frequency, and its slope gives g."],
        "A free electron spin in a field B has two energy levels split by g mu_B B. Radio waves of frequency f are absorbed "
        "when h f = g mu_B B. With a small modulation of the field and lock-in detection the output is the derivative of the "
        "absorption line: it crosses zero at the resonance, and the distance between its maximum and minimum is the "
        "peak-to-peak width dBpp = 2 dB/sqrt(3) for a Lorentzian line of half width dB. A line width gives the spin-spin "
        "time T2* = 2/(sqrt(3) gamma_e dBpp). The line position, g-factor 2.0036 and width of DPPH are quoted from memory "
        "and are unsourced / illustrative; no hyperfine structure is simulated, so only the single-line sample is covered.",
        MAG_SAFE,
        [_q("At resonance the derivative signal", ["Crosses zero", "Is largest", "Is negative"], 0, "The derivative of a peak is zero at the top."),
         _q("Doubling the RF frequency makes the resonance field", ["Twice as large", "Half", "Unchanged"], 0, "B0 = h f/(g mu_B).")],
        [SLICHTER, CODATA, ILLUS],
        {"reading": "g", "textbook": "phd_g", "tol": 0.01}, CH_MR)


def nmr_cw() -> dict:
    return _mk(
        "phd-nmr-cw", "phd-resonance-bench", "Continuous-wave NMR: gyromagnetic ratio and nuclear g-factor",
        "Hold the RF frequency fixed, sweep the magnet current through the proton resonance, read the resonance field "
        "at three frequencies and find the gyromagnetic ratio and the nuclear g-factor.",
        "phd_nmrcw", {"B": 0.3, "f": 1.5e7, "gamma": 2.6752218744e8, "dB": 2.0e-4, "amp": 1.0},
        [knob("f", "RF frequency", "f", 1.2e7, 2.0e7, 1e5, 1.5e7, "Hz"),
         knob("gamma", "This sample (its gamma is hidden)", "gamma", 2.0e8, 2.8e8, 1e5, 2.6752218744e8, "rad/(s T)", hidden=True)],
        ["Place the sample in the RF coil between the magnet poles and switch on the oscillator and the field modulation.",
         "Set the RF frequency to 12 MHz and sweep the magnet current (the field).",
         "Capture the derivative signal and find where it crosses zero.",
         "Repeat at 15 MHz and 18 MHz.",
         "The resonance field is B0 = 2 pi f/gamma: the slope of B0 against f gives the gyromagnetic ratio."],
        "A nucleus with magnetic moment mu = g_I mu_N I precesses at the Larmor frequency omega = gamma B with "
        "gamma = g_I mu_N/hbar. At a fixed RF frequency f the radio waves are absorbed when the field reaches "
        "B0 = 2 pi f/gamma (0.35 T at 15 MHz for protons). With modulation and a lock-in the output is the derivative of "
        "the absorption line, which crosses zero at B0. The slope of B0 against f gives gamma and so the nuclear g-factor "
        "g_I = hbar gamma/mu_N (5.586 for the proton). The line width here is set by the magnet's inhomogeneity.",
        MAG_SAFE + " The RF coil is live while the oscillator is on.",
        [_q("The resonance field increases when the RF frequency", ["Increases", "Decreases", "Is not changed"], 0, "B0 = 2 pi f/gamma."),
         _q("Fluorine-19 has a gamma ", ["Slightly smaller than hydrogen", "Twice as large", "Zero"], 0, "About 94 % of the proton value.")],
        [SLICHTER, CODATA, ILLUS],
        {"reading": "gI", "textbook": "phd_gI", "tol": 0.01}, CH_PG)


def mossbauer() -> dict:
    return _mk(
        "phd-mossbauer-fe57", "phd-resonance-bench", "Moessbauer spectroscopy of an iron absorber (simulated instrument)",
        "SIMULATED INSTRUMENT. Drive a 57Co source on a constant-acceleration velocity ramp, record the gamma transmission "
        "through an iron foil and read the hyperfine field from the spacing of the six lines.",
        "phd_mossbauer", {"v": 0.0, "Bhf": 33.0, "delta": 0.0, "eps": 0.0, "wid": 0.25e-3, "depth": 0.1},
        [knob("v", "Source velocity", "v", -0.008, 0.008, 0.0001, 0.0, "m/s", k=1e-3),
         knob("Bhf", "This absorber (its hyperfine field is hidden)", "Bhf", 10, 60, 0.01, 33, "T", hidden=True)],
        ["Read the title card: a 57Co source and a Doppler drive are not student apparatus, so this is a simulation.",
         "Mount the absorber between the source and the detector.",
         "Run the velocity sweep over -8 to +8 mm/s and capture the transmission.",
         "Six absorption lines appear in the ratio 3:2:1:1:2:3.",
         "The spacing of the outer pair gives the hyperfine field; their centre gives the isomer shift."],
        "SIMULATED INSTRUMENT. In 57Fe the 14.4 keV gamma ray is absorbed without recoil (Moessbauer effect) only when "
        "the Doppler shift of the moving source matches the nuclear transition in the absorber. A hyperfine field B_hf "
        "splits the ground state (I = 1/2) and the excited state (I = 3/2) so that six lines appear, the centre of the pattern "
        "giving the isomer shift and any asymmetry the quadrupole shift. The line positions follow the nuclear g-factors "
        "g_g and g_e: v = c mu_N B (g_e m_e - g_g m_g)/E_gamma. Those 57Fe nuclear moments, E_gamma = 14.4125 keV and the "
        "33 T of alpha-iron are quoted from memory and are unsourced / illustrative; the pattern is idealised, with no "
        "counting noise.",
        "No radioactive source is present. A real 57Co source (sealed, a few hundred MBq) needs a licence, shielding and a "
        "radiation-safety officer.",
        [_q("A Moessbauer line is absorbed only when", ["The Doppler shift matches the nuclear transition", "The absorber is hot", "The source is at rest"], 0,
            "The line is so narrow that a velocity of a few mm/s tunes through it."),
         _q("In alpha-iron the six lines have heights in the ratio", ["3:2:1:1:2:3", "1:1:1:1:1:1", "1:2:3:3:2:1"], 0, "Set by the angular momentum coupling of the transitions.")],
        [{"title": "R. L. Moessbauer, Z. Phys. 151, 124 (1958); N. N. Greenwood and T. C. Gibb, Moessbauer Spectroscopy (Chapman and Hall, 1971)"},
         CODATA, SIMI, ILLUS],
        {"reading": "Bhf", "textbook": "phd_Bhf", "tol": 0.01}, CH_MR, topic="Simulated research instrument")


BUILDERS = (sc_tc, sc_ic, acsusc, thermo, josephson, dcsquid, qhe, sdh, weakloc, tunnel, pulsed_nmr, nmr_pfg, esr,
            nmr_cw, mossbauer)
