"""Lab pack `phd_laser_w10`: Ph.D. laser spectroscopy, atomic physics, interferometry and quantum optics set-ups of
`syllabus/physics/phd.json` (wave 10). Physics: the `phd_laser_w10` kernel pack (`pl10_*`) and its JavaScript twin.

One studio rig, `pl10-laser-bench`, draws each set-up on an optical table (the Rb saturated-absorption bench, the
optical-pumping cell in its Helmholtz coils, the scanning monochromator with H / D / He lamps, the diode-laser mount,
the locked laser with its servo, the SHG crystal on a rotation stage, the z-scan rail, the TCSPC set, the pump-probe
delay line, the MOT and BEC vacuum chambers with their cameras, the Michelson interferometer, the HOM / CHSH / eraser
photon-counting tables) and walks one sweep per stage.

Every lab's check runs the kernel's own plan and fit (the same rows the rig records) against the textbook relation.
Photon-counting data is SIMULATED DATA from the lab's seed; the MOT and the BEC are simulated instruments and say so.
Constants written from memory are labelled "from memory - verify"; design values of a particular apparatus are
labelled illustrative. English only.
"""
from __future__ import annotations

from ..catalog import B, board, inst, knob, lab

RIG = "pl10-laser-bench"
LEVEL = "Ph.D."
GRP = "Physics · Lasers, Atoms and Quantum Optics"
CH_LAS = "Laser spectroscopy and atomic physics"
CH_INT = "Interferometry, quantum optics and photon statistics"
MEM = "from memory - verify"

MIT = {"title": "MIT Junior Lab (8.13/8.14) experiment guides: Doppler-Free Laser Spectroscopy, Optical Pumping of "
                "Rubidium Vapor, Optical Emission Spectra of Hydrogenic Atoms, Michelson Interferometer"}
FOOT = {"title": "C. J. Foot, Atomic Physics (Oxford, 2005): saturated absorption, laser stabilisation, laser cooling "
                 "and trapping, Bose-Einstein condensation"}
STECK = {"title": "D. A. Steck, Rubidium 87 D Line Data and Rubidium 85 D Line Data (steck.us/alkalidata)",
         "note": "87Rb F'3-F'2 266.650, F'2-F'1 156.947 MHz; 85Rb F'4-F'3 120.640, F'3-F'2 63.401 MHz; G 6.0666 MHz; "
                 "gJ 2.00233113; I = 3/2, 5/2; masses 86.909180527, 84.911789738 u; vapour pressure log10 P(torr) = "
                 "7.738 - 4215/T; line strengths approximate - " + MEM}
CODATA = {"title": "CODATA 2018 / SI 2019: h, kB, c, e exact; muB, mu0, u, me/mp = 1/1836.15267343, "
                   "md/mp = 1.99900750139, R_inf = 10973731.568160 1/m"}
LOUDON = {"title": "R. Loudon, The Quantum Theory of Light, 3rd ed. (OUP): photon counting, two-photon interference, "
                   "entanglement, single-photon interference"}
BOYD = {"title": "R. W. Boyd, Nonlinear Optics, 3rd ed.: second harmonic generation, phase matching, nonlinear refraction"}
SB = {"title": "M. Sheik-Bahae, A. A. Said, T.-H. Wei, D. J. Hagan and E. W. Van Stryland, IEEE J. Quantum Electron. 26, "
               "760 (1990): sensitive measurement of optical nonlinearities using a single beam",
      "note": "the on-axis closed-aperture and the open-aperture formulas used here; cited " + MEM}
SIM = {"title": "Hoola Prayogshala kernel pack phd_laser_w10",
       "note": "SIMULATED DATA: every reading comes from the simulation code and is checked against the textbook "
               "relation in Hoola's tests"}
ILLUS = {"title": "Illustrative apparatus values",
         "note": "powers, gains, efficiencies, count rates, cell and coil dimensions, servo gains and sample constants not "
                 "named in a source are chosen to be typical of a research laboratory; they are not properties of a "
                 "named device"}
LASER_SAFE = ("Class 3B laser light: wear goggles rated for the wavelength, keep the beams at table height and blocked "
              "at the ends, take off watches and rings, and never look along a beam.")
HV_SAFE = "The detector and lamp supplies are at high voltage: switch them off before touching a connection."


def _q(q, opts, ans, why):
    return {"q": q, "options": opts, "answer": ans, "why": why}


def _stat(tol: str, why: str) -> dict:
    return {"title": "About this lab's check", "note": f"Within {tol} of the exact relation. {why}"}


def _bodies(name: str, info: str) -> list[dict]:
    return [board(1.4, 0.7),
            B("main", "box", name=name, info=info, size=[0.6, 0.12, 0.3], pos=[-0.2, 0.06, -0.25], color="#3a3f47"),
            B("unit", "box", name="Instruments", info="The read-out and the recorder of the experiment.",
              size=[0.4, 0.12, 0.22], pos=[0.45, 0.06, -0.22], color="#2b2f36")]


def _mk(id, kernel, chapter, title, aim, params, knobs, insts, theory, steps, questions, sources, check, safety,
        name, info, tour):
    return lab(id=id, rig=RIG, title=title, group=GRP, level=LEVEL, topic=chapter, chapter=chapter, aim=aim,
               kernel=kernel, params=params, autorun=True, camera={"pos": [0.1, 0.9, 1.15], "look": [0.1, 0.1, -0.25]},
               floor=-0.03, bodies=_bodies(name, info), knobs=knobs, instruments=insts, steps=steps, theory=theory,
               safety=safety, tour=tour, questions=questions, sources=sources, check=check)


def _y(label, unit, lc, digits):
    return [inst("y", "readout", label, "y", unit=unit, lc=lc, digits=digits)]


