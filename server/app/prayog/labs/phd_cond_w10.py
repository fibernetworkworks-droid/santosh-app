"""Lab pack `phd_cond_w10`: Ph.D. research techniques of condensed matter (wave 10) from
`syllabus/physics/phd.json` - low temperature and superconductivity, quantum transport and semiconductor
characterisation, magnetic resonance and hyperfine methods, magnetism and magneto-optics. Physics: the
`phd_cond_w10` kernel pack (`pk10_*`) and its JavaScript twin. One studio rig, `pk10-research-bench`, draws each
instrument (cryostat with magnet and transport rack, magnetometer, dilution refrigerator, probe station, solar-cell
bench, Moessbauer spectrometer, microwave resonance bridge, positron coincidence table, Kerr bench) and walks one sweep
per stage.

Honesty, said in every lab: these are research instruments a student cannot touch, so every lab is a SIMULATED
INSTRUMENT whose SIMULATED DATA comes from the published model named in its sources. Material constants quoted from
memory are labelled "from memory - verify"; numbers chosen for the lab are labelled illustrative. English only.
"""
from __future__ import annotations

from ..catalog import B, board, inst, knob, lab

RIG = "pk10-research-bench"
LEVEL = "Ph.D."
GRP = "Physics · Condensed Matter Research"
CH_LT = "Low temperature and superconductivity"
CH_QT = "Quantum transport"
CH_MR = "Magnetic resonance and hyperfine"
CH_MG = "Magnetism and magneto-optics"

SIM = {"title": "Hoola Prayogshala kernel pack phd_cond_w10",
       "note": "SIMULATED INSTRUMENT, SIMULATED DATA: every reading comes from the published model in the kernel, noiseless, "
               "rounded to the instrument's least count, and is checked against the textbook relation in Hoola's tests"}
SI = {"title": "SI 2019 exact constants h, e, kB, NA; CODATA 2018 muB, muN, m_e, mu0, eps0",
      "note": "R_K = h/e^2 = 25812.80745 ohm is exact in the SI since 2019"}
ILLUS = {"title": "Illustrative instrument and sample values",
         "note": "dimensions, currents, heater powers, line widths, the field laws and the sample sizes are chosen for the lab; "
                 "they are not properties of a named device"}
TINKHAM = {"title": "M. Tinkham, Introduction to Superconductivity, 2nd ed. (McGraw-Hill, 1996)"}
POBELL = {"title": "F. Pobell, Matter and Methods at Low Temperatures, 3rd ed. (Springer, 2007)"}
KITTEL = {"title": "C. Kittel, Introduction to Solid State Physics, 8th ed. (Wiley, 2005)"}
IHN = {"title": "T. Ihn, Semiconductor Nanostructures (Oxford University Press, 2010)"}
SCHRODER = {"title": "D. K. Schroder, Semiconductor Material and Device Characterization, 3rd ed. (Wiley, 2006)"}
SZE = {"title": "S. M. Sze and K. K. Ng, Physics of Semiconductor Devices, 3rd ed. (Wiley, 2007)"}
SLICHTER = {"title": "C. P. Slichter, Principles of Magnetic Resonance, 3rd ed. (Springer, 1990)"}
CLARKE = {"title": "J. Clarke and A. I. Braginski (eds.), The SQUID Handbook, vol. I (Wiley-VCH, 2004)"}
KNOLL = {"title": "G. F. Knoll, Radiation Detection and Measurement, 4th ed. (Wiley, 2010): fast-fast coincidence timing"}
MIT = {"title": "MIT Junior Lab (8.13/8.14) experiment notes: superconductivity, Moessbauer spectroscopy"}
DU = {"title": "University of Delhi, M.Sc. Physics (2025-26), PH-DSE5112 / 5164 research extensions"}

CRYO = ("Cryogens (liquid nitrogen at 77 K, liquid helium at 4.2 K) burn skin and can displace the air of a closed room: "
        "only trained staff transfer them, with a face shield and cryogenic gloves, in a ventilated room. Never seal a "
        "vessel that holds a cryogen. In this simulation nothing is poured.")
MAG = ("A superconducting magnet attracts steel tools and can disturb pacemakers and other implants: anyone with an "
       "implant stays outside the marked line, and watches, cards and phones stay away. In this simulation no magnet is live.")
RAD = ("Sealed sources only, handled with tongs and kept shielded; dosimeter badge worn; sources back in the locked store "
       "after the run. In this simulation no source is handled.")
ELEC = "Switch the supplies off before changing a connection and keep every current inside the instrument's range."
LASER = ("A class 3B laser: never look into the beam or a reflection, wear the goggles for the wavelength, keep the beam at "
         "bench height and block it at the end.")
MW = ("The microwave bridge is low power, but never look into an open waveguide and switch the source off before opening a "
      "joint.")


def _q(q, opts, ans, why):
    return {"q": q, "options": opts, "answer": ans, "why": why}


def _bodies(name: str, info: str) -> list[dict]:
    return [board(1.4, 0.7),
            B("main", "box", name=name, info=info, size=[0.42, 0.14, 0.26], pos=[-0.28, 0.07, -0.25], color="#4a4f57"),
            B("unit", "box", name="Instrument rack", info="The supplies, the readout and the recorder of the measurement.",
              size=[0.4, 0.12, 0.22], pos=[0.4, 0.06, -0.22], color="#2b2f36")]


def _mk(id, kernel, chapter, title, aim, params, knobs, insts, theory, steps, questions, sources, textbook, safety,
        name, info):
    return lab(id=id, rig=RIG, title=title, group=GRP, level=LEVEL, topic="Research laboratory", chapter=chapter, aim=aim,
               kernel=kernel, params=params, autorun=True, camera={"pos": [0.1, 0.9, 1.15], "look": [0.1, 0.1, -0.25]},
               floor=-0.03, bodies=_bodies(name, info), knobs=knobs, instruments=insts, steps=steps, theory=theory,
               safety=safety, tour=[{"say": info}], questions=questions, sources=sources + [SI, SIM],
               check={"reading": "res", "textbook": textbook})


def _y(label, unit, lc, digits):
    return [inst("y", "readout", label, "y", unit=unit, lc=lc, digits=digits)]


# ================================================================================ low temperature + superconductivity
def sc_tc() -> dict:
    return _mk(
        "pk10-sc-tc", "pk10_sctc", CH_LT, "Superconducting Tc by four-probe resistance against temperature",
        "Measure the four-probe resistance of a YBCO bar while it warms through its transition, in zero field and in an "
        "applied field: find Tc at the midpoint, the 10-90 % width and the residual resistance ratio. SIMULATED INSTRUMENT.",
        {"x": 100.0, "s": 0.0},
        [knob("x", "Sample temperature", "x", 0.3, 300, 0.01, 100, "K"),
         knob("Tc0", "This sample (its Tc is hidden)", "Tc0", 1, 130, 0.01, 92, "K", hidden=True)],
        _y("Four-probe resistance", "mohm", 1e-4, 4),
        "Below its critical temperature Tc a superconductor has zero resistance. A steady current through the outer "
        "pair of contacts and the voltage on the inner pair (four-probe) remove the lead and contact resistance. Above "
        "the transition the normal state is a straight line R = Rres + aT; Tc is quoted where R has fallen to half that "
        "line extrapolated to the same temperature, and the width as the 10-90 % span. An applied field lowers Tc along "
        "the phase boundary Bc(T) = Bc0(1 - (T/Tc0)^2). The residual resistance ratio RRR = R(300 K) / Rres measures how "
        "clean the metal is. In this lab the fall is a logistic step of width w (a smooth stand-in for the measured "
        "shape), the normal state is linear and Bc0 is illustrative.",
        ["Mount the bar with four spring contacts, the thermometer beside it, and lower the insert into the cryostat.",
         "Pass a steady 1 mA through the outer leads; read the inner pair with the nanovoltmeter.",
         "Warm slowly through the transition in zero field, in fine steps across the fall.",
         "Repeat in the applied field: the transition moves down.",
         "Read R at 300 K. Fit the normal-state line, find R/Rn = 0.5, the width and the RRR."],
        [_q("Why four probes and not two?", ["The contact and lead resistances drop out", "It doubles the current",
            "It cools the sample"], 0, "The inner pair carries no current, so its leads add no voltage."),
         _q("An applied field makes Tc", ["Lower", "Higher", "Unchanged"], 0, "The field suppresses superconductivity.")],
        [TINKHAM, MIT, KITTEL, {"title": "M. K. Wu et al., Phys. Rev. Lett. 58, 908 (1987): YBa2Cu3O7 near 93 K",
                                "note": "Tc 92 K used here; Nb 9.25 K and Pb 7.19 K are Kittel's table values - from memory - verify"},
         ILLUS],
        "pk10t_tc", CRYO + " " + MAG, "Cryostat insert in a superconducting magnet",
        "A sample insert in a helium cryostat with a superconducting magnet, a current source, a nanovoltmeter and a temperature controller.")