# ================================================================================================ laser spectroscopy
def sat_abs() -> dict:
    return _mk(
        "pl10-sat-abs", "pl10_satabs", CH_LAS, "Doppler-free saturated absorption spectroscopy of rubidium",
        "Scan a 780 nm laser over the Rb D2 line through a natural Rb cell with counter-propagating pump and probe beams, "
        "find the Lamb dips and crossovers of 87Rb and 85Rb, measure the upper-level hyperfine splittings and estimate "
        "the natural line width from the dip width against pump power.",
        {"x": 0.0, "s": 0.0, "q": 0.0},
        [knob("x", "Scope cursor (frequency offset) or pump saturation", "x", -500, 50, 0.01, 0, "MHz"),
         knob("d87a", "This atom (the F'3-F'2 splitting is hidden)", "d87a", 200, 330, 0.001, 266.65, "MHz", hidden=True)],
        _y("Peak centre", "MHz", 0.01, 2),
        "In a vapour cell the D2 absorption is Doppler broadened to about 500 MHz, which hides the hyperfine structure of "
        "the upper level. A strong pump beam and a weak probe beam from the same laser cross the cell in opposite "
        "directions. Only atoms moving across the beams (v = 0) see both at the same frequency, so at each atomic "
        "resonance the pump saturates the atoms the probe would have used and the probe absorption drops: a narrow "
        "Lamb dip of about the natural width. Two transitions from the same lower level also give a CROSSOVER exactly "
        "half way between them, from the atoms whose Doppler shift puts the pump on one line and the probe on the other. "
        "Subtracting a reference probe that the pump does not cross removes the Doppler background. The dip width is "
        "the natural width G power broadened, G sqrt(1 + I/Isat), plus the laser line width: plotted against "
        "sqrt(1 + I/Isat) it is a straight line of slope G. The scan axis is calibrated with a Fabry-Perot etalon of "
        "known free spectral range, so the scope reads megahertz.",
        ["Lock nothing yet: set the laser current and temperature so the scan covers the 87Rb F = 2 group.",
         "Block the reference beam path difference: the scope shows the difference signal with six peaks.",
         "Put the cursor on each peak and press PEAK: the scope reads its centre. The tallest outer peak is F'= 3.",
         "Tune to the 85Rb F = 3 group and read its six peaks the same way.",
         "Back on the 87Rb F = 2 -> F' = 3 dip, read its width at six pump powers.",
         "Splittings are differences of peak centres; the crossovers sit half way between the lines they join."],
        [_q("A crossover resonance appears", ["Half way between two transitions that share a lower level",
            "At twice the frequency of a transition", "Only in a heated cell"], 0,
            "Atoms of one velocity class see the pump on one line and the probe on the other."),
         _q("Heating the cell changes", ["The size of the dips, not their positions or widths", "The hyperfine splittings",
            "The natural width"], 0, "More atoms absorb; the Doppler-free features stay where they are."),
         _q("The dip width extrapolated to zero pump power gives", ["The natural width plus the laser line width",
            "The Doppler width", "The hyperfine splitting"], 0, "Power broadening goes away as the pump goes to zero.")],
        [MIT, FOOT, STECK, CODATA, ILLUS, SIM,
         {"title": "About the line width", "note": "the neighbouring peaks' tails widen the measured dip by a few tenths of "
                                                   "a per cent, so the line-width result carries that systematic"}],
        {"reading": "res", "textbook": "pl10_sat", "tol": 0.01}, LASER_SAFE + " The cell heater is hot when it is on.",
        "Saturated-absorption bench", "A 780 nm diode laser, a thick glass plate making pump and two probe beams, the Rb "
        "cell in its heater and magnetic shield, and a balanced pair of photodiodes.",
        [{"say": "The diode laser, the beam-splitting plate, the rubidium cell in its shield and the two photodiodes."}])


def optical_pumping() -> dict:
    return _mk(
        "pl10-optical-pumping", "pl10_oppump", CH_LAS, "Optical pumping of rubidium",
        "Pump natural Rb vapour with circularly polarised D1 light, find the RF resonances of 85Rb and 87Rb against the "
        "Helmholtz coil current at several frequencies with the field forward and reversed, and work out gF, the "
        "nuclear spins, the Earth's horizontal field and the pumping time.",
        {"x": 1000.0, "s": 0.0, "q": 0.0},
        [knob("x", "RF frequency or time after unblocking", "x", 0, 2000, 1, 1000, "kHz"),
         knob("I85", "This atom (the nuclear spin of 85Rb is hidden)", "I85", 0.5, 4.5, 0.5, 2.5, hidden=True)],
        [inst("y", "readout", "87Rb resonance current", "y", unit="mA", lc=0.01, digits=2)],
        "Circularly polarised D1 light can only raise mF by one, so the atoms pile up in the sublevel with the largest "
        "mF, which cannot absorb: the cell becomes more transparent. That is optical pumping. A radio-frequency field "
        "at h f = gF muB B moves atoms back out and the transmitted light dips. For an alkali ground state (J = 1/2) and "
        "F = I + 1/2, gF = gJ / (2 I + 1), so the resonance field of each isotope tells its nuclear spin. The field is "
        "the Helmholtz pair's k I, k = (4/5)^(3/2) mu0 N / R, plus the horizontal Earth's field along the axis; "
        "reversing the current makes the Earth's field subtract instead of add, so half the difference of the two "
        "intercepts is the Earth's field. At these fields the quadratic Zeeman shift (Breit-Rabi) is a few tens of "
        "hertz and is left out. When the pumping light is unblocked, the transmission rises to its pumped value "
        "exponentially with the pumping time.",
        ["Warm the cell to about 45 C and let the lamp settle; align the axis of the coils north-south.",
         "At each RF frequency sweep the coil current and note the current of the 87Rb and the 85Rb dips.",
         "Reverse the coil current and repeat at the same frequencies.",
         "Plot current against frequency: the slopes give gF of each isotope, the intercepts the Earth's field.",
         "Block and unblock the pumping light and read the transmitted signal against time: the rise gives the pumping time."],
        [_q("The 85Rb resonance needs a larger field than 87Rb at the same frequency because", ["Its gF is smaller (1/3)",
            "It is heavier", "Its lamp is weaker"], 0, "gF = gJ/(2I + 1) with I = 5/2."),
         _q("Reversing the coil current", ["Makes the Earth's field subtract instead of add", "Changes gF",
            "Doubles the resonance frequency"], 0, "Only the coil field changes sign.")],
        [MIT, FOOT, STECK, CODATA, ILLUS, SIM,
         {"title": "Helmholtz coils (illustrative)", "note": "135 turns of radius 0.275 m; the Earth's horizontal field of "
                                                             "36 microtesla is this laboratory's illustrative value"}],
        {"reading": "res", "textbook": "pl10_pump", "tol": 0.01}, HV_SAFE + " The RF coil and the cell heater are live.",
        "Optical pumping cell in Helmholtz coils", "An Rb discharge lamp, a D1 filter and circular polariser, the heated "
        "cell inside a large Helmholtz pair with an RF coil, and a photodiode.",
        [{"say": "The rubidium lamp, the filter and polariser, the cell between the big Helmholtz coils, and the photodiode."}])


def hd_isotope() -> dict:
    return _mk(
        "pl10-hd-isotope", "pl10_hdshift", CH_LAS, "Balmer lines of hydrogen and deuterium: Rydberg constant and isotope shift",
        "Calibrate a scanning monochromator with the helium lamp, measure the Balmer lines of the hydrogen and the "
        "deuterium lamps, find the Rydberg constant for hydrogen and, from the H / D isotope shift, the deuteron to "
        "proton mass ratio.",
        {"x": 0.0, "s": 0.0, "q": 0.0},
        [knob("x", "Lamp line", "x", 0, 6, 1, 0),
         knob("rd", "This nucleus (the deuteron/proton mass ratio is hidden)", "rd", 1.5, 2.5, 0.00001, 1.99900750139, hidden=True)],
        _y("Counter reading", "nm", 0.0002, 4),
        "In the Bohr model with a nucleus of finite mass M the electron's reduced mass gives R_M = R_inf / (1 + me/M). "
        "The Balmer lines obey 1/lam = R_M (1/4 - 1/n^2) (vacuum wavelengths). Deuterium's heavier nucleus makes R_D "
        "slightly larger, so every D line is about 0.027 % shorter than its H line: 0.18 nm at H-alpha. The counter of "
        "the monochromator is first calibrated against helium lines of known wavelength; the air wavelengths are turned "
        "into vacuum wavelengths with the refractive index of air. From R_H and R_D, (1 + me/mp) R_H / R_D - 1 = me/md, "
        "and with me/mp known the mass ratio md/mp follows.",
        ["Put the helium lamp at the slit and read the counter at the centre of each of five He lines.",
         "Replace it with the hydrogen lamp and read H-alpha to H-delta (n = 3 to 6).",
         "Replace it with the deuterium lamp and read the same four lines.",
         "Fit the helium calibration, convert every reading to a vacuum wavelength.",
         "Fit 1/lam against (1/4 - 1/n^2) through the origin for each lamp; compare R_H and R_D."],
        [_q("The D lines are shorter than the H lines because", ["The deuteron's larger mass raises the reduced mass",
            "Deuterium has two electrons", "The lamp is hotter"], 0, "R_M = R_inf/(1 + me/M)."),
         _q("The helium lamp is used to", ["Calibrate the monochromator's counter", "Excite the hydrogen", "Measure R_inf"],
            0, "Its lines have known wavelengths.")],
        [MIT, CODATA, {"title": "NIST Atomic Spectra Database, He I lines in air: 447.1479, 501.5678, 587.5621, 667.8151, "
                                "706.5188 nm; refractive index of air 1.000277 (average over the visible)", "note": MEM},
         ILLUS, SIM, _stat("2 %", "The mass ratio rests on a 0.03 % shift read to 0.0002 nm; the Rydberg constant is "
                                  "within 0.001 %.")],
        {"reading": "res", "textbook": "pl10_ryd", "tol": 0.02}, HV_SAFE + " The discharge lamps get hot.",
        "Scanning monochromator", "A 1 m scanning grating monochromator with a photomultiplier and a wavelength counter, "
        "and the helium, hydrogen and deuterium discharge lamps.",
        [{"say": "The lamp at the entrance slit, the 1 m monochromator with its counter, and the photomultiplier at the exit."}])


def diode_laser() -> dict:
    return _mk(
        "pl10-diode-laser", "pl10_diodelaser", CH_LAS, "Diode laser threshold, slope efficiency and tuning",
        "Measure the light-current curve of a 780 nm diode laser at 25 C, find its threshold current and slope "
        "efficiency, and measure how its wavelength tunes with the drive current and the case temperature; compare the "
        "curve with the steady state of the laser rate equations.",
        {"x": 0.0, "s": 0.0, "q": 0.0},
        [knob("x", "Drive current or case temperature", "x", 0, 120, 0.1, 0, "mA"),
         knob("Ith", "This diode (its threshold is hidden)", "Ith", 5, 80, 0.01, 32.5, "mA", hidden=True)],
        _y("Reading", "mW or nm", 0.0001, 4),
        "The rate equations for the carrier number and the photon number in a laser diode have a steady state with a "
        "threshold: below it the light is spontaneous emission (a small fraction beta of it goes into the lasing mode), "
        "above it the carrier density clamps and every extra electron makes a photon, so P = eta (I - Ith) with eta the "
        "slope efficiency. With beta included the normalised photon number is s = ((r - 1) + sqrt((r - 1)^2 + "
        "4 beta r)) / 2 with r = I / Ith: a soft knee that becomes the straight line well above threshold. The "
        "threshold rises with temperature as exp((T - T_ref)/T0). The wavelength follows the gain peak and the cavity "
        "index: it tunes by a few picometres per milliampere (heating by the current) and by about a quarter of a "
        "nanometre per kelvin of the case; real diodes also hop between modes, averaged out here.",
        ["Set the temperature controller to 25 C. Raise the current in 5 mA steps from zero and read the power meter.",
         "Fit a straight line to the points well above the knee: its intercept is the threshold, its slope eta.",
         "With the wavemeter, read the wavelength at currents 20 mA either side of the operating point.",
         "Hold the current and read the wavelength as the case temperature goes from 15 C to 35 C.",
         "The slopes are the current and temperature tuning rates."],
        [_q("Above threshold the output power rises", ["Linearly with current", "As the square of the current",
            "Exponentially"], 0, "The carrier density is clamped."),
         _q("Warming the diode", ["Raises the threshold and lengthens the wavelength", "Lowers the threshold",
            "Does nothing to the wavelength"], 0, "The gain falls and the gain peak moves to the red.")],
        [FOOT, {"title": "L. A. Coldren, S. W. Corzine and M. L. Masanovic, Diode Lasers and Photonic Integrated "
                         "Circuits, 2nd ed. (Wiley): rate equations and the light-current curve"},
         ILLUS, SIM, {"title": "This diode (illustrative)", "note": "threshold 32.5 mA, 0.82 W/A, 6.5 pm/mA, 0.27 nm/K, "
                                                                     "T0 = 60 K and beta = 1e-4 are typical design values"}],
        {"reading": "res", "textbook": "pl10_diode", "tol": 0.01}, LASER_SAFE + " Never exceed the diode's maximum current.",
        "Diode laser on a temperature-controlled mount", "A diode laser in a Peltier-cooled mount with its collimating "
        "lens, a power meter head and a fibre-coupled wavemeter.",
        [{"say": "The diode in its temperature-controlled mount, the power meter and the wavemeter."}])