def sc_jc() -> dict:
    return _mk(
        "pk10-sc-jc", "pk10_jc", CH_LT, "Critical current density of a superconductor (1 uV/cm criterion)",
        "Record the transport I-V of a YBCO bridge at 77 K, 60 K and in a field, find Ic with the 1 uV/cm electric-field "
        "criterion and the critical current density Jc = Ic / A, and see Jc fall with temperature and field. SIMULATED INSTRUMENT.",
        {"x": 0.0, "s": 0.0},
        [knob("x", "Transport current", "x", 0, 1000, 0.001, 0, "A"),
         knob("Ic0", "This sample (its Ic0 is hidden)", "Ic0", 0.01, 1000, 0.01, 2, "A", hidden=True)],
        _y("Voltage between the taps", "uV", 1e-4, 4),
        "A superconductor carries current without loss only up to its critical current. Near Ic the voltage between "
        "taps a distance L apart rises steeply as a power of the current, V = Ec L (I/Ic)^n, so Ic is defined by an "
        "electric-field criterion: E = V/L = 1 uV/cm, i.e. V = 0.2 uV for taps 2 mm apart. Interpolating log V against "
        "log I between the two readings around that voltage gives Ic; the slope of the same line is the n-value. The "
        "critical current density Jc = Ic/A (cross-section A) is what is compared between samples. Here Ic falls with "
        "temperature as (1 - t^2)^1.5 and with field as 1/(1 + B/B0) (an illustrative law of the Kim type).",
        ["Mount the bridge, solder the current and voltage leads and cool to the first temperature.",
         "Raise the current in steps; read the voltage with the nanovoltmeter after it settles.",
         "Find where the voltage crosses 0.2 uV (1 uV/cm): that is Ic; Jc = Ic/A.",
         "Repeat at a lower temperature and in an applied field."],
        [_q("The 1 uV/cm criterion is needed because", ["The voltage rises smoothly, with no sharp onset",
            "The sample melts at Ic", "The voltmeter cannot read zero"], 0, "A criterion defines a reproducible Ic."),
         _q("A larger n-value means", ["A sharper transition", "A lower Tc", "More heating of the leads"], 0,
            "V ~ I^n rises more steeply.")],
        [TINKHAM, {"title": "Y. B. Kim, C. F. Hempstead and A. R. Strnad, Phys. Rev. 129, 528 (1963): field dependence of Jc"},
         {"title": "IEC 61788-2 (critical current measurement of composite superconductors): the 1 uV/cm criterion",
          "note": "cited from memory - verify"}, ILLUS],
        "pk10t_jc", CRYO + " Large currents heat the leads: stay within the supply's limit and ramp slowly.",
        "Variable-temperature insert with current leads",
        "A bridge on a variable-temperature insert in a magnet, a 1000 A-class current source, a nanovoltmeter and a temperature controller.")


def squid() -> dict:
    return _mk(
        "pk10-squid", "pk10_mag", CH_LT, "SQUID magnetometry: M-H loops and ZFC-FC M-T",
        "Measure the moment of a paramagnetic salt in a SQUID magnetometer: the M-H curve at 2 K and the zero-field-cooled "
        "and field-cooled M-T curves; find the Curie constant and the effective moment. SIMULATED INSTRUMENT.",
        {"x": 0.0, "s": 0.0, "typ": 0.0, "nmol": 1.0e-5, "g": 2.0, "J": 3.5, "T0": 2.0, "Bm": 5.0, "Bf": 0.01, "lcm": 1.0e-8},
        [knob("x", "Field or temperature", "x", -7, 400, 0.0001, 0),
         knob("g", "This salt (its g-factor is hidden)", "g", 1, 3, 0.0001, 2, hidden=True)],
        _y("Moment", "emu", 1e-8, 8),
        "A SQUID magnetometer moves the sample through superconducting pick-up coils coupled to a SQUID and reads the "
        "flux change as a magnetic moment. A paramagnetic salt follows the Brillouin function: at 2 K and 5 T the moment "
        "saturates, while in a small field it obeys the Curie law m = C B/T with C = N g^2 muB^2 J(J+1)/(3 kB). Plotting "
        "1/m against T gives a straight line of slope 1/(C B) and the effective moment mu_eff = g sqrt(J(J+1)) muB. "
        "Ferromagnetic nanoparticles show a blocking temperature where the zero-field-cooled (ZFC) and field-cooled (FC) "
        "curves part (Neel-Arrhenius, monodisperse); a superconductor shields its interior below Tc (ZFC) and expels "
        "less flux on field cooling (FC).",
        ["Weigh the sample into a gelatin capsule, fix it in the straw and centre it in the pick-up coils.",
         "At 2 K, sweep the field from +5 T down to -5 T and back, reading the moment.",
         "Warm to 300 K, cool in zero field, apply the measuring field and read the ZFC curve while warming.",
         "Cool again in the field and read the FC curve.",
         "Plot 1/m against T above 20 K: C from the slope, mu_eff from C."],
        [_q("ZFC and FC curves of a paramagnet", ["Lie on top of each other", "Part at a blocking temperature",
            "Cross at Tc"], 0, "A paramagnet has no memory of how it was cooled."),
         _q("The Curie constant gives", ["The effective moment per ion", "The coercive field", "The Weiss field only"], 0,
            "C = N mu_eff^2/(3 kB).")],
        [CLARKE, KITTEL, {"title": "C. P. Bean and J. D. Livingston, J. Appl. Phys. 30, 120S (1959): superparamagnetism and the blocking temperature"},
         {"title": "Gd2(SO4)3.8H2O: Gd3+ is 8S7/2, J = 7/2, g = 2 (from memory - verify)"}, ILLUS],
        "pk10t_mag", CRYO + " " + MAG, "SQUID magnetometer",
        "A SQUID magnetometer cabinet: a helium dewar with a 7 T magnet, the sample rod and its transport, and the control rack.")


def dilution() -> dict:
    return _mk(
        "pk10-dilution", "pk10_dil", CH_LT, "Dilution refrigerator: base temperature and cooling power",
        "Run a 3He-4He dilution refrigerator: read the mixing-chamber temperature at several heater powers, find the base "
        "temperature, the cooling power against temperature and the 3He circulation rate. SIMULATED INSTRUMENT.",
        {"x": 0.0, "s": 0.0},
        [knob("x", "Mixing-chamber heater power", "x", 0, 500, 0.1, 0, "uW"),
         knob("nd", "This fridge (its circulation rate is hidden)", "nd", 1e-6, 1e-3, 1e-7, 1e-4, "mol/s", hidden=True)],
        _y("Mixing-chamber temperature (RuO2)", "mK", 1e-3, 3),
        "In the mixing chamber 3He crosses from the concentrated phase into the dilute phase; the enthalpy difference "
        "cools it. With a perfect heat exchanger the cooling power is Qdot = 84 ndot T^2 W (ndot the 3He circulation "
        "rate in mol/s, T in K; Pobell). With a heater power P and the residual heat leak Q0 the chamber settles where "
        "84 ndot T^2 = P + Q0. So T^2 against P is a straight line: its slope is 1/(84 ndot), and its intercept gives the "
        "base temperature with the heater off, T_base = sqrt(Q0/(84 ndot)).",
        ["Condense the mixture, start circulation and wait for the base temperature.",
         "Read the RuO2 thermometer with the heater off.",
         "Step the heater power up, waiting for each temperature to settle.",
         "Plot T^2 against P: ndot from the slope, the heat leak from the intercept."],
        [_q("The cooling power of a dilution fridge rises with temperature as", ["T^2", "T", "exp(-1/T)"], 0,
            "Qdot = 84 ndot T^2 for an ideal heat exchanger."),
         _q("What sets the base temperature?", ["The heat leak against the cooling power", "The helium bath only",
            "The magnet"], 0, "Base temperature is where the cooling power equals the parasitic heat.")],
        [POBELL, {"title": "Pobell, ch. 7: Qdot = ndot3 (95 Tmc^2 - 11 Tex^2), i.e. 84 ndot T^2 for Tex = Tmc",
                  "note": "the coefficients 95, 11 and 84 J/(mol K^2) are quoted from memory - verify"}, ILLUS],
        "pk10t_nd", CRYO + " The still and the gas handling system are at low pressure: only the operator opens a valve.",
        "Dilution refrigerator insert and gas handling rack",
        "A dilution refrigerator cryostat hanging from its frame, the gas handling rack with pumps and the resistance bridge.")


def heat_capacity() -> dict:
    return _mk(
        "pk10-heat-capacity", "pk10_hcr", CH_LT, "Heat capacity by the relaxation method",
        "Measure the heat capacity of a copper reference from 1 to 10 K by thermal relaxation: find the Sommerfeld "
        "coefficient and the Debye temperature from C/T against T^2. SIMULATED INSTRUMENT.",
        {"x": 4.0, "s": 0.0, "typ": 0.0},
        [knob("x", "Platform temperature", "x", 0.3, 60, 0.01, 4, "K"),
         knob("ThD", "This sample (its Debye temperature is hidden)", "ThD", 50, 2000, 0.1, 343, "K", hidden=True)],
        [inst("y", "readout", "Relaxation time", "y", unit="s", lc=1e-6, digits=6)],
        "The sample sits on a platform hanging from a weak thermal link of conductance K. A heater power P0 raises it by "
        "dT = P0/K above the bath; switched off, the platform relaxes back as exp(-t/tau) with tau = C/K. So each "
        "temperature gives K from the steady rise and C = K tau. For a metal at low temperature C = gamma T + beta T^3: "
        "the electrons give gamma T (the Sommerfeld coefficient) and the lattice the Debye T^3 law, beta = "
        "(12 pi^4/5) R/ThD^3 per mole. C/T against T^2 is a straight line: gamma is its intercept, beta its slope. A "
        "superconductor shows a jump at Tc and an exponential fall below it; a magnetic insulator shows a two-level "
        "(Schottky) anomaly.",
        ["Grease the sample onto the platform, pump the chamber to high vacuum and cool to the lowest temperature.",
         "At each temperature apply the heater power, read the steady rise dT, switch off and fit the decay time tau.",
         "C = (P0/dT) tau; divide by the number of moles.",
         "Plot C/T against T^2: gamma from the intercept, ThD from the slope."],
        [_q("In C = gamma T + beta T^3, gamma comes from", ["The conduction electrons", "The phonons", "The addenda"], 0,
            "The electronic heat capacity is linear in T."),
         _q("The relaxation time tau equals", ["C/K", "K/C", "C K"], 0, "A heat capacity drained through a conductance.")],
        [POBELL, KITTEL, {"title": "Kittel, Tables 6.3 and 5.1: copper gamma = 0.695 mJ/(mol K^2), ThD = 343 K; Nb gamma = 7.79 mJ/(mol K^2), ThD = 275 K",
                          "note": "quoted from memory - verify"},
         {"title": "J. S. Hwang, K. J. Lin and C. Tien, Rev. Sci. Instrum. 68, 94 (1997): relaxation calorimetry",
          "note": "cited from memory - verify"}, ILLUS],
        "pk10t_hcr", CRYO, "Relaxation calorimeter puck in a cryostat",
        "A calorimeter puck with a sapphire platform on fine wires, inserted in a helium cryostat, with its bridge and heater supply.")


def thermal_cond() -> dict:
    return _mk(
        "pk10-thermal-cond", "pk10_ktc", CH_LT, "Steady-state thermal conductivity at low temperature",
        "Measure the thermal conductivity of a copper rod from 1 to 20 K by the steady-state method and find its residual "
        "resistivity through the Wiedemann-Franz law. SIMULATED INSTRUMENT.",
        {"x": 2.0, "s": 0.0, "typ": 0.0},
        [knob("x", "Bath temperature", "x", 0.3, 100, 0.01, 2, "K"),
         knob("rho0", "This rod (its residual resistivity is hidden)", "rho0", 1, 10000, 0.1, 100, "pohm m", k=1e-12, hidden=True)],
        [inst("y", "readout", "Temperature difference", "y", unit="mK", lc=1e-5, digits=5)],
        "One end of the rod is fixed to the bath, a heater P sits on the other, and two thermometers a distance L apart "
        "read the temperature difference dT. In the steady state the heat flowing through the cross-section A is P, so "
        "kappa = P L/(A dT), belonging to the mean temperature. In a pure metal the electrons carry the heat: at low T "
        "1/kappa = W0/T + beta T^2, the first term from impurities with W0 = rho0/L0 (Wiedemann-Franz, L0 = 2.44e-8 "
        "W ohm/K^2) and the second from phonon scattering, so T/kappa against T^3 is a line whose intercept is rho0/L0. "
        "An alloy follows a weak power law; an insulating crystal shows the phonon peak, rising as T^3 (boundary "
        "scattering, Casimir) and falling once Umklapp scattering sets in.",
        ["Clamp the rod to the cold plate, fix the heater and two calibrated thermometers, and radiation-shield it.",
         "At each bath temperature apply the heater power and wait for dT to settle.",
         "kappa = P L/(A dT) at the mean temperature.",
         "Plot T/kappa against T^3: the intercept times L0 is the residual resistivity."],
        [_q("Wiedemann-Franz relates kappa of a metal to", ["Its electrical conductivity", "Its heat capacity only",
            "Its density"], 0, "kappa/(sigma T) = L0."),
         _q("A small dT is used so that", ["kappa belongs to one temperature", "The heater lasts longer",
            "The bath stays warm"], 0, "kappa changes with temperature.")],
        [POBELL, KITTEL, {"title": "R. Berman, Thermal Conduction in Solids (Oxford, 1976): boundary (Casimir) and Umklapp scattering"},
         {"title": "NIST cryogenic material properties: 304 stainless steel thermal conductivity",
          "note": "the stainless power law and the sapphire numbers here are order-of-magnitude, from memory - verify"}, ILLUS],
        "pk10t_ktc", CRYO, "Steady-state conductivity stage in a cryostat",
        "A rod clamped to the cold plate of a cryostat, a heater on its free end and two thermometers, with the resistance bridge.")