def freq_lock() -> dict:
    return _mk(
        "pl10-freq-lock", "pl10_freqlock", CH_LAS, "Laser frequency locking to a rubidium line",
        "Lock a diode laser to a Rb saturated-absorption dip, on the side of the fringe and with a dither and lock-in; "
        "measure the discriminator slope, the lock bandwidth from the suppression of an injected disturbance, and the "
        "residual frequency noise against an independent reference.",
        {"x": 0.0, "s": 0.0, "q": 0.0, "m": 0.0},
        [knob("x", "Detuning, disturbance frequency or measurement band", "x", -1, 300000, 0.01, 0),
         knob("Ki", "This servo (its integrator gain is hidden)", "Ki", 1e4, 1e6, 100, 3e5, hidden=True)],
        _y("Reading", "", 0.0001, 4),
        "A lock needs a DISCRIMINATOR: a signal that is zero at the wanted frequency and changes sign either side. On the "
        "side of a fringe the absorption signal minus half its height does that, with slope Hd/Gd at the half-height "
        "point, but any change of laser power moves the lock point. A dither lock modulates the frequency slightly and "
        "demodulates with a lock-in: the output is the derivative of the line, zero at its centre, slope 8 a Hd / Gd^2, "
        "and insensitive to power. An integrating servo with gain Ki then corrects the laser; the loop gain falls as "
        "fu/f, so disturbances below the unity-gain frequency fu = D Ki are suppressed by f/sqrt(f^2 + fu^2) and those "
        "above it pass. Plotting 1/S^2 against 1/f^2 gives a straight line of slope fu^2. White free-running frequency "
        "noise leaves sigma^2 = S0 (B - fu atan(B/fu)) in a band B; on the side of the fringe, intensity noise is "
        "written onto the frequency inside the loop band as well.",
        ["Scan the laser slowly over the dip and read the error signal at five detunings round the lock point: the slope D.",
         "Close the loop. Modulate the laser current at frequencies from 1 kHz to 300 kHz and read how much of the "
        "modulation is left: the suppression.",
         "Fit 1/S^2 against 1/f^2: the square root of the slope is the lock bandwidth.",
         "Beat the locked laser against a second, independent locked laser and read the rms frequency noise in 1, 10 and "
        "100 kHz bands."],
        [_q("A dither (lock-in) lock is better than a side-of-fringe lock because", ["It locks to the line centre and "
            "ignores power changes", "It needs no laser", "It has no bandwidth"], 0, "The derivative is zero at the centre."),
         _q("Above the unity-gain frequency the servo", ["Can no longer suppress noise", "Doubles the noise",
            "Removes all noise"], 0, "The loop gain is below one there.")],
        [FOOT, {"title": "E. D. Black, Am. J. Phys. 69, 79 (2001) and the standard servo theory of a first-order integrator "
                         "loop", "note": MEM},
         ILLUS, SIM],
        {"reading": "res", "textbook": "pl10_lock", "tol": 0.01}, LASER_SAFE,
        "Locked laser with its servo", "The diode laser, a small saturated-absorption set-up for the discriminator, a "
        "lock-in amplifier, the servo (PI controller) and a beat-note photodiode.",
        [{"say": "The laser, its own saturated-absorption reference, the lock-in and servo, and the beat-note detector."}])


def shg() -> dict:
    return _mk(
        "pl10-shg", "pl10_shg", CH_LAS, "Second harmonic generation and phase matching in BBO",
        "Double a 1064 nm laser in a beta-barium borate (BBO) crystal: show that the green power grows as the square of "
        "the infrared power, then tilt the crystal through phase matching and find the type-I phase-matching angle.",
        {"x": 0.0, "s": 0.0, "q": 1.0},
        [knob("x", "Infrared power or crystal tilt", "x", -5, 5, 0.001, 0),
         knob("thc", "This crystal's cut angle (hidden)", "thc", 10, 60, 0.01, 22.5, "deg", hidden=True)],
        _y("Green power", "mW", 0.0001, 4),
        "A non-centrosymmetric crystal driven by a strong field at w radiates at 2w through its second-order "
        "susceptibility, so the green power grows as P^2 while the pump is not depleted. The 2w wave generated at each "
        "point adds up along the crystal only if it keeps in step with the driving polarisation: dk = k(2w) - 2 k(w) "
        "must be near zero, and P2 ~ sinc^2(dk L / 2). In a negative uniaxial crystal (BBO, KDP) an ordinary wave at w "
        "can drive an extraordinary wave at 2w with n_e(2w, theta) = n_o(w) at one angle theta to the optic axis "
        "(type-I, ooe): sin^2 theta = (n_o(w)^-2 - n_o(2w)^-2)/(n_e(2w)^-2 - n_o(2w)^-2). The indices come from the "
        "crystal's Sellmeier equations. Tilting the crystal by an external angle turns the internal angle by the "
        "refracted amount, theta = theta_cut + asin(sin(tilt)/n_o).",
        ["Set the crystal at the peak of the green light and read the green power at six infrared powers.",
         "Plot log P2 against log P: the slope should be 2.",
         "At 2 W of infrared, tilt the crystal in 0.02 degree steps through the peak and read the green power.",
         "The centre of the sinc^2 curve (half-height midpoint) is the phase-matching tilt; add the cut angle and the "
         "refraction to get the internal angle."],
        [_q("Why does the green power depend on the crystal angle?", ["The phase mismatch dk changes with the angle",
            "The crystal gets thicker", "The laser changes colour"], 0, "Only near dk = 0 do the contributions add."),
         _q("Doubling the infrared power multiplies the green power by", ["4", "2", "8"], 0, "P2 ~ P^2.")],
        [BOYD, {"title": "Sellmeier equations: BBO (Eimerl et al. 1987 form) n_o^2 = 2.7359 + 0.01878/(l^2 - 0.01822) - "
                         "0.01354 l^2, n_e^2 = 2.3753 + 0.01224/(l^2 - 0.01667) - 0.01516 l^2; KDP (Zernike 1964 form)",
                "note": "coefficients written " + MEM},
         ILLUS, SIM],
        {"reading": "res", "textbook": "pl10_shgpm", "tol": 0.01}, LASER_SAFE + " 1064 nm is invisible: use the IR viewer.",
        "SHG crystal on a rotation stage", "A 1064 nm laser, a half-wave plate and polariser to set the power, a focusing "
        "lens, the crystal on a fine rotation stage, an IR-blocking filter and a power meter.",
        [{"say": "The infrared laser, the power control, the lens, the crystal on its rotation stage and the green power meter."}])