# ================================================================================ quantum transport
def qhe() -> dict:
    return _mk(
        "pk10-qhe", "pk10_qhe", CH_QT, "Integer quantum Hall effect (simulated instrument)",
        "Sweep the field to 9 T on a GaAs/AlGaAs Hall bar at 1.5 K and 300 mK, read R_xy and R_xx, find the plateaus "
        "h/(i e^2), the carrier density from the low-field Hall slope and the mobility. SIMULATED INSTRUMENT.",
        {"x": 0.0, "s": 0.0, "gr": 0.0, "n": 3.0e15, "mu": 100.0},
        [knob("x", "Magnetic field", "x", 0, 12, 0.01, 0, "T"),
         knob("mu", "This wafer (its mobility is hidden)", "mu", 0.1, 1000, 0.01, 100, "m^2/V s", hidden=True)],
        [inst("y", "readout", "Hall resistance R_xy", "y", unit="ohm", lc=1e-3, digits=3)],
        "In a two-dimensional electron gas a field B splits the states into Landau levels, each holding eB/h electrons "
        "per square metre (per spin). The filling factor is nu = n h/(e B). When the Fermi level lies between levels "
        "the longitudinal resistance R_xx vanishes and the Hall resistance is exactly R_xy = h/(i e^2): the von Klitzing "
        "constant h/e^2 = 25812.807 ohm divided by an integer, independent of the sample's shape and impurities. At low "
        "field R_xy = B/(n e) gives the density, and R_xx(0) = rho0 L/W gives the mobility mu = 1/(n e rho0). Lower "
        "temperature makes the plateaus wider. Graphene shows the half-integer sequence nu = 2, 6, 10 (= 4(k + 1/2)). "
        "The staircase here is a smoothed model, not a full Landau-level calculation.",
        ["Cool the Hall bar to 1.5 K; pass 100 nA through the source and drain.",
         "Sweep B from 0 to 9 T, reading R_xy and R_xx.",
         "Cool to 300 mK and sweep again.",
         "Density from the low-field Hall slope; on each R_xx zero, i R_xy = h/e^2."],
        [_q("On a quantum Hall plateau R_xx is", ["Zero", "h/e^2", "Largest"], 0, "Transport is dissipationless there."),
         _q("The plateau value depends on", ["Only h, e and the integer i", "The sample's width", "The mobility"], 0,
            "That is why it is a resistance standard.")],
        [IHN, {"title": "K. von Klitzing, G. Dorda and M. Pepper, Phys. Rev. Lett. 45, 494 (1980)"},
         {"title": "K. S. Novoselov et al., Nature 438, 197 (2005); Y. Zhang et al., Nature 438, 201 (2005): graphene's half-integer sequence"},
         ILLUS],
        "pk10t_rk", CRYO + " " + MAG, "Hall bar in a 3He cryostat and magnet",
        "A Hall-bar chip on a 3He insert inside a 12 T magnet, with a lock-in amplifier and a current source.")


def sdh() -> dict:
    return _mk(
        "pk10-sdh", "pk10_sdh", CH_QT, "Shubnikov-de Haas oscillations",
        "Record R_xx of a GaAs 2DEG against 1/B, find the carrier density from the period, the effective mass from the "
        "temperature dependence of the amplitude and the quantum lifetime from the Dingle plot. SIMULATED INSTRUMENT.",
        {"x": 1.0, "s": 0.0, "typ": 0.0, "n": 3.0e15, "ms": 0.067, "tq": 1.0e-12, "Bhi": 4.0, "nper": 9.0, "Bf": 2.0},
        [knob("x", "Field or temperature", "x", 0.1, 30, 0.0001, 1),
         knob("ms", "This sample (its effective mass is hidden)", "ms", 0.005, 2, 0.0001, 0.067, "m_e", hidden=True)],
        [inst("y", "readout", "Longitudinal resistance", "y", unit="ohm", lc=1e-5, digits=5)],
        "Landau quantisation makes the density of states at the Fermi level oscillate as the field changes, and R_xx "
        "with it, periodically in 1/B (Lifshitz-Kosevich): dR/R0 = 4 (X/sinh X) exp(-pi/(wc tq)) cos(2 pi F/B - pi), "
        "X = 2 pi^2 kB T m*/(hbar e B). The frequency F gives the density of a 2D gas, n = gs e F/h (gs = 2 for GaAs, "
        "4 for graphene); in a 3D metal such as bismuth F is the extremal area of a Fermi-surface pocket. The amplitude "
        "against T at a fixed field follows X/sinh X, which gives m*. The amplitude against 1/B (Dingle plot) gives the "
        "quantum lifetime tq. The fundamental harmonic only.",
        ["Cool the sample to 1.5 K and pass a small lock-in current.",
         "Sweep the field, reading R_xx at steps evenly spaced in 1/B.",
         "Number the maxima and plot their 1/B against the index: the slope is 1/F.",
         "At a fixed field read the oscillation amplitude at several temperatures and fit X/sinh X for m*."],
        [_q("SdH oscillations are periodic in", ["1/B", "B", "B^2"], 0, "Landau levels cross the Fermi level at equal steps of 1/B."),
         _q("Warming the sample makes the oscillations", ["Weaker", "Stronger", "Faster in 1/B"], 0,
            "Thermal smearing: the factor X/sinh X.")],
        [IHN, {"title": "D. Shoenberg, Magnetic Oscillations in Metals (Cambridge, 1984): Lifshitz-Kosevich formula"},
         {"title": "GaAs conduction-band mass 0.067 m_e; Bi hole pocket F about 6.3 T, m* about 0.064 m_e",
          "note": "quoted from memory - verify; densities and lifetimes are illustrative"}, ILLUS],
        "pk10t_sdh", CRYO + " " + MAG, "Sample in a variable-temperature cryostat and magnet",
        "A sample on a rotator in a variable-temperature insert inside a superconducting magnet, with a lock-in amplifier.")


def hall_mob() -> dict:
    return _mk(
        "pk10-hall-mob", "pk10_hall", CH_QT, "Hall bar and van der Pauw: carrier density and mobility against T",
        "Measure a doped silicon layer as a Hall bar and as a van der Pauw square: find the sheet density, the sheet "
        "resistance and the Hall mobility at 300 K, then the mobility from 20 to 400 K and its scattering law. SIMULATED INSTRUMENT.",
        {"x": 0.0, "s": 0.0},
        [knob("x", "Field, configuration or temperature", "x", -1, 400, 0.01, 0),
         knob("muL", "This layer (its lattice mobility is hidden)", "muL", 0.001, 2, 0.0001, 0.14, "m^2/V s", hidden=True)],
        [inst("y", "readout", "Hall voltage or resistance", "y", unit="uV", lc=1e-4, digits=4)],
        "The Hall voltage across a bar carrying a current I in a field B is V_H = I B/(e ns), so the slope of V_H against "
        "B gives the sheet density ns. The van der Pauw method measures the sheet resistance Rs of a sample of any "
        "shape from two four-terminal resistances, exp(-pi RA/Rs) + exp(-pi RB/Rs) = 1. The Hall mobility is "
        "mu = 1/(e ns Rs). Against temperature the mobility follows Matthiessen's rule: phonons limit it at high T "
        "(mu ~ T^-alpha) and ionised impurities at low T (mu ~ T^1.5), so the slope of log mu against log T names the "
        "scattering mechanism.",
        ["Bond the Hall bar and the van der Pauw square; check that every contact is ohmic.",
         "At 300 K sweep B from -1 to +1 T with a fixed current and read the Hall voltage.",
         "On the square, read the two four-terminal resistances RA and RB.",
         "Warm from 20 to 400 K reading the Hall and longitudinal voltages at a fixed field."],
        [_q("The van der Pauw method needs", ["Small contacts on the edge of a uniform sample", "A long thin bar",
            "No magnetic field ever"], 0, "That is the theorem's condition."),
         _q("Mobility rising with temperature at low T points to", ["Ionised-impurity scattering", "Phonon scattering",
            "Surface roughness only"], 0, "Impurity scattering weakens as the carriers get faster.")],
        [SCHRODER, SZE, {"title": "L. J. van der Pauw, Philips Res. Rep. 13, 1 (1958)"},
         {"title": "Silicon electron mobility 1350-1400 cm^2/V s and lattice exponent about 2.4 (Sze)",
          "note": "quoted from memory - verify; the doping and the impurity term are illustrative"}, ILLUS],
        "pk10t_mu", ELEC + " The cryostat is pumped: do not open it cold.", "Hall bar on a closed-cycle cryostat stage",
        "A Hall bar and a van der Pauw square on a closed-cycle cryostat stage between electromagnet poles, with a current source and nanovoltmeter.")


def seebeck() -> dict:
    return _mk(
        "pk10-seebeck", "pk10_seeb", CH_QT, "Seebeck coefficient and thermoelectric power factor",
        "Measure the Seebeck coefficient of bismuth telluride at 300 K by the differential steady-state method and by the "
        "quasi-static slope method, its resistivity by four probes, and the power factor S^2/rho. SIMULATED INSTRUMENT.",
        {"x": 0.0, "s": 0.0},
        [knob("x", "Temperature difference or current", "x", -5, 100, 0.01, 0),
         knob("S", "This sample (its Seebeck coefficient is hidden)", "S", -0.001, 0.001, 1e-7, 0.0002, "V/K", hidden=True)],
        [inst("y", "readout", "Thermoelectric voltage", "y", unit="uV", lc=1e-3, digits=3)],
        "A temperature difference dT across a conductor produces a voltage V = S dT (S the Seebeck coefficient). It is "
        "read through copper leads, which add their own small coefficient (S_Cu about +1.8 uV/K at 300 K), and the "
        "amplifier adds an offset voltage. The differential method takes two equal and opposite small dT about the mean "
        "temperature, so the offset cancels: S - S_Cu = (V+ - V-)/(2 dT). The quasi-static method sweeps dT and takes "
        "the slope. With the four-probe resistivity rho the power factor is S^2/rho; ZT also needs kappa.",
        ["Clamp the bar between two heater blocks with a differential thermocouple and copper voltage leads.",
         "Set dT = -1 K and +1 K about 300 K and read the voltage at each.",
         "Sweep dT from -2 to +2 K for the slope method.",
         "Pass currents and read the four-probe voltage for rho; then S^2/rho."],
        [_q("Reversing dT in the differential method", ["Cancels the offset voltage", "Doubles the offset",
            "Changes the sign of S"], 0, "The offset does not reverse with dT."),
         _q("A positive Seebeck coefficient means the majority carriers are", ["Holes", "Electrons", "Phonons"], 0,
            "Holes diffuse to the cold end and charge it positive.")],
        [DU, {"title": "G. J. Snyder and E. S. Toberer, Nature Materials 7, 105 (2008): thermoelectric materials",
              "note": "Bi2Te3 S about +200 uV/K, rho about 1e-5 ohm m at 300 K; copper +1.83 uV/K - from memory - verify"}, ILLUS],
        "pk10t_s", ELEC + " The heater blocks get hot: let them cool before touching.", "Seebeck stage with two heater blocks",
        "A bar between two small heater blocks with a differential thermocouple, in a vacuum chamber, with a nanovoltmeter.")


def dlts() -> dict:
    return _mk(
        "pk10-dlts", "pk10_dlts", CH_QT, "Deep level transient spectroscopy",
        "Scan the temperature of a Schottky diode on n-Si with a double-boxcar DLTS at four rate windows; from the peak "
        "temperatures make the Arrhenius plot and find the trap activation energy, capture cross-section and density. SIMULATED INSTRUMENT.",
        {"x": 200.0, "s": 0.0},
        [knob("x", "Sample temperature", "x", 20, 800, 0.01, 200, "K"),
         knob("Ea", "This trap (its activation energy is hidden)", "Ea", 0.05, 1.5, 0.0001, 0.55, "eV", hidden=True)],
        [inst("y", "readout", "Boxcar signal", "y", unit="fF", lc=1e-4, digits=4)],
        "A filling pulse fills the traps in the depletion layer; at the reverse bias they then emit their electrons at "
        "the rate e = sigma gamma T^2 exp(-Ea/kT) and the capacitance recovers as dC0 exp(-e t). A double boxcar "
        "S = dC(t1) - dC(t2) (t2 = 2 t1) is largest when e = ln2 / t1, the rate window. Scanning T with several windows "
        "gives a peak temperature for each rate; ln(e/T^2) against 1/T is a straight line of slope -Ea/kB (the Arrhenius "
        "plot), its intercept gives sigma, and the peak height dC0/C0 = NT/(2 ND) gives the trap density.",
        ["Mount the diode on the cryostat stage and set the reverse bias and the filling pulse.",
         "Set the rate windows 1, 2, 5 and 10 ms (t1) and scan the temperature through the peak of each.",
         "Find the peak temperature of each window.",
         "Plot ln(e/T^2) against 1/T: Ea from the slope, sigma from the intercept."],
        [_q("A shorter rate window moves the DLTS peak to", ["Higher temperature", "Lower temperature", "Nowhere"], 0,
            "A faster emission needs more heat."),
         _q("The factor T^2 in the emission rate comes from", ["The thermal velocity and the density of states",
            "The capacitance", "The boxcar"], 0, "v_th ~ T^1/2, Nc ~ T^3/2.")],
        [SCHRODER, {"title": "D. V. Lang, J. Appl. Phys. 45, 3023 (1974): deep level transient spectroscopy"},
         {"title": "gamma_n = 1.07e21 (Si) and 2.3e20 (GaAs) cm^-2 s^-1 K^-2; Au acceptor in Si about Ec - 0.55 eV; EL2 in GaAs about Ec - 0.82 eV",
          "note": "quoted from memory - verify; cross-sections and densities illustrative"}, ILLUS],
        "pk10t_ea", ELEC + " " + CRYO, "DLTS cryostat with a capacitance meter",
        "A diode on a liquid-nitrogen cryostat stage with a 1 MHz capacitance meter, a pulse generator and the boxcar.")


def cv() -> dict:
    return _mk(
        "pk10-cv", "pk10_cv", CH_QT, "C-V doping profile of a Schottky diode, p-n junction or MOS capacitor",
        "Measure the high-frequency C-V of a Schottky diode on n-Si: find the doping density from the slope of 1/C^2, the "
        "built-in potential from its intercept and the doping profile against depth. SIMULATED INSTRUMENT.",
        {"x": 0.0, "s": 0.0, "typ": 0.0},
        [knob("x", "Bias", "x", -10, 10, 0.01, 0, "V"),
         knob("Vbi", "This diode (its built-in potential is hidden)", "Vbi", 0.1, 1.5, 0.0001, 0.6, "V", hidden=True)],
        [inst("y", "readout", "Capacitance", "y", unit="pF", lc=1e-4, digits=4)],
        "A reverse-biased junction is a capacitor whose plates are the edges of the depletion layer: C = eps A/W. For a "
        "Schottky diode or a one-sided abrupt junction 1/C^2 = 2(Vbi - V - kT/q)/(q eps N A^2), so 1/C^2 against V is "
        "a line: N from its slope, Vbi from its intercept, and the local N(W) = 2/(q eps A^2 d(1/C^2)/dV) at the depth "
        "W = eps A/C is the doping profile. For a p+-n junction Vbi = (kT/q) ln(NA ND/ni^2). A MOS capacitor gives Cox in "
        "accumulation and a depletion branch whose 1/C^2 line reaches 1/Cox^2 at the flat-band voltage "
        "VFB = phi_ms - Qox/Cox. Depletion approximation.",
        ["Probe the device on the station and connect the LCR meter (1 MHz, small a.c. level).",
         "Sweep the bias across the range, reading C.",
         "Plot 1/C^2 against V.",
         "N from the slope; Vbi (or VFB) from the intercept; the profile N(W) point by point."],
        [_q("1/C^2 is linear in V when", ["The doping is uniform", "The diode is forward biased", "The frequency is low"], 0,
            "Each extra volt uncovers the same charge per unit depth."),
         _q("A MOS capacitor in accumulation shows", ["Its oxide capacitance", "Its smallest capacitance", "No capacitance"], 0,
            "The semiconductor surface is highly conducting.")],
        [SCHRODER, SZE, {"title": "Silicon: eps_r = 11.7, ni about 1.0e10 cm^-3 at 300 K; SiO2 eps_r = 3.9",
                         "note": "quoted from memory - verify; dopings, oxide charge and work-function difference illustrative"}, ILLUS],
        "pk10t_cv", ELEC, "Probe station with an LCR meter",
        "A probe station with two micromanipulator probes on the device under a microscope, and a 1 MHz LCR meter with a bias supply.")