def z_scan() -> dict:
    return _mk(
        "pl10-z-scan", "pl10_zscan", CH_LAS, "Z-scan: nonlinear refraction of carbon disulphide",
        "Move a 1 mm cell of carbon disulphide through the focus of a picosecond 532 nm beam and record the open- and "
        "closed-aperture transmission together; find the nonlinear refractive index n2 (and, where the sample absorbs, "
        "the two-photon absorption coefficient).",
        {"x": 0.0, "s": 0.0, "q": 0.0},
        [knob("x", "Sample position z", "x", -20, 20, 0.1, 0, "mm"),
         knob("n2", "This sample (its n2 is hidden)", "n2", -50, 50, 0.001, 3, "x 1e-18 m²/W", 1e-18, hidden=True)],
        [inst("y", "readout", "Normalised transmission", "y", lc=0.0001, digits=4)],
        "A Gaussian beam of waist w0 focused through a thin sample changes the sample's index by n2 I: the sample "
        "becomes a weak lens whose strength follows the intensity, strongest at the focus. A small aperture in the far "
        "field then sees the transmission rise and fall as the sample moves through the focus: for small phase shifts "
        "T(x) = 1 + 4 dPhi x / ((x^2 + 9)(x^2 + 1)), x = z/z0, with a peak-valley shape whose sign tells the sign of n2 "
        "(Sheik-Bahae et al. 1990). dPhi = k n2 I0 Leff. With the aperture removed (open aperture) only absorption "
        "is seen: two-photon absorption gives T(x) = sum_m (-q0)^m / ((m+1)^1.5 (1 + x^2)^m), q0 = beta I0 Leff. "
        "Both detectors read together and dividing the closed trace by the open one removes the absorption (the usual "
        "product approximation).",
        ["Measure the beam waist (here 20 micrometre, so z0 = pi w0^2 / lambda is 2.36 mm) and the peak intensity.",
         "Move the sample from -14 mm to +14 mm through the focus and read the open-aperture detector.",
         "Repeat with the aperture in place, reading both detectors at every position.",
         "Fit the open trace for q0 (and beta); divide the closed by the open trace and fit dPhi, then n2."],
        [_q("A closed-aperture trace with a valley before the focus and a peak after it means", ["n2 is positive (self-"
            "focusing)", "n2 is negative", "There is no nonlinearity"], 0, "Sheik-Bahae's sign rule."),
         _q("The open-aperture trace is flat when", ["The sample has no nonlinear absorption", "n2 is large",
            "The beam is defocused"], 0, "Without the aperture refraction is not seen.")],
        [BOYD, SB, ILLUS, SIM,
         {"title": "Sample constants", "note": "carbon disulphide n2 about 3e-18 m^2/W for picosecond pulses at 532 nm, no "
                                               "two-photon absorption - " + MEM + "; the dye and the colloid variants use "
                                               "illustrative values, not those of a named compound"}],
        {"reading": "res", "textbook": "pl10_nl", "tol": 0.01}, LASER_SAFE + " CS2 is toxic and very flammable: sealed cell only.",
        "Z-scan rail", "A picosecond 532 nm laser, a focusing lens, the sample cell on a motorised rail, a beam splitter, "
        "an open detector and a detector behind a small far-field aperture.",
        [{"say": "The laser, the lens, the cell on its motorised rail through the focus, and the open and closed detectors."}])


def tcspc() -> dict:
    return _mk(
        "pl10-tcspc", "pl10_tcspc", CH_INT, "Fluorescence lifetime by time-correlated single photon counting",
        "Excite rhodamine 6G with a picosecond pulsed diode laser, build the histogram of photon arrival times with a "
        "TCSPC module, take off the background and fit the decay for the fluorescence lifetime. SIMULATED DATA.",
        {"x": 0.0, "s": 0.0, "q": 0.0},
        [knob("x", "Histogram bin start", "x", 0, 200, 0.01, 0, "ns"),
         knob("t1", "This sample (its lifetime is hidden)", "t1", 0.1, 100, 0.001, 4.08, "ns", hidden=True)],
        [inst("y", "readout", "Counts in the bin", "y", lc=1, digits=0)],
        "At each laser pulse at most one fluorescence photon is detected (the count rate is kept to a few per cent of "
        "the pulse rate), and the module measures the time between the pulse and that photon. Repeated millions of "
        "times, the histogram of these times IS the decay curve: counts proportional to exp(-t/tau), convolved with "
        "the instrument response (the laser pulse and the detector jitter), on a flat background of dark counts. "
        "After the response has passed, ln(counts - background) falls linearly with slope -1/tau (fitted with weights, "
        "because the counts are Poisson). A sample with two emitting species (quantum dots of several sizes or "
        "surface states) needs a two-exponential least-squares fit. The counts here are Poisson draws: SIMULATED DATA.",
        ["Record the instrument response with a scattering solution; it is about 0.1 ns wide.",
         "Put the sample in and collect until the peak bin holds about 2 x 10^5 counts.",
         "Read the counts in bins across the whole histogram, including the bins before the pulse (the background).",
         "Fit the decay after the response has passed."],
        [_q("Why must the detection rate be kept far below the pulse rate?", ["Otherwise early photons are favoured "
            "(pile-up)", "The laser would overheat", "The background rises"], 0, "Only the first photon of a pulse is timed."),
         _q("The background is found from", ["The bins before the excitation pulse", "The peak bin", "The last bin only"],
            0, "No fluorescence arrives before the pulse.")],
        [LOUDON, {"title": "W. Becker, Advanced Time-Correlated Single Photon Counting Techniques (Springer, 2005)"},
         {"title": "Sample lifetimes", "note": "rhodamine 6G about 4.1 ns in water / ethanol, ruby R line about 3 ms at room "
                                               "temperature - " + MEM + "; the quantum-dot components are illustrative"},
         ILLUS, SIM, _stat("2 %", "The counts are Poisson: the lifetime carries a statistical scatter of a few tenths of a "
                                  "per cent, the two-component fit about 1 %.")],
        {"reading": "res", "textbook": "pl10_life", "tol": 0.02}, LASER_SAFE + " " + HV_SAFE,
        "TCSPC set-up", "A picosecond pulsed diode laser, the cuvette holder, a monochromator, a single-photon detector and "
        "the TCSPC timing module.",
        [{"say": "The pulsed laser, the cuvette, the emission monochromator, the photon detector and the timing module."}])


def pump_probe() -> dict:
    return _mk(
        "pl10-pump-probe", "pl10_pumpprobe", CH_LAS, "Pump-probe transient absorption of a semiconductor film",
        "Excite a semiconductor film with a femtosecond pump pulse, probe its transmission with a delayed weak pulse from "
        "the same laser, scan the delay line for the carrier relaxation time, and record the transient bleach spectrum.",
        {"x": 25.0, "s": 0.0, "q": 0.0},
        [knob("x", "Delay stage position or probe wavelength", "x", 0, 1000, 0.0001, 25, "mm"),
         knob("tc", "This sample (its relaxation time is hidden)", "tc", 0.05, 100, 0.001, 1.6, "ps", hidden=True)],
        [inst("y", "readout", "dT/T x 1000", "y", lc=0.001, digits=3)],
        "The pump excites carriers; while they are there the film absorbs less at the probe wavelength (band filling: "
        "the BLEACH), so the probe transmission rises by dT/T. The probe is delayed by a retro-reflector on a stage: "
        "moving it by x adds 2x/c of delay (6.67 ps per millimetre). As the carriers relax, the bleach decays as "
        "exp(-t/tc); the measured curve is that decay convolved with the pump-probe cross-correlation, so after a few "
        "pulse widths ln(dT/T) falls linearly with slope -1/tc. At a fixed delay, scanning the probe wavelength gives "
        "the transient spectrum: the bleach peaks where the excited carriers fill the states.",
        ["Find zero delay (the half-rise of the signal) with the probe at 870 nm.",
         "Step the delay stage in 0.06 mm steps (0.4 ps) from just before zero delay to about 9 ps and read dT/T.",
         "Fit the tail: the relaxation time is -1/slope of ln(dT/T) against the delay.",
         "At 0.5 ps delay scan the probe wavelength across the band and find the bleach peak."],
        [_q("Moving the retro-reflector by 1 mm changes the delay by", ["6.67 ps", "3.33 ps", "1 ns"], 0, "Twice the travel at c."),
         _q("The signal rises over about", ["The pump-probe cross-correlation time", "The relaxation time", "A nanosecond"],
            0, "The rise is set by the pulses.")],
        [{"title": "J. Shah, Ultrafast Spectroscopy of Semiconductors and Semiconductor Nanostructures, 2nd ed. (Springer)"},
         ILLUS, SIM, {"title": "The samples", "note": "relaxation times, bleach peaks and band widths of the film and of the "
                                                     "dye are illustrative, not those of a named material"}],
        {"reading": "res", "textbook": "pl10_relax", "tol": 0.01}, LASER_SAFE + " Femtosecond pulses burn at very low average power.",
        "Pump-probe delay line", "A femtosecond laser, a beam splitter, the pump chopper, a retro-reflector on a motorised "
        "delay stage, the sample, and a probe photodiode with a lock-in.",
        [{"say": "The femtosecond laser, the pump and probe arms, the retro-reflector on its delay stage and the sample."}])