def haynes() -> dict:
    return _mk(
        "pk10-haynes", "pk10_hs", CH_QT, "Drift mobility and lifetime by Haynes-Shockley with pulsed laser injection",
        "Inject holes into an n-Ge bar with a laser pulse, watch the pulse arrive at the collector at several distances "
        "and fields, and find the drift mobility, the diffusion coefficient and the lifetime. SIMULATED INSTRUMENT.",
        {"x": 5.0, "s": 0.0},
        [knob("x", "Distance or drift field", "x", 1, 40, 0.01, 5),
         knob("mu", "This bar (its drift mobility is hidden)", "mu", 0.005, 1, 0.0001, 0.19, "m^2/V s", hidden=True)],
        [inst("y", "readout", "Arrival time of the peak", "y", unit="us", lc=1e-4, digits=4)],
        "A short laser pulse makes a packet of minority carriers at one point of a bar carrying a drift field E. The "
        "packet drifts at v = mu E, spreads by diffusion (D = mu kT/e) and decays with the lifetime tau, so the "
        "collector a distance d away sees n ~ exp(-(d - v t)^2/(4 D t) - t/tau)/sqrt(t). The arrival time grows as d/v, so "
        "the slope of t0 against d gives 1/v and mu = v/E (the recombination term changes it by under 0.1 % at this "
        "field); the width gives D, and the peak height against t0 gives tau.",
        ["Set the drift field across the bar and focus the laser on the injection point.",
         "Move the collector probe and read the arrival time, width and height of the pulse on the oscilloscope.",
         "At a fixed distance change the drift field and read again.",
         "mu from the slope of t0 against d; D from the width; tau from the heights."],
        [_q("Doubling the drift field makes the pulse arrive", ["In about half the time", "In twice the time", "At the same time"], 0,
            "v = mu E."),
         _q("The pulse gets wider as it travels because of", ["Diffusion", "The laser", "The collector"], 0, "Its width grows as sqrt(D t).")],
        [DU, SZE, {"title": "J. R. Haynes and W. Shockley, Phys. Rev. 81, 835 (1951)"},
         {"title": "Hole mobility in Ge about 1900 and electron mobility in Si about 1350 cm^2/V s at 300 K (Sze)",
          "note": "quoted from memory - verify; lifetimes illustrative"}, ILLUS],
        "pk10t_hs", LASER + " " + ELEC, "Haynes-Shockley bar with a pulsed laser",
        "A germanium bar on a probe stage with a movable collector probe, a pulsed laser, a drift supply and an oscilloscope.")


def solar() -> dict:
    return _mk(
        "pk10-solar-eqe", "pk10_eqe", CH_QT, "Solar cell external quantum efficiency and dark I-V",
        "Measure the external quantum efficiency spectrum of a silicon cell with a monochromator and the dark forward "
        "I-V; find the ideality factor, the band-gap edge and the short-circuit current. SIMULATED INSTRUMENT.",
        {"x": 500.0, "s": 0.0},
        [knob("x", "Wavelength or bias", "x", 0, 1400, 0.001, 500),
         knob("nid", "This cell (its ideality factor is hidden)", "nid", 1, 3, 0.0001, 1.3, hidden=True)],
        [inst("y", "readout", "EQE or dark current", "y", unit="% or mA", lc=1e-7, digits=7)],
        "The EQE is the fraction of incident photons that give an electron at short circuit, measured against a "
        "calibrated photodiode at each wavelength: EQE = eta (1 - R)(1 - exp(-alpha W)), with the absorption alpha rising "
        "above the band gap (as (E - Eg)^2 for indirect silicon, (E - Eg)^1/2 for direct CdTe or a perovskite). Jsc is "
        "the EQE weighted by the reference spectrum (AM1.5G, IEC 60904-3). In the dark the cell is a diode: "
        "I = I0(exp(qV/(n kT)) - 1) with series and shunt resistance; the slope of ln I against V in the middle range "
        "gives the ideality factor n.",
        ["Mount the cell under the monochromator beam; calibrate the beam with the reference photodiode.",
         "Step the wavelength from 350 to 1200 nm and read the short-circuit current; EQE = cell/reference.",
         "Cover the cell, sweep the forward bias and read the dark current.",
         "n from the slope of ln I against V between 1 uA and 100 uA."],
        [_q("The EQE falls to zero at long wavelength because", ["The photon energy is below the band gap",
            "The lamp switches off", "The cell heats"], 0, "No absorption below Eg."),
         _q("Series resistance bends the ln I - V line at", ["High current", "Low current", "Zero bias"], 0,
            "The IR drop grows with current.")],
        [SCHRODER, {"title": "IEC 60904-8 (spectral responsivity) and IEC 60904-3 (AM1.5G reference spectrum)",
                    "note": "this lab does not carry the AM1.5G table, so its Jsc is only an estimate against a flat illustrative spectrum"},
         {"title": "Band gaps: Si 1.12, CdTe about 1.5, MAPbI3 perovskite about 1.6 eV",
          "note": "quoted from memory - verify; absorption and diode parameters illustrative"}, ILLUS],
        "pk10t_nid", ELEC + " The xenon lamp is bright and hot and emits UV: keep its housing closed.",
        "Monochromator EQE bench with a source-measure unit",
        "A xenon lamp and monochromator with a chopper and lock-in, the cell on a temperature-controlled chuck, and a source-measure unit.")


# ================================================================================ magnetic resonance + hyperfine
def mossbauer() -> dict:
    return _mk(
        "pk10-mossbauer", "pk10_moss", CH_MR, "Moessbauer spectroscopy of iron compounds",
        "Record the 57Fe Moessbauer spectrum of an alpha-iron foil with a constant-acceleration drive and find the "
        "hyperfine field from the outer lines of the sextet; the isomer shift and quadrupole splitting follow. SIMULATED INSTRUMENT.",
        {"x": 0.0, "s": 0.0, "typ": 0.0, "B": 33.0, "dIS": 0.0, "eps": 0.0},
        [knob("x", "Source velocity", "x", -12, 12, 0.0001, 0, "mm/s"),
         knob("B", "This absorber (its hyperfine field is hidden)", "B", 0, 70, 0.001, 33, "T", hidden=True)],
        [inst("y", "readout", "Counts in the channel", "y", unit="counts", lc=1, digits=0)],
        "A 57Co source emits the 14.4 keV gamma ray of 57Fe with a natural width of nano-electronvolts. Moving the source "
        "at velocity v Doppler-shifts it by (v/c) E, enough to scan the absorber's nuclear levels. In a magnetic "
        "material the hyperfine field B splits the I = 1/2 ground and I = 3/2 excited states, giving six lines "
        "(intensities 3:2:1:1:2:3 for a random foil): the outer pair is 2 (|mu_e|/I_e x 3/2 + mu_g/I_g x 1/2) B c/E apart, "
        "10.6 mm/s at 33 T. The centre of the pattern is the isomer shift; a quadrupole interaction shifts the outer "
        "pair against the inner four (sextet) or splits a single line into a doublet. Lines are Lorentzians, so 1/(N0 - N) "
        "is a parabola near each line and gives its centre.",
        ["Mount the foil between the source on the drive and the proportional counter; set the window on 14.4 keV.",
         "Run a survey over +-10 mm/s.",
         "Take fine steps across each line.",
         "Find each line centre; B from the outer pair; the isomer shift from the centre."],
        [_q("A paramagnetic iron compound with no field and no field gradient shows", ["One line", "Six lines", "Two lines"], 0,
            "No splitting, only the isomer shift."),
         _q("The isomer shift measures", ["The s-electron density at the nucleus", "The magnetic field", "The thickness"], 0,
            "It depends on the chemical state of iron.")],
        [MIT, {"title": "R. L. Moessbauer, Z. Phys. 151, 124 (1958); N. N. Greenwood and T. C. Gibb, Moessbauer Spectroscopy (Chapman and Hall, 1971)"},
         {"title": "57Fe: mu_g = +0.09044 muN, mu_e = -0.1549 muN, E = 14.4125 keV; alpha-Fe 33.0 T at room temperature",
          "note": "quoted from memory - verify"}, ILLUS],
        "pk10t_moss", RAD, "Moessbauer spectrometer",
        "A 57Co source on a velocity transducer, the absorber in its holder, a proportional counter, and the drive unit with its multichannel scaler.")