def mot() -> dict:
    return _mk(
        "pl10-mot", "pl10_mot", CH_LAS, "Magneto-optical trap of rubidium (simulated instrument)",
        "Trap rubidium-87 atoms from the background vapour in a magneto-optical trap, count them from their fluorescence, "
        "measure the cloud temperature by time of flight and the capture velocity from the loading curve. SIMULATED "
        "INSTRUMENT: the readings come from a model of a typical student MOT.",
        {"x": 1.0, "s": 0.0, "q": 0.0},
        [knob("x", "Reading number, flight time or loading time", "x", 0, 20, 0.01, 1),
         knob("vc", "This trap (its capture velocity is hidden)", "vc", 5, 60, 0.001, 25, "m/s", hidden=True)],
        _y("Reading", "V or mm", 0.0001, 4),
        "Six red-detuned beams in a quadrupole field slow and push atoms to the centre. Each trapped atom scatters "
        "R = (G/2) s / (1 + s + 4 (det/G)^2) photons a second; a lens catching the fraction eta of them on a calibrated "
        "photodiode gives the atom number N = V / (R h nu eta resp Rf). Switch the trap off and let the cloud fall and "
        "spread for a time t, then image it: sigma^2 = sigma0^2 + kB T t^2 / m, so the slope of sigma^2 against t^2 "
        "gives T. Atoms from the vapour slower than the capture velocity vc are caught: the loading rate is "
        "R = (1/2) n A vc^4 (m / 2 kB T_room)^(3/2) (Monroe et al. 1990), and the trap fills as N(t) = R tau (1 - "
        "exp(-t/tau)), so the loading curve gives R, tau and then vc.",
        ["With the trap loaded, read the fluorescence photodiode three times.",
         "Switch the trap off for 2 to 12 ms and image the falling cloud; read its rms size.",
         "Switch the quadrupole field off to empty the trap, then on, and read the fluorescence at times from 0.1 to 15 s.",
         "N from the fluorescence, T from the slope of sigma^2 against t^2, vc from the loading rate."],
        [_q("Time of flight measures the temperature because", ["The cloud spreads at its thermal speed",
            "The atoms fall faster when hot", "The fluorescence changes colour"], 0, "sigma^2 grows as kB T t^2 / m."),
         _q("The loading rate depends on the capture velocity as", ["vc^4", "vc", "vc^2"], 0, "Monroe et al. 1990.")],
        [FOOT, {"title": "C. Monroe, W. Swann, H. Robinson and C. Wieman, Phys. Rev. Lett. 65, 1571 (1990): very cold trapped "
                         "atoms in a vapor cell", "note": "the loading-rate formula is cited " + MEM},
         STECK, CODATA, ILLUS, SIM],
        {"reading": "res", "textbook": "pl10_motq", "tol": 0.01}, LASER_SAFE + " The vacuum chamber is under ultra-high vacuum.",
        "MOT vacuum chamber", "A glass vacuum cell with a rubidium dispenser, six circularly polarised beams, the anti-"
        "Helmholtz coils, a fluorescence photodiode and an imaging camera.",
        [{"say": "The vacuum cell, the six trapping beams, the quadrupole coils, the photodiode and the camera."}])


def bec() -> dict:
    return _mk(
        "pl10-bec", "pl10_bec", CH_LAS, "Bose-Einstein condensation of rubidium (simulated instrument)",
        "Evaporate Rb-87 in a magnetic trap to lower temperatures, fit each time-of-flight image with the bimodal (thermal "
        "plus Thomas-Fermi) profile, follow the condensate fraction against T and find the critical temperature. "
        "SIMULATED INSTRUMENT: ideal-Bose-gas model.",
        {"x": 30.0, "s": 0.0, "q": 0.0},
        [knob("x", "Final RF frequency above the trap bottom", "x", 1, 200, 0.1, 30, "kHz"),
         knob("fz", "This trap (its axial frequency is hidden)", "fz", 10, 500, 0.1, 120, "Hz", hidden=True)],
        [inst("y", "readout", "Temperature from the wings", "y", unit="nK", lc=0.1, digits=1)],
        "In a harmonic trap of mean frequency wbar an ideal Bose gas of N atoms condenses below kB Tc = zeta(3)^(-1/3) "
        "hbar wbar N^(1/3) = 0.94 hbar wbar N^(1/3); below Tc the condensed fraction is 1 - (T/Tc)^3. Forced RF "
        "evaporation removes the hottest atoms and the rest re-thermalise colder. After release the thermal atoms spread "
        "as a Gaussian set by T, while the condensate, a Thomas-Fermi parabola (the solution of the Gross-Pitaevskii "
        "equation when the interaction energy dominates), stays narrow: the bimodal profile. Fitting both parts gives T "
        "(from the wings), N and N0/N. For each shot below Tc, Tc = T / (1 - N0/N)^(1/3); scaled to a common atom number "
        "these must agree with the formula. The evaporation trajectory (how T and N fall together) is illustrative.",
        ["Load the magnetic trap and evaporate to 60 kHz above the trap bottom; release and image.",
         "Fit the image with the bimodal profile and read T, N and the condensate fraction.",
         "Repeat for final frequencies down to 18 kHz.",
         "For every shot with a condensate, work out Tc and scale it to 10^6 atoms."],
        [_q("The condensate shows up in time of flight as", ["A narrow dense peak on a broad thermal cloud",
            "A ring", "A uniform cloud"], 0, "The bimodal profile."),
         _q("Below Tc in a harmonic trap the thermal fraction is", ["(T/Tc)^3", "T/Tc", "(T/Tc)^1.5"], 0,
            "The density of states of a 3-D harmonic trap.")],
        [FOOT, {"title": "C. J. Pethick and H. Smith, Bose-Einstein Condensation in Dilute Gases (CUP): Tc in a harmonic "
                         "trap, the Thomas-Fermi profile"}, CODATA, ILLUS, SIM],
        {"reading": "res", "textbook": "pl10_tc", "tol": 0.01}, LASER_SAFE + " The trap coils carry large currents.",
        "BEC apparatus", "A double MOT vacuum system, the magnetic trap coils, the RF evaporation antenna and the "
        "absorption-imaging camera.",
        [{"say": "The ultra-high vacuum chamber, the magnetic trap coils, the RF antenna and the imaging camera."}])


# ================================================================================================ interferometry
def michelson() -> dict:
    return _mk(
        "pl10-michelson", "pl10_michmetro", CH_INT, "Michelson interferometric displacement, coherence length and line width",
        "Use a Michelson interferometer three ways: count He-Ne fringes with a photodiode to measure a displacement, scan "
        "the path difference with an LED (white-light coherence scan) to measure its coherence length, and follow the "
        "beats of the sodium D lines to find the line width of the sodium lamp.",
        {"x": 0.0, "s": 0.0, "q": 0.0},
        [knob("x", "Mirror travel or path difference", "x", 0, 200000, 0.01, 0, "um"),
         knob("cal", "This micrometer (its real travel per division is hidden)", "cal", 0.9, 1.1, 0.0001, 1.0237, hidden=True)],
        _y("Reading", "", 0.001, 3),
        "Moving one mirror by d changes the path difference by 2d, so one fringe passes the photodiode for every lam/2 "
        "of travel: d = N lam / 2, as good as the count of whole fringes. With a broad source the fringes only appear "
        "near zero path difference: the visibility is the Fourier transform of the spectrum, so a Gaussian line of width "
        "dlam gives a Gaussian envelope whose FWHM in path difference is the coherence length 4 ln2 lam^2 / (pi dlam). "
        "A sodium lamp has two lines 0.6 nm apart: the fringes beat, vanishing every 0.29 mm of path difference and "
        "returning every 0.58 mm; the beat maxima slowly fade with the line width dnu, as exp(-(pi dnu x/c)^2/(4 ln2)) "
        "for Doppler-shaped lines.",
        ["He-Ne: zero the counter, turn the micrometer by 20, 40, 60, 80 and 100 micrometres and read the fringe count.",
         "LED: find zero path difference, then step the mirror and read the fringe visibility out to 24 micrometres.",
         "Sodium: read the visibility at the beat maxima, every 50 beats out to 17 cm of path difference.",
         "Displacement = N lam/2; coherence length = FWHM of the envelope; sodium line width from ln V against x^2."],
        [_q("One fringe passes when the mirror moves", ["Half a wavelength", "One wavelength", "A quarter wavelength"], 0,
            "The path changes by twice the travel."),
         _q("The sodium fringes vanish periodically because", ["The two D lines beat", "The lamp flickers",
            "The mirror tilts"], 0, "Their fringe patterns go in and out of step.")],
        [MIT, {"title": "M. Born and E. Wolf, Principles of Optics: coherence and visibility"},
         {"title": "Wavelengths", "note": "He-Ne 632.816 nm in air; Na D2 588.995 nm, D1 589.592 nm in air (NIST); the LED "
                                          "(625 nm, 17 nm FWHM) and the lamp's 1.7 GHz line width (about its Doppler width "
                                          "at 500 K) are illustrative - " + MEM},
         ILLUS, SIM],
        {"reading": "res", "textbook": "pl10_mich", "tol": 0.01}, LASER_SAFE + " The sodium lamp is hot.",
        "Michelson interferometer", "A Michelson interferometer on a long-travel stage with a micrometer drive, a photodiode "
        "and fringe counter, and the He-Ne laser, LED and sodium lamp.",
        [{"say": "The beam splitter, the fixed and moving mirrors, the long-travel stage and the photodiode."}])


def hom() -> dict:
    return _mk(
        "pl10-hom", "pl10_hom", CH_INT, "Hong-Ou-Mandel two-photon interference",
        "Send the two photons of a degenerate SPDC pair into the two inputs of a 50:50 beam splitter, scan the delay of "
        "one input and record the coincidence counts: find the depth (visibility) and the width of the Hong-Ou-Mandel "
        "dip and from it the photons' coherence length. SIMULATED DATA.",
        {"x": 0.0, "s": 0.0, "q": 0.0},
        [knob("x", "Delay stage position", "x", -500, 500, 0.5, 0, "um"),
         knob("V0", "This source (its indistinguishability is hidden)", "V0", 0.3, 1.0, 0.001, 0.96, hidden=True)],
        [inst("y", "readout", "Coincidences", "y", lc=1, digits=0)],
        "Two identical photons arriving together at a 50:50 beam splitter always leave by the same port: the two ways of "
        "getting one photon at each detector (both transmitted, both reflected) cancel. The coincidence rate falls to "
        "zero at zero delay, the HOM dip. Its depth (visibility) measures how indistinguishable the photons are "
        "(polarisation, spectrum, timing): V = V0 cos^2(theta) when their polarisations differ by theta. Its width is "
        "the photons' coherence length: for Gaussian filters of FWHM dlam the dip's FWHM in path difference is "
        "4 ln2 lam^2 / (pi dlam). The counts are Poisson draws: SIMULATED DATA.",
        ["Align the SPDC pair through 5 nm filters into fibres and onto the beam splitter.",
         "Step the delay stage from -350 to +350 micrometres and count coincidences for 60 s at each.",
         "Take off the accidental coincidences; the far points give the baseline.",
         "Fit ln(1 - C/C0) against x^2 near the dip: the intercept gives V, the slope the width."],
        [_q("At zero delay with identical photons the coincidence rate", ["Falls to zero", "Doubles", "Is unchanged"], 0,
            "The two amplitudes cancel."),
         _q("Narrower filters make the dip", ["Wider", "Narrower", "Deeper only"], 0, "Coherence length ~ lam^2/dlam.")],
        [LOUDON, {"title": "C. K. Hong, Z. Y. Ou and L. Mandel, Phys. Rev. Lett. 59, 2044 (1987)"}, ILLUS, SIM,
         _stat("3 %", "Coincidence counts are Poisson: the visibility and the width carry about 1 % scatter.")],
        {"reading": "res", "textbook": "pl10_homv", "tol": 0.03}, LASER_SAFE + " " + HV_SAFE,
        "HOM interferometer", "A 405 nm pump laser on a BBO crystal, filters and fibre couplers, a fibre beam splitter, "
        "a delay stage, two single-photon detectors and a coincidence counter.",
        [{"say": "The pump laser and SPDC crystal, the two photon arms, the delay stage, the beam splitter and the detectors."}])