def fmr() -> dict:
    return _mk(
        "pk10-fmr", "pk10_fmr", CH_MR, "Ferromagnetic resonance: Kittel relation and damping",
        "Measure the field-swept FMR of a YIG sphere at 4, 8, 12 and 16 GHz; fit the Kittel relation for the g-factor and "
        "the line width against frequency for the Gilbert damping. SIMULATED INSTRUMENT.",
        {"x": 0.1, "s": 0.0, "typ": 0.0, "g": 2.0, "Ms": 0.0, "alpha": 5.0e-5, "dB0": 2.0e-5},
        [knob("x", "Magnetic field", "x", 0, 2, 0.000001, 0.1, "T"),
         knob("g", "This sample (its g-factor is hidden)", "g", 1.5, 2.5, 0.0001, 2, hidden=True)],
        [inst("y", "readout", "Lock-in signal dP/dB", "y", unit="arb.", lc=1e-3, digits=3)],
        "A ferromagnet's magnetisation precesses about the field; microwaves at the precession frequency are absorbed. "
        "Kittel's relation gives the resonance: f = (g muB/h) B for a sphere (the demagnetising fields cancel), and "
        "f = (g muB/h) sqrt(B (B + mu0 Ms)) for a film magnetised in plane, so f^2/B against B is a line whose intercept "
        "over slope is mu0 Ms. The field-modulated lock-in records the derivative of the absorption; its zero crossing is "
        "the resonance field and its peak-to-peak width grows with frequency as dBpp = dB0 + (2/sqrt3) alpha f/(g muB/h) "
        "(Gilbert damping alpha).",
        ["Place the sample in the shorted waveguide (or on the coplanar line) between the magnet poles.",
         "At each frequency sweep the field through the resonance with field modulation and the lock-in.",
         "Read the zero crossing (resonance field) and the peak-to-peak width.",
         "Fit f against B (sphere) or f^2/B against B (film); fit the width against f for alpha."],
        [_q("For a sphere the resonance is f = gamma B because", ["The demagnetising fields cancel", "Ms is zero",
            "The sphere is small"], 0, "Nx = Ny = Nz."),
         _q("The line width grows with frequency because of", ["Gilbert damping", "The magnet", "The lock-in"], 0,
            "The damping term is proportional to frequency.")],
        [SLICHTER, KITTEL, {"title": "C. Kittel, Phys. Rev. 73, 155 (1948): ferromagnetic resonance"},
         {"title": "YIG g = 2.00 and alpha about 5e-5; permalloy mu0 Ms about 1.0 T, g about 2.1, alpha about 0.008",
          "note": "quoted from memory - verify"}, ILLUS],
        "pk10t_fmr", MW, "Broadband FMR between electromagnet poles",
        "A coplanar waveguide between the poles of an electromagnet, a microwave generator and diode detector, field modulation coils and a lock-in.")


def esr() -> dict:
    return _mk(
        "pk10-esr", "pk10_esr", CH_MR, "ESR line shape, g-factor and hyperfine constant",
        "Record the X-band ESR derivative spectrum of DPPH with field modulation and find its g-factor and line width; "
        "with Mn2+ in MgO find the hyperfine constant. SIMULATED INSTRUMENT.",
        {"x": 330.0, "s": 0.0, "typ": 0.0, "g": 2.0036, "A": 0.0, "I": 0.0, "dBpp": 0.15},
        [knob("x", "Magnetic field", "x", 200, 500, 0.0001, 330, "mT"),
         knob("g", "This sample (its g-factor is hidden)", "g", 1.9, 2.1, 0.0001, 2.0036, hidden=True)],
        [inst("y", "readout", "First-derivative signal", "y", unit="arb.", lc=1e-3, digits=3)],
        "An unpaired electron in a field B has two levels g muB B apart; microwaves of frequency f are absorbed at "
        "h f = g muB B. With a small field modulation and a lock-in the spectrometer records the derivative of the "
        "absorption: each line's centre is the zero crossing between its positive and negative peaks, and its width "
        "is the peak-to-peak distance. A nucleus of spin I splits the line into 2I + 1 lines spaced by the hyperfine "
        "constant A; to second order B_m = B0 - A m - (A^2/2B0)(I(I+1) - m^2), so the outermost pair is exactly 2IA "
        "apart. g = h f/(muB B) from the centre of a single line.",
        ["Tune the cavity at X-band (9.5 GHz), set the microwave power low and the modulation below the line width.",
         "Sweep the field through the line(s), reading the lock-in.",
         "Find each zero crossing.",
         "g from h f/(muB B0); A from the outermost lines; the width from the peak-to-peak distance."],
        [_q("Mn2+ (I = 5/2) shows", ["Six hyperfine lines", "Two lines", "One line"], 0, "2I + 1 = 6."),
         _q("Field modulation makes the spectrometer record", ["The derivative of the absorption", "The absorption itself",
            "The dispersion only"], 0, "The lock-in detects at the modulation frequency.")],
        [SLICHTER, {"title": "A. Abragam and B. Bleaney, Electron Paramagnetic Resonance of Transition Ions (Oxford, 1970)"},
         {"title": "DPPH g = 2.0036; Mn2+ in MgO g = 2.0014, |A| = 81e-4 cm^-1 = 8.67 mT; malonic acid radical alpha-proton about 2.1 mT",
          "note": "quoted from memory - verify; line widths illustrative"}, ILLUS],
        "pk10t_esr", MW + " " + MAG, "X-band ESR spectrometer",
        "An X-band microwave bridge with a resonant cavity between electromagnet poles, the modulation coils and a lock-in.")


def positron() -> dict:
    return _mk(
        "pk10-positron", "pk10_pos", CH_MR, "Positron annihilation: lifetime and angular correlation",
        "With a Na-22 source sandwiched in aluminium, record the positron lifetime spectrum by fast-fast coincidence and the "
        "angular correlation of the annihilation photons; find the bulk lifetime and the Fermi cut-off. SIMULATED INSTRUMENT.",
        {"x": 0.0, "s": 0.0, "typ": 0.0},
        [knob("x", "Delay or angle", "x", -20, 20, 0.001, 0),
         knob("t1", "This sample (its positron lifetime is hidden)", "t1", 0.05, 1, 0.0001, 0.165, "ns", hidden=True)],
        [inst("y", "readout", "Counts", "y", unit="counts", lc=1, digits=0)],
        "Na-22 emits a positron and, within picoseconds, a 1274 keV gamma ray (the start). The positron thermalises in the "
        "sample and annihilates into two 511 keV photons (the stop). A fast-fast coincidence with BaF2 detectors records "
        "the delay; the spectrum is a sum of exponentials I_i/tau_i exp(-t/tau_i) convolved with the timing resolution. "
        "Far from the peak the resolution no longer matters and the slope of ln(counts - background) is -1/tau. A defect-"
        "free metal has one lifetime; a polymer shows a long ortho-positronium component (nanoseconds) whose lifetime "
        "measures the free volume. The two photons leave almost back to back: the small angle theta = p/(m c) carries "
        "the electron momentum, so a metal shows the free-electron parabola cut off at theta_F = hbar kF/(m c).",
        ["Sandwich the sealed Na-22 source between two pieces of the sample.",
         "Set the constant-fraction windows: start 1274 keV, stop 511 keV; calibrate the time scale.",
         "Accumulate the lifetime spectrum; read it channel by channel.",
         "Move the angular-correlation detector across the back-to-back direction and count coincidences."],
        [_q("The start signal of the lifetime measurement is", ["The 1274 keV gamma ray", "A 511 keV photon", "The clock"], 0,
            "It is emitted with the positron."),
         _q("A long-lived component in a polymer comes from", ["Ortho-positronium in free volume", "Free positrons in a metal",
            "The source"], 0, "o-Ps lives nanoseconds in a void.")],
        [KNOLL, {"title": "R. Krause-Rehberg and H. S. Leipner, Positron Annihilation in Semiconductors (Springer, 1999)"},
         {"title": "Aluminium bulk positron lifetime about 0.165 ns; o-Ps in polyethylene about 2.5 ns, intensity about 20 %",
          "note": "quoted from memory - verify; resolution and counts illustrative"}, ILLUS],
        "pk10t_pos", RAD, "Positron lifetime and angular-correlation table",
        "Two BaF2 detectors facing the source sandwich, constant-fraction discriminators and a time-to-amplitude converter, and a detector on an angular arm.")


# ================================================================================ magnetism + magneto-optics
def moke() -> dict:
    return _mk(
        "pk10-moke", "pk10_moke", CH_MG, "Magneto-optic Kerr effect hysteresis",
        "Record the longitudinal and polar MOKE loops of a cobalt film and its remanence against the in-plane angle: find "
        "the coercive field, the Kerr rotation and the easy axis. SIMULATED INSTRUMENT.",
        {"x": 0.0, "s": 0.0, "typ": 0.0},
        [knob("x", "Field or angle", "x", -4000, 4000, 0.001, 0),
         knob("Bc", "This film (its coercive field is hidden)", "Bc", 0.01, 50, 0.001, 2, "mT", hidden=True)],
        [inst("y", "readout", "Kerr rotation", "y", unit="mrad", lc=1e-5, digits=5)],
        "Linearly polarised light reflected from a magnetised surface turns its polarisation by a small Kerr angle "
        "proportional to the magnetisation component in the plane of incidence (longitudinal MOKE, in-plane field) or "
        "normal to the surface (polar MOKE). A balanced detector behind an analyser near extinction reads the rotation, "
        "so a field sweep draws the hysteresis loop; the coercive field is where each branch crosses zero, the Kerr "
        "rotation at saturation is the loop's height. The remanence after saturating along each in-plane direction maps "
        "the anisotropy: uniaxial gives |cos(phi - phi_E)|, cubic Fe(001) on MgO a fourfold pattern. Polar MOKE of an "
        "in-plane film is a hard-axis line saturating at mu0 Ms. The loop shape here is phenomenological.",
        ["Align the laser, polariser, sample (between the electromagnet poles) and analyser; set the analyser near extinction.",
         "Sweep the in-plane field down from +B and back up, reading the rotation.",
         "Saturate along each in-plane angle and read the remanent rotation.",
         "Turn the magnet for the polar geometry and sweep the out-of-plane field."],
        [_q("The coercive field is where", ["The Kerr rotation crosses zero on a branch", "The rotation is largest",
            "The field is zero"], 0, "The magnetisation averages to zero there."),
         _q("A fourfold remanence pattern shows", ["Cubic anisotropy", "No anisotropy", "A uniaxial easy axis"], 0,
            "Two equivalent easy axes at 90 degrees.")],
        [{"title": "H. Fujiwara, Spectroscopic Ellipsometry (Wiley, 2007): polarisation optics"},
         {"title": "Z. Q. Qiu and S. D. Bader, Rev. Sci. Instrum. 71, 1243 (2000): surface magneto-optic Kerr effect"},
         {"title": "Fe(001) easy axes along <100>; permalloy coercivity about 0.1 mT; mu0 Ms of Co about 1.8 T",
          "note": "quoted from memory - verify; loop widths and Kerr angles illustrative"}, ILLUS],
        "pk10t_hc", LASER + " " + ELEC, "Kerr bench with an electromagnet",
        "A laser, polariser, the film between electromagnet poles on a rotation stage, an analyser and a balanced photodetector with a lock-in.")


def vsm() -> dict:
    return _mk(
        "pk10-vsm", "pk10_mag", CH_MG, "Vibrating sample magnetometry: M-H loop and M-T",
        "Measure ferrite nanoparticles in a vibrating sample magnetometer: the room-temperature M-H loop for the saturation "
        "magnetisation, coercivity and anisotropy, and M-T in a field to the Curie temperature. SIMULATED INSTRUMENT.",
        {"x": 0.0, "s": 0.0, "typ": 3.0, "T0": 300.0, "Bm": 2.0, "Bf": 1.0, "Tc": 858.0, "Bc": 0.015, "Bw": 0.06,
         "ms0": 0.08, "chi": 1.0e-5, "mass": 1.0e-6, "lcm": 1.0e-6, "Thi": 900.0},
        [knob("x", "Field or temperature", "x", -3, 1000, 0.0001, 0),
         knob("ms0", "This powder (its saturation moment is hidden)", "ms0", 0.00001, 1, 0.00001, 0.08, "A m^2", hidden=True)],
        _y("Moment", "emu", 1e-6, 6),
        "The sample vibrates at a fixed frequency between pick-up coils in the magnet's field; the induced voltage is "
        "proportional to its moment. Sweeping the field down and back draws the M-H loop. At high field the moment "
        "approaches saturation on top of the holder's linear background, m = ms + chi B, so a line through the high-field "
        "points gives ms at its intercept; divided by the mass it is the saturation magnetisation (emu/g = A m^2/kg). "
        "The coercive field and the shape of the approach give the anisotropy. Heating in a field, ms(T) falls to zero "
        "at the Curie temperature; near Tc the mean-field form m^2 ~ (Tc - T) gives Tc as the intercept of m^2 against T.",
        ["Weigh the powder into the holder, fix it on the vibrating rod and centre it between the coils.",
         "At room temperature sweep the field from +2 T to -2 T and back.",
         "In the oven, apply the field and heat through the Curie temperature, reading the moment.",
         "Ms from the high-field intercept per gram; Tc from m^2 against T."],
        [_q("The holder's background is removed using", ["The slope of the high-field points", "The zero-field moment",
            "The coercive field"], 0, "Above saturation only the linear background still grows."),
         _q("Above the Curie temperature the spontaneous moment is", ["Zero", "Largest", "Negative"], 0,
            "The ferromagnet has become a paramagnet.")],
        [DU, KITTEL, {"title": "S. Foner, Rev. Sci. Instrum. 30, 548 (1959): vibrating sample magnetometer"},
         {"title": "Magnetite: Curie temperature about 858 K, bulk Ms about 92 emu/g; nanoparticles 60-80 emu/g",
          "note": "quoted from memory - verify; the film and its Tc are illustrative"}, ILLUS],
        "pk10t_mag", MAG + " The oven runs hot: let it cool before changing the sample.", "Vibrating sample magnetometer",
        "A VSM head above an electromagnet with pick-up coils, an oven insert, and the lock-in and gaussmeter rack.")


BUILDERS = (sc_tc, sc_jc, squid, dilution, heat_capacity, thermal_cond, qhe, sdh, hall_mob, seebeck, dlts, cv, haynes,
            solar, mossbauer, fmr, esr, positron, moke, vsm)