def chsh() -> dict:
    return _mk(
        "pl10-chsh", "pl10_chsh", CH_INT, "Entangled photons and the CHSH Bell inequality",
        "Make polarisation-entangled photon pairs with a two-crystal type-I SPDC source, record the polarisation "
        "correlation curves and the sixteen coincidence counts of the CHSH test, and find S. SIMULATED DATA.",
        {"x": 0.0, "s": 0.0, "q": 0.0},
        [knob("x", "Analyser setting number", "x", 0, 17, 1, 0),
         knob("V", "This source (its visibility is hidden)", "V", 0.3, 1.0, 0.001, 0.93, hidden=True)],
        [inst("y", "readout", "Coincidences", "y", lc=1, digits=0)],
        "Two thin BBO crystals with crossed optic axes, pumped at 45 degrees, make the pair state (|HH> + |VV>)/sqrt2: "
        "neither photon has a polarisation of its own, but they always agree. With analysers at a and b the coincidence "
        "rate is R0/4 (1 + V cos 2(a - b)), so the correlation E(a, b) = V cos 2(a - b) depends only on the "
        "difference, in every basis. Any local hidden-variable theory obeys |S| <= 2 with S = E(a,b) - E(a,b') + "
        "E(a',b) + E(a',b'); quantum mechanics gives S = 2 sqrt2 V at a = 0, a' = 45, b = 22.5, b' = 67.5 degrees "
        "(2 sqrt2 is Tsirelson's bound). E is formed from four coincidence counts with the analysers and their "
        "orthogonal settings. Accidental coincidences (singles x window) are taken off first.",
        ["With analyser A at 0 degrees, turn analyser B in 22.5 degree steps and count 30 s at each; repeat with A at 45.",
         "The visibility of both curves should be the same: the state is entangled, not just correlated in H/V.",
         "Count the sixteen settings a in {0, 45, 90, 135} and b in {22.5, 67.5, 112.5, 157.5}.",
         "Form the four E values and S."],
        [_q("Local realism requires", ["|S| <= 2", "|S| <= 2 sqrt2", "S = 0"], 0, "The CHSH inequality."),
         _q("Why measure the correlation in the 45 degree basis too?", ["A merely classically correlated source shows no "
            "fringes there", "To check the laser", "To raise S"], 0, "Entanglement keeps the visibility in every basis.")],
        [LOUDON, {"title": "J. F. Clauser, M. A. Horne, A. Shimony and R. A. Holt, Phys. Rev. Lett. 23, 880 (1969); "
                           "P. G. Kwiat et al., Phys. Rev. A 60, R773 (1999)"}, ILLUS, SIM,
         _stat("2 %", "Coincidence counts are Poisson: S carries about 0.5 % scatter.")],
        {"reading": "res", "textbook": "pl10_bell", "tol": 0.02}, LASER_SAFE + " " + HV_SAFE,
        "Entangled-photon table", "A 405 nm pump laser, the two-crystal BBO source, two polariser-analysers on rotation "
        "mounts, filters, two single-photon detectors and a coincidence counter.",
        [{"say": "The pump laser, the two-crystal source, the two analysers on rotation mounts and the detectors."}])


def eraser() -> dict:
    return _mk(
        "pl10-eraser", "pl10_eraser", CH_INT, "Single-photon interference and the quantum eraser",
        "Send a strongly attenuated laser, one photon at a time, through a Mach-Zehnder interferometer: record the fringes, "
        "mark the paths with a half-wave plate so the fringes vanish, then erase the mark with a polariser and see them "
        "return; measure the visibility in each case. SIMULATED DATA.",
        {"x": 0.0, "s": 0.0, "q": 0.0},
        [knob("x", "Piezo voltage", "x", 0, 10, 0.01, 0, "V"),
         knob("V0", "This interferometer (its visibility is hidden)", "V0", 0.3, 1.0, 0.001, 0.94, hidden=True)],
        [inst("y", "readout", "Counts", "y", lc=1, digits=0)],
        "With fewer than one photon in the interferometer at a time the counts still form fringes as the path difference "
        "changes: each photon interferes with itself. Fringes need the two paths to be indistinguishable. A half-wave "
        "plate turning one arm's polarisation through psi marks which path a photon took; the fringe visibility falls to "
        "V0 |cos psi|, zero for orthogonal polarisations. A polariser at psi/2 after the interferometer projects both "
        "paths onto the same polarisation: the which-path information is erased and the full visibility V0 returns, with "
        "half the light. Visibility comes from a least-squares fit of counts = a + b cos(phase) + c sin(phase): "
        "V = sqrt(b^2 + c^2)/a. The counts are Poisson draws: SIMULATED DATA.",
        ["Attenuate the laser so the mean photon number per coherence time is far below one.",
         "Scan the piezo over two fringes and count 10 s at each step.",
         "Turn the half-wave plate in one arm to mark the path and scan again.",
         "Put the polariser at psi/2 after the output beam splitter and scan again.",
         "Fit the visibility of each scan."],
        [_q("Why do fringes form with one photon at a time?", ["Each photon interferes with itself", "Photons push each "
            "other", "The detector remembers"], 0, "Interference is of amplitudes for one photon."),
         _q("The eraser restores the fringes because", ["It removes the which-path information", "It adds light",
            "It moves the mirror"], 0, "After the polariser the paths are indistinguishable again.")],
        [LOUDON, {"title": "S. P. Walborn, M. O. Terra Cunha, S. Padua and C. H. Monken, Phys. Rev. A 65, 033818 (2002); "
                           "the quantum eraser of Scully and Druhl (1982)", "note": MEM}, ILLUS, SIM,
         _stat("2 %", "The counts are Poisson: the visibility carries a few tenths of a per cent scatter.")],
        {"reading": "res", "textbook": "pl10_erase", "tol": 0.02}, LASER_SAFE + " The photon counter must never see room light.",
        "Mach-Zehnder single-photon interferometer", "An attenuated laser (or a heralded single-photon source), a "
        "Mach-Zehnder interferometer with a piezo mirror, a half-wave plate in one arm, an eraser polariser and a "
        "single-photon detector.",
        [{"say": "The attenuated laser, the two beam splitters and mirrors, the piezo, the wave plate and the photon counter."}])


BUILDERS = (sat_abs, optical_pumping, hd_isotope, diode_laser, freq_lock, shg, z_scan, tcspc, pump_probe, mot, bec,
            michelson, hom, chsh, eraser)
