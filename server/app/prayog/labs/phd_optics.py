"""Prayogshala lab pack: Ph.D. LASER SPECTROSCOPY, INTERFEROMETRY, PHOTON STATISTICS, SIGNAL RECOVERY AND PLASMA
DIAGNOSTICS - research techniques on four benches (rigs).

    phd-noise-bench    lock-in detection, Johnson noise (kB), shot noise (e), noise spectra with 1/f, boxcar averaging.
    phd-photon-bench   Hanbury Brown-Twiss g2(0), Poisson counting statistics, heralded single-photon anticorrelation.
    phd-laser-bench    a scanning Fabry-Perot cavity: free spectral range, finesse, laser mode structure.
    phd-plasma-bench   Langmuir probe (single, double, emissive) and the Paschen breakdown curve.

Every reading comes from this area's own kernels (`packs/phd_optics.py`); every noisy or counting process is drawn from
a generator seeded by the lab's own `seed`, and each lab carries a `check`: the reading found on the simulated response
against an exact relation (Johnson-Nyquist, shot noise, Poisson, Airy finesse, ...). For a noise result the check is
within a stated statistical tolerance (2 to 4 %), not 1 %, and the lab says so in its sources. Where the real
instrument is not something a student may touch, the lab text says so.
"""
from __future__ import annotations

from ..catalog import B, lab

GRP = "Physics · Research Techniques in Optics, Signals and Plasma"
LVL = "Ph.D."
SIM = {"title": "Hoola Prayogshala kernel",
       "note": "noise and counts are drawn from the lab's own seed; checked against the exact relation in Hoola's tests"}
CODATA = {"title": "SI 2019 exact values: e = 1.602176634e-19 C, kB = 1.380649e-23 J/K, c = 299792458 m/s",
          "note": "CODATA 2018 for the electron mass and the atomic mass unit (plasma lab)"}
ART = {"title": "Horowitz and Hill, The Art of Electronics, chapter 8 (noise) and chapter 15 (signal recovery)"}
MIT = {"title": "MIT Junior Lab: Johnson Noise and Shot Noise"}
LOUDON = {"title": "R. Loudon, The Quantum Theory of Light, photon statistics and coherence chapters"}
HUTCH = {"title": "I. H. Hutchinson, Principles of Plasma Diagnostics, electric probes chapter"}


def _statnote(tol: str, why: str) -> dict:
    return {"title": "About this lab's check",
            "note": f"Within {tol} of the exact relation. {why}"}


def _q(q, options, answer, why):
    return {"q": q, "options": options, "answer": answer, "why": why}


def _bench() -> list[dict]:
    return [B("bench", "box", name="Optical table", size=[1.0, 0.02, 0.6], pos=[0, -0.02, 0], color="wood", cut=False),
            B("unit", "box", name="Instrument", size=[0.3, 0.12, 0.2], pos=[0, 0.06, 0], color="#2b2f36")]


def _mk(id, rig, title, kernel, params, aim, steps, theory, safety, questions, sources, check, topic, chapter):
    return lab(id=id, rig=rig, title=title, group=GRP, level=LVL, topic=topic, chapter=chapter, aim=aim,
               kernel=kernel, params=params, autorun=True,
               camera={"pos": [0.0, 0.5, 0.9], "look": [0.0, 0.05, 0.0]}, floor=-0.2, bodies=_bench(),
               steps=steps, theory=theory, safety=safety, questions=questions, sources=sources, check=check)


NOISE = "phd-noise-bench"
TWEEZ = "phd-tweezers-bench"
PHOTON = "phd-photon-bench"
LASER = "phd-laser-bench"
PLASMA = "phd-plasma-bench"
CH_SIG = "Signal recovery and noise"
CH_LAS = "Laser spectroscopy and atomic physics"
CH_INT = "Interferometry, quantum optics and photon statistics"
CH_PLA = "Plasma diagnostics"
NOLASER = "No laser and no high voltage is used in this experiment."


# ================================================================================================ signal recovery
def lockin_detection() -> dict:
    return _mk(
        "phd-lockin-detection", NOISE, "Phase-sensitive (lock-in) detection of a small signal", "phd_lockin",
        {"A": 2.0e-5, "f": 137.0, "phi": 35.0, "en": 3.0e-7, "tc": 3.0, "phr": 0.0, "dual": 1.0, "seed": 5.0},
        "Recover a 20 microvolt signal chopped at 137 Hz from broadband noise several times larger: first with a "
        "single-phase lock-in, by turning the reference phase, then with a dual-phase lock-in that reads X, Y, R and "
        "the signal phase together, and see how the noise falls with the time constant.",
        ["Switch the instrument on. The chopper runs at 137 Hz and the lock-in takes its reference from it.",
         "Single phase: set the time constant to 1 s and write X down at six reference phases from 0 to 300 degrees.",
         "X follows the amplitude times the cosine of the phase difference; the peak of that cosine is the amplitude.",
         "Dual phase: set the reference to 0 degrees and take a reading at each time constant, 0.1, 0.3, 1 and 3 s.",
         "Each dual reading gives X, Y, then R and theta; the instrument repeats it five times so you can see the scatter.",
         "Compare the scatter at each time constant: it falls as one over the square root of the time constant."],
        "The input is multiplied by a reference at the signal frequency and the product is averaged by a low-pass filter "
        "of time constant tau. The signal, being at the reference frequency, gives a steady output; noise at any other "
        "frequency averages away. Only a band of about 1/(4 tau) round the reference gets through, so the noise left "
        "falls as 1/sqrt(tau). A single mixer gives X = A cos(phi - phi_r): you have to turn the reference to find the "
        "peak. Two mixers 90 degrees apart give X and Y together, so R = sqrt(X^2 + Y^2) = A is independent of the "
        "phase and theta = arctan(Y/X) is the phase itself. The noise here is white and drawn from the lab's seed; the "
        "signal amplitude, phase and noise density are the lab's design values, not a particular instrument's.",
        NOLASER + " Keep the chopper guard on.",
        [_q("Why does a longer time constant give a cleaner reading?", ["It narrows the band of noise that gets through", "It makes the signal larger", "It raises the chopper frequency"], 0,
            "The detection band is about 1/(4 tau)."),
         _q("A lock-in shows X = 0 and Y = A. The signal phase relative to the reference is", ["90 degrees", "0 degrees", "180 degrees"], 0,
            "X = A cos(delta) and Y = A sin(delta)."),
         _q("Quadrupling the time constant changes the noise on a reading by a factor of about", ["0.5", "4", "0.25"], 0, "Noise falls as 1/sqrt(tau).")],
        [LOUDON | {"title": "Preston and Dietz, The Art of Experimental Physics: signal recovery and lock-in detection"}, ART, SIM,
         _statnote("2 %", "The reading is noisy, and its statistical scatter at 3 s is about 0.4 %."),
         {"title": "Illustrative design values", "note": "signal amplitude, phase, chopper frequency and noise density are the lab's own; no instrument datasheet is quoted"}],
        {"reading": "R", "textbook": "phd_lockin_A", "tol": 0.02}, "Signal recovery", CH_SIG)


def johnson_noise() -> dict:
    return _mk(
        "phd-johnson-noise", NOISE, "Johnson noise and Boltzmann's constant", "phd_johnson",
        {"T": 300.0, "df": 10000.0, "G": 1000.0, "en": 2.0e-9, "n": 100000.0, "seed": 3.0, "R": 10000.0},
        "Measure the mean-square thermal noise voltage of eight metal-film resistors through a low-noise amplifier at "
        "room temperature, find Boltzmann's constant from the slope against resistance, and see the noise fall when the "
        "resistors are cooled in liquid nitrogen.",
        ["Switch the amplifier and the true-rms voltmeter on. The noise bandwidth is set by the amplifier's filter: 10 kHz.",
         "With the switch on SHORT read the mean-square output: that is the amplifier's own noise.",
         "Turn the switch to each resistor in turn, from 1 kilohm to 100 kilohm, press MEASURE and write v squared down.",
         "Plot v squared against R. The slope is 4 kB T G squared times the bandwidth; the intercept is the amplifier's noise.",
         "Lower the can of resistors into the liquid nitrogen (about 77 K) and read the short and the 100 kilohm again.",
         "Check that the resistor's part of the noise has fallen in proportion to the temperature."],
        "Charge carriers in a resistor move at random with thermal energy, so a resistor at temperature T has a "
        "fluctuating voltage across its ends even with no current. In a bandwidth df the mean square of that voltage is "
        "4 kB T R df (Nyquist, 1928). The amplifier multiplies the voltage by its gain G, so the voltmeter reads G^2 "
        "times as much, plus the square of the amplifier's own input noise. Measured for several R, the points lie on "
        "a straight line whose slope is 4 kB T df G^2 and whose intercept is the amplifier's noise. Each reading is the "
        "mean square of a finite number of samples, so it carries a statistical scatter of about sqrt(2/n).",
        "Liquid nitrogen is at about 77 K: wear gloves and goggles, use a vented container, lower the can on its rod and "
        "never hold it in your hand. " + NOLASER,
        [_q("Cooling the resistor from 300 K to 77 K changes its noise power by a factor of about", ["0.26", "4", "0.5"], 0, "v squared is proportional to T."),
         _q("What does the intercept of the line v squared against R measure?", ["The noise of the amplifier", "The temperature", "The bandwidth"], 0,
            "With the input shorted only the amplifier's noise is left."),
         _q("Why is the noise voltage measured in a stated bandwidth?", ["The noise power is proportional to the bandwidth", "The meter is slow", "The resistor changes with frequency"], 0, "v squared = 4 kB T R df.")],
        [MIT, ART, CODATA, SIM, _statnote("2 %", "kB comes from a straight-line fit to noisy mean squares: the scatter is about 0.5 %.")],
        {"reading": "kB23", "textbook": "phd_o_kB", "tol": 0.02}, "Noise", CH_SIG)


def shot_noise() -> dict:
    return _mk(
        "phd-shot-noise", NOISE, "Shot noise and the electron charge", "phd_shot",
        {"Rf": 1.0e4, "df": 20000.0, "n": 40000.0, "seed": 11.0, "T": 300.0, "I": 2.0e-4, "q": 1.602176634e-19, "Iscale": 1.0},
        "Measure the noise of a photocurrent from a p-n photodiode lit by an LED at seven currents, and find the charge of "
        "the carrier from the slope of the mean-square noise against the current.",
        ["Switch the transimpedance amplifier and the voltmeter on. The amplifier has a 10 kilohm feedback resistor and a 20 kHz bandwidth.",
         "With the LED dark, read the mean-square output: it is the feedback resistor's own Johnson noise.",
         "Turn the LED current knob to each of the six lit positions and read the mean-square output at each.",
         "Write the readings in the table and plot v squared against the photocurrent.",
         "The slope is 2 q times Rf squared times the bandwidth. Work out q."],
        "Current is a stream of separate charges q arriving at random. Counting them in a short time gives a Poisson "
        "number, so the current fluctuates; in a bandwidth df the mean-square fluctuation is 2 q I df. A transimpedance "
        "amplifier turns the current into the voltage Rf I, so the voltmeter reads Rf^2 times the current noise. The "
        "feedback resistor adds its own Johnson noise, 4 kB T df / Rf, which is the intercept of the line at zero "
        "current. The slope of mean-square voltage against current is therefore 2 q Rf^2 df, and q follows. The "
        "carrier is the electron; the lab's simulation draws Gaussian noise of the right variance, which is what a Poisson "
        "stream of this many charges per sample looks like.",
        "The LED is a low-power visible indicator LED, not a laser. " + NOLASER,
        [_q("Doubling the photocurrent makes the shot-noise power", ["Double", "Four times", "Unchanged"], 0, "i squared = 2 q I df is proportional to I."),
         _q("Why is the noise at zero current not zero?", ["The feedback resistor still makes Johnson noise", "The LED leaks", "The meter is faulty"], 0, "It is the intercept of the line."),
         _q("What does the slope of v squared against I give?", ["The charge of the carrier", "The resistance", "The temperature"], 0, "slope = 2 q Rf squared df.")],
        [MIT, ART, CODATA, SIM, _statnote("2 %", "q comes from a straight-line fit to noisy mean squares: the scatter is about 0.6 %.")],
        {"reading": "q19", "textbook": "phd_o_qe", "tol": 0.02}, "Noise", CH_SIG)


def noise_spectral_density() -> dict:
    return _mk(
        "phd-noise-spectrum", NOISE, "Noise spectral density and 1/f noise", "phd_psd",
        {"T": 300.0, "R": 10000.0, "en": 5.0e-9, "fc": 150.0, "fs": 8000.0, "N": 256.0, "nseg": 256.0, "seed": 17.0},
        "Look at the voltage noise of a resistor and its amplifier on an FFT spectrum analyser, average more and more "
        "spectra, and find the flat white-noise floor and the corner frequency below which 1/f noise takes over.",
        ["Switch the spectrum analyser on. It samples at 8 kHz and takes records of 256 points with a Hann window.",
         "Choose 4 averages, press ACQUIRE and look at the spectrum on the log-log screen.",
         "Press the fit: the analyser fits a floor plus a 1/f term and gives the floor and the corner frequency.",
         "Write them down. Repeat with 16, 64 and 256 averages.",
         "See the scatter of the spectrum shrink as the averages grow, and the two fitted numbers settle."],
        "A resistor and an amplifier give a flat (white) voltage noise, S_w = 4 kB T R + e_n^2 in V^2/Hz, with an extra "
        "excess noise that rises as 1/f at low frequency. Writing S(f) = S_w (1 + f_c / f), the corner f_c is where the "
        "1/f part equals the white floor. The analyser takes the FFT of many windowed records and averages the power. "
        "A single power spectrum of random noise scatters by 100 % in every bin; averaging N of them cuts that to "
        "1/sqrt(N). The fit weights each point by the model, since the scatter of a point is proportional to the "
        "point. The resistor, amplifier and corner frequency here are the lab's design values.",
        NOLASER,
        [_q("What is the corner frequency?", ["Where the 1/f part equals the white floor", "Where the noise stops", "The sampling frequency"], 0, "S(f_c) = 2 S_w."),
         _q("Averaging 64 spectra instead of 4 makes the scatter of each point", ["Four times smaller", "Sixteen times smaller", "The same"], 0, "It falls as 1/sqrt(N)."),
         _q("The white floor of a resistor in front of an amplifier is", ["4 kB T R plus the amplifier's e_n squared", "4 kB T / R", "kB T"], 0, "The resistor's Johnson noise plus the amplifier's own.")],
        [ART, CODATA, SIM, _statnote("4 %", "The floor is a fit to an average of 256 noisy spectra: the scatter is about 1 %."),
         {"title": "Illustrative design values", "note": "the corner frequency and amplifier noise are the lab's own and not those of a named device"}],
        {"reading": "floor18", "textbook": "phd_psd_floor", "tol": 0.04}, "Noise", CH_SIG)


def boxcar_averaging() -> dict:
    return _mk(
        "phd-boxcar-averaging", NOISE, "Boxcar averaging of a repetitive pulse", "phd_boxcar",
        {"tau": 2.0e-6, "A": 1.0, "vn": 3.0e-4, "w": 5.0e-7, "td": 0.0, "nav": 20000.0, "seed": 23.0},
        "Recover a 2 microsecond decaying light pulse from noise with a boxcar averager: show that the signal-to-noise "
        "ratio grows as the square root of the number of shots, then step the gate along the pulse to map out its decay time.",
        ["Switch the boxcar averager on. The pulse generator flashes the LED once a millisecond and triggers the gate.",
         "Put the gate at the start of the pulse. For 1, 4, 16, 64 and 256 shots averaged, write down the SNR.",
         "The instrument repeats the measurement 40 times at each setting; the SNR is the mean over the scatter.",
         "Plot log SNR against log N. The slope should be one half.",
         "Now average 20000 shots and step the gate in eight steps along the pulse. Write the output down at each.",
         "The slope of ln(output) against gate delay is minus one over the decay time."],
        "A boxcar averager opens a short gate a chosen time after each trigger, averages the signal inside it, and "
        "averages that over many shots. The pulse repeats exactly, the noise does not, so the signal adds up N times "
        "and the noise only sqrt(N) times: the signal-to-noise ratio grows as sqrt(N). For a pulse A exp(-t/tau) the "
        "gate average is A (tau/w) (1 - exp(-w/tau)) exp(-td/tau), so ln(output) falls linearly with the gate delay td "
        "with slope -1/tau, whatever the gate width w. The noise in a gate of width w is e_n / sqrt(2 w) for a white "
        "noise density e_n. The pulse and noise are the lab's design values (a 2 microsecond decay is typical of a "
        "fast fluorescence or a photodiode response).",
        NOLASER,
        [_q("Averaging 100 pulses instead of 1 improves the signal-to-noise ratio by", ["10", "100", "1"], 0, "SNR grows as sqrt(N)."),
         _q("Why does the gate width not change the measured decay time?", ["The log of the output stays a line of the same slope", "The gate is too short", "The pulse is always the same"], 0,
            "ln(output) = const - td / tau."),
         _q("What must the pulse do for boxcar averaging to work?", ["Repeat identically while the noise does not", "Be very large", "Be a sine wave"], 0, "Only a repeating signal adds coherently.")],
        [ART, SIM, _statnote("3 %", "The decay time is a fit to noisy averages: the scatter is about 0.7 %."),
         {"title": "Illustrative design values", "note": "the 2 microsecond decay and the noise density are the lab's own"}],
        {"reading": "tau", "textbook": "phd_boxcar_tau", "tol": 0.03}, "Signal recovery", CH_SIG)


# ================================================================================================ photon statistics
def hbt_g2() -> dict:
    return _mk(
        "phd-hbt-g2", PHOTON, "Hanbury Brown-Twiss intensity correlations", "phd_g2",
        {"tc": 5.0e-5, "kind": 1.0, "R1": 2.0e5, "R2": 2.0e5, "Ts": 30.0, "nb": 81.0, "bw": 6.25e-6, "seed": 9.0},
        "Split a beam in two, count the photons on each side with two detectors, and histogram the delay between "
        "coincidences. Pseudo-thermal light from a rotating ground-glass disc bunches, g2(0) = 2; laser light does not, "
        "g2 = 1. Find g2(0) and the coherence time.",
        ["Switch the counters on. The laser is expanded and sent through a rotating ground-glass disc (a pseudo-thermal source).",
         "Accumulate the coincidence histogram for 30 s. Each bin is 6.25 microseconds wide and the histogram spans plus and minus 250 microseconds.",
         "Divide the centre bin by the mean of the far bins: that is g2(0).",
         "Fit ln(g2(tau) - 1) against tau squared near zero delay. The slope gives the coherence time.",
         "Take the ground glass out of the beam and repeat: the histogram is flat and g2 = 1."],
        "The normalised intensity correlation g2(tau) = <I(t) I(t+tau)> / <I>^2 compares the chance of two photons "
        "arriving tau apart with the chance for uncorrelated arrivals. Thermal (chaotic) light has g2(0) = 2: "
        "photons arrive in bunches (Hanbury Brown and Twiss, 1956). Light from a steady laser has g2 = 1 at every delay: "
        "arrivals are independent. Here the thermal source is a laser beam scattered by a rotating ground-glass disc, "
        "with g2(tau) = 1 + exp(-(tau/tc)^2), a model of Gaussian speckle decorrelation; tc depends on the disc speed. "
        "The expected counts in a bin of width bw are R1 R2 T bw g2(tau), and each bin is a Poisson number from the "
        "lab's seed.",
        "The laser is a low-power Class 2 beam: keep it horizontal at bench height, never look into the beam or at a "
        "reflection from the ground glass, and shield the detectors from room light.",
        [_q("Thermal light has g2(0) equal to", ["2", "1", "0"], 0, "Chaotic light bunches."),
         _q("A steady laser beam gives g2(tau)", ["1 at every delay", "2 at zero delay", "0 at zero delay"], 0, "Photon arrivals are independent."),
         _q("A faster-rotating disc makes the coherence time", ["Shorter", "Longer", "The same"], 0, "The speckle pattern decorrelates sooner.")],
        [LOUDON, {"title": "R. Hanbury Brown and R. Q. Twiss, Nature 177 (1956) 27: a test of a new type of stellar interferometer"}, SIM,
         {"title": "About the source model", "note": "g2 = 1 + exp(-(tau/tc)^2) is the lab's model of Gaussian speckle decorrelation; the 50 us coherence time is the lab's own design value"},
         _statnote("1 %", "Each bin holds millions of counts: the scatter is under 0.1 %.")],
        {"reading": "g2_0", "textbook": "phd_g2_zero", "tol": 0.01}, "Photon statistics", CH_INT)


def poisson_counting() -> dict:
    return _mk(
        "phd-poisson-counting", PHOTON, "Poisson statistics of counting", "phd_poisson",
        {"rate": 200.0, "td": 1.0e-5, "tw": 1.0, "nwin": 1000.0, "seed": 13.0},
        "Count photons or scintillation pulses for many equal times, show that the variance equals the mean, that the "
        "gaps between counts follow an exponential law, and see how a counter's dead time makes the counts more regular "
        "than Poisson at a high rate.",
        ["Switch the counter on and set the source rate with the knob (the distance of the source).",
         "Take 1000 counts of 1 second. Write down the mean and the variance of the counts per second.",
         "Repeat at several rates, low to high. At low rates the variance equals the mean.",
         "Look at the histogram of the gaps between counts: ln of the number in each gap bin is a straight line.",
         "At the highest rate the variance falls below the mean, because the counter is blind for 10 microseconds after every count."],
        "Independent random events at a steady rate follow Poisson statistics: the number in a fixed time has variance "
        "equal to its mean, and the gaps between events are exponential with mean 1/rate. A real counter is blind for a "
        "dead time td after each count (non-paralysable). The registered gaps are then td plus an exponential gap, so "
        "the counts become more regular: the Fano factor, variance over mean, falls to 1/(1 + rate td)^2 at a high rate. "
        "The stream is simulated event by event from the lab's seed.",
        NOLASER,
        [_q("For Poisson counts the variance of the number in a fixed time equals", ["The mean", "The mean squared", "Zero"], 0, "That is the Poisson law."),
         _q("A counter's dead time makes the variance at a high rate", ["Smaller than the mean", "Larger than the mean", "Equal to the mean"], 0, "The counts are more regular than random."),
         _q("The gaps between independent random counts are distributed", ["Exponentially", "Normally", "Uniformly"], 0, "The chance of waiting longer decays as exp(-rate t).")],
        [MIT | {"title": "MIT Junior Lab: Poisson Statistics"}, LOUDON, SIM, _statnote("1 %", "The mean gap over 200 000 counts has a scatter of 0.2 %.")],
        {"reading": "gap", "textbook": "phd_poisson_gap", "tol": 0.01}, "Photon statistics", CH_INT)


def heralded_antibunching() -> dict:
    return _mk(
        "phd-heralded-antibunching", PHOTON, "Single-photon anticorrelation with heralded photons", "phd_antibunch",
        {"q": 0.02, "eta": 0.5, "NG": 4.0e8, "seed": 21.0},
        "Count a heralding detector G, and the clicks at the two outputs T and R of a beam splitter that follow it, and "
        "find the anticorrelation parameter alpha. A classical wave cannot give alpha below 1; a single photon gives 0.",
        ["Switch the counters on. A heralding photon arrives at G; the partner goes to the beam splitter.",
         "Count for the run: N_G heralds, then the clicks N_GT, N_GR and the three-fold coincidences N_GTR.",
         "Work out alpha = N_G N_GTR / (N_GT N_GR).",
         "Compare with 1: a value well below 1 cannot come from a classical field.",
         "Note what alpha would be for a perfect single photon (zero) and why the measured value is not quite zero."],
        "For a classical field the chance of detecting a photon at both outputs of a beam splitter, given a heralding "
        "event, is at least the product of the chances at each: alpha = N_G N_GTR / (N_GT N_GR) >= 1 (Grangier, Roger and "
        "Aspect, 1986). One photon can be detected at T or R but not at both, so alpha = 0. Real heralded sources "
        "sometimes hold two photons: here a fraction q of the heralds do. Detectors of efficiency eta then give "
        "alpha = q eta^2/2 divided by the square of the single-click chance. The counts are Poisson numbers from the "
        "lab's seed. The source is a simulated heralded-photon source, not an apparatus a student builds from scratch: "
        "the lab says so.",
        "A real experiment needs a pump laser and single-photon detectors: they are Class 3B and protected, set up by "
        "staff. " + "In this simulation nothing is hazardous.",
        [_q("A perfect single photon at a beam splitter gives alpha equal to", ["0", "1", "2"], 0, "It can click only one detector."),
         _q("Which alpha rules out any classical wave?", ["Below 1", "Above 1", "Exactly 1"], 0, "A classical field gives alpha at least 1."),
         _q("Why is the measured alpha not exactly zero?", ["Some heralds hold two photons", "The beam splitter is not 50:50", "The detectors are slow"], 0, "Multi-pair events click both detectors.")],
        [LOUDON, {"title": "P. Grangier, G. Roger, A. Aspect, Europhysics Letters 1 (1986) 173: experimental evidence for a photon anticorrelation effect on a beam splitter"}, SIM,
         {"title": "About the source model", "note": "heralded-pair fraction q and detector efficiency eta are the lab's own design values; alpha follows from them by counting"},
         _statnote("1 %", "N_GTR holds about a million counts: the scatter is about 0.1 %.")],
        {"reading": "alpha", "textbook": "phd_antibunch_alpha", "tol": 0.01}, "Photon statistics", CH_INT)


# ================================================================================================ laser bench
def fabry_perot_cavity() -> dict:
    return _mk(
        "phd-fabry-perot", LASER, "Scanning Fabry-Perot cavity: free spectral range and finesse", "phd_fp",
        {"L": 0.075, "R": 0.95, "lam": 6.328e-7, "kz": 1.0e-8, "dnu": 4.9965e8, "amp2": 0.45, "Vmax": 120.0},
        "Scan the mirror of a Fabry-Perot cavity with a piezo and read the transmitted light on a scope: the spacing "
        "of the peaks is the free spectral range, the ratio of spacing to width is the finesse, and the extra peaks of "
        "a two-mode laser show its mode spacing.",
        ["Switch the laser, the cavity piezo ramp and the photodiode on. The beam is horizontal at bench height.",
         "Read the peak positions on the scope in volts. One spacing is a mirror displacement of lambda over two: that calibrates the volts.",
         "Measure the full width at half maximum of a peak in volts.",
         "Finesse = peak spacing / width. Free spectral range = c / 2L in hertz, with L the printed mirror separation.",
         "Switch the laser to the two-mode He-Ne: extra, smaller peaks appear between the main ones. Their offset in volts, over the peak spacing, times the FSR, is the mode spacing."],
        "Two parallel mirrors of intensity reflectivity R and separation L transmit light of frequency nu with the Airy "
        "function T = 1 / (1 + F sin^2(delta/2)), F = 4R/(1-R)^2, delta = 4 pi L nu / c. Transmission peaks every free "
        "spectral range, FSR = c/2L, and each peak is narrower the higher R: finesse = FSR / width = pi sqrt(R) / (1 - R) "
        "to a good approximation. Moving one mirror by lambda/2 shifts the pattern by one order, so the piezo volts "
        "between two peaks is a calibration of the scan. A laser with two longitudinal modes gives two interleaved "
        "sets of peaks, offset by the mode spacing.",
        "The He-Ne beam (Class 3R at most) is clamped horizontal at bench height. Never look into the beam or at a "
        "reflection from a mirror. Block the beam when changing optics.",
        [_q("The free spectral range of a cavity of length L is", ["c / 2L", "c / L", "2L / c"], 0, "The round trip is 2L."),
         _q("Higher mirror reflectivity makes the peaks", ["Narrower", "Wider", "Higher"], 0, "Finesse = pi sqrt(R)/(1-R) grows with R."),
         _q("What does a moving mirror shift by lambda/2 do to the pattern?", ["Moves it by one free spectral range", "Does nothing", "Doubles the peaks"], 0, "That is the definition of the order.")],
        [{"title": "C. J. Foot, Atomic Physics (2005), optical cavities"}, CODATA, SIM,
         {"title": "Illustrative design values", "note": "the 95 % mirrors, the 7.5 cm separation, the 30 cm He-Ne tube (500 MHz mode spacing) and the piezo sensitivity are the lab's own; the scan is noise-free"},
         _statnote("1 %", "The finesse is read from the simulated trace by the same peak-width search the student uses.")],
        {"reading": "finesse", "textbook": "phd_fp_finesse", "tol": 0.01}, "Laser spectroscopy", CH_LAS)


# ================================================================================================ plasma bench
def langmuir_probe() -> dict:
    return _mk(
        "phd-langmuir-probe", PLASMA, "Langmuir probe I-V: single, double and emissive probes", "phd_langmuir",
        {"Te": 3.0, "ne": 1.0e16, "Vp": 8.0, "M": 39.948, "Ap": 2.0e-6, "noise": 0.003, "seed": 31.0, "W": 4.5, "Ar": 6.0e5, "Kh": 250.0, "V": 0.0},
        "Find the electron temperature and density of an argon DC glow discharge from the current-voltage curve of a "
        "single probe, check the temperature with a double probe, and find the plasma potential with a heated "
        "emissive probe.",
        ["The discharge is struck in the tube at about 10 pascal. The probe supply and the picoammeter are switched on.",
         "Single probe: sweep from -40 V to +20 V and record the curve. Ion saturation current is the flat part at the far negative end.",
         "Add the ion current back, take the log of the electron current in the transition region and fit a line: the slope is 1/Te.",
         "Double probe: sweep the symmetric pair from -30 V to +30 V. Te follows from the slope near zero and the ion saturation current.",
         "Emissive probe: raise the heater current and read the floating potential. It rises towards the plasma potential and flattens when the wire emits strongly.",
         "Use Te and the ion saturation current to find the plasma density."],
        "A small metal probe in a plasma collects ions (ion saturation current, set by the Bohm speed sqrt(kTe/M)) when "
        "very negative, and electrons when positive. In between the Maxwellian electrons are repelled in proportion to "
        "exp(eV/kTe), so ln of the electron current is a straight line of slope 1/Te volts. The knee where it saturates is "
        "the plasma potential. A double probe floats with no reference to the plasma and draws at most the ion current, "
        "I = Iis tanh(V/2Te). A heated emissive probe floats close to the plasma potential, because its emission balances "
        "the electron flux. The numbers come from a model with an ideal probe, no sheath expansion and no magnetic field; "
        "the wire's work function, Richardson constant and heating are illustrative.",
        "A glow discharge needs a high-voltage supply: keep the cover on the tube and never touch the electrodes or the probe "
        "leads while it is on. The heated wire and the glass are hot.",
        [_q("The slope of ln(electron current) against V is", ["1/Te in volts", "Te", "The plasma potential"], 0, "Ie is proportional to exp(V/Te)."),
         _q("A double probe can never draw more than", ["The ion saturation current", "The electron saturation current", "Zero"], 0, "It floats and draws equal and opposite currents."),
         _q("A heated emissive probe floats at", ["Close to the plasma potential", "Far below it", "Zero volts"], 0, "Strong emission raises the floating potential to Vp.")],
        [HUTCH, CODATA, SIM, {"title": "IUPAC standard atomic weight of argon, 39.948"},
         {"title": "Illustrative design values", "note": "Te, ne, Vp of the discharge are the lab's own; the emissive wire's work function 4.5 eV, Richardson constant 6e5 A/m2K2 and heating 250 K/A2 are unsourced and illustrative"},
         _statnote("1 %", "Te is a line fit to a swept curve with 0.3 % noise on each point.")],
        {"reading": "Te", "textbook": "phd_lang_te", "tol": 0.01}, "Plasma diagnostics", CH_PLA)


def paschen_curve() -> dict:
    return _mk(
        "phd-paschen-curve", PLASMA, "Paschen breakdown curve", "phd_paschen",
        {"A": 15.0, "B": 365.0, "gam": 0.01, "noise": 0.003, "seed": 41.0, "pd": 1.0},
        "Find the voltage at which a gas breaks down between two parallel plates at many values of pressure times gap, "
        "and locate the minimum of the curve: the lowest breakdown voltage and the pd at which it occurs.",
        ["Evacuate the chamber and admit the gas. The plates are 1 cm apart; the pressure sets pd.",
         "Raise the voltage slowly until the gas breaks down and record the breakdown voltage.",
         "Repeat at pressures from the lowest to 300 torr cm on a roughly logarithmic grid.",
         "Plot the breakdown voltage against pd. The curve has a minimum.",
         "Find the minimum by a quadratic fit of the lowest points against ln(pd)."],
        "Breakdown occurs when each electron leaving the cathode makes enough ions to free one more: gamma "
        "(exp(alpha d) - 1) = 1. With the ionisation coefficient alpha = A p exp(-B p / E) this gives Paschen's law "
        "V = B pd / (ln(A pd) - ln(ln(1 + 1/gamma))). The voltage rises at high pd (many collisions) and at low pd (too "
        "few), with a minimum V_min = e B ln(1 + 1/gamma) / A at pd = e ln(1 + 1/gamma) / A, where e = 2.718. The gas "
        "constants A and B and the cathode's gamma are unsourced values reproduced from memory of a textbook table, "
        "and are illustrative.",
        "The breakdown supply is high voltage. In a real experiment the chamber is screened and interlocked; never "
        "touch the electrodes while the supply is on. " + NOLASER,
        [_q("At very low pd the breakdown voltage rises because", ["Electrons cross the gap without enough collisions", "The gas is too hot", "The plates are too far apart"], 0, "Too few ionising collisions."),
         _q("The minimum of the Paschen curve depends on", ["The gas and the cathode surface", "Only the supply", "Only the temperature"], 0, "Through A, B and gamma."),
         _q("Doubling the gap at fixed pd", ["Leaves V_b unchanged", "Doubles V_b", "Halves V_b"], 0, "V_b depends on pd only.")],
        [HUTCH | {"title": "Lieberman and Lichtenberg, Principles of Plasma Discharges and Materials Processing: Paschen's law"}, SIM,
         {"title": "Unsourced / illustrative constants", "note": "A = 15 /(cm torr), B = 365 V/(cm torr) and gamma = 0.01 for air are remembered textbook-table values, not looked up for this lab"},
         _statnote("1 %", "Each breakdown carries 0.3 % scatter; the minimum is found by a quadratic fit.")],
        {"reading": "Vmin", "textbook": "phd_paschen_vmin", "tol": 0.01}, "Plasma diagnostics", CH_PLA)


def optical_tweezers() -> dict:
    return _mk(
        "phd-optical-tweezers", TWEEZ, "Optical tweezers: trap stiffness (simulated instrument)", "phd_tweezers",
        {"a": 5.0e-7, "eta": 1.0e-3, "T": 295.0, "kp": 2.0e-6, "P": 5.0, "fs": 5000.0, "N": 262144.0, "seg": 2048.0,
         "nseg": 32.0, "v": 1.0e-4, "Td": 10.0, "seed": 71.0},
        "Hold a silica bead in an optical trap and measure its stiffness three ways: the width of its thermal wander "
        "(equipartition), the corner frequency of its spectrum, and its lag behind a moving stage (Stokes drag). Then find kB and the viscosity.",
        ["Switch the trap analyser on. The enclosed laser is a simulated instrument: you only set its power with the knob.",
         "Equipartition: record the bead for 52 s at three or four laser powers, work out the mean square displacement and kappa = kB T / <x squared>.",
         "Plot kappa against power: it is a straight line through the origin.",
         "Power spectrum: at the third power, fit a Lorentzian to the averaged spectrum. The corner frequency gives kappa = 2 pi gamma fc, with gamma = 6 pi eta a.",
         "Stokes drag: move the stage at 100 micrometres per second and measure the lag of the bead behind its rest position. kappa = gamma v / x_d.",
         "Compare the three stiffnesses. With the drag value of kappa, the equipartition record gives kB; with the equipartition kappa, the corner frequency gives the viscosity."],
        "Light refracted by a transparent bead pulls it towards the focus of a tightly focused beam: near the focus it "
        "is a spring of stiffness kappa that grows with laser power. Thermal kicks from the water make the bead wander "
        "(Brownian motion), and in the trap this is an Ornstein-Uhlenbeck process. Three independent ways give kappa. "
        "Equipartition: the mean potential energy kappa <x^2> / 2 is kB T / 2. Power spectrum: the position spectrum "
        "is a Lorentzian with corner frequency fc = kappa / (2 pi gamma), where gamma = 6 pi eta a is the Stokes drag "
        "of a sphere; the digitiser's sampling is allowed for in the fit. Stokes drag: a stage moving at speed v makes the "
        "water drag the bead with force gamma v, balanced by kappa x_d. The record is simulated from the lab's own seed.",
        "SIMULATED INSTRUMENT. A real trapping laser is an invisible Class 4 infrared beam: it is enclosed and interlocked, "
        "set up by staff, and no student opens the box, the beam tube or looks into a microscope port.",
        [_q("Doubling the laser power makes the trap stiffness", ["Double", "Half", "Unchanged"], 0, "kappa is proportional to the power."),
         _q("Equipartition says the mean potential energy of the bead in the trap is", ["kB T / 2", "kB T", "Zero"], 0, "One degree of freedom."),
         _q("A stiffer trap has a corner frequency that is", ["Higher", "Lower", "The same"], 0, "fc = kappa / (2 pi gamma)."),
         _q("Which method needs the viscosity and the bead radius?", ["The corner frequency and the drag test", "Only equipartition", "None of them"], 0, "gamma = 6 pi eta a enters both.")],
        [{"title": "MIT Junior Lab: Optical Trapping"},
         {"title": "K. Berg-Sorensen and H. Flyvbjerg, Rev. Sci. Instrum. 75 (2004) 594: power spectrum analysis for optical tweezers"}, CODATA, SIM,
         {"title": "Illustrative design values", "note": "kp = 2 micronewtons per metre per milliwatt is the lab's own stiffness per unit power; the 1 micrometre bead, water at 295 K and 1.0 mPa s are typical, not a named product"},
         _statnote("4 %", "kappa from equipartition has a statistical scatter of about 1 % over a 52 s record; the spectrum fit about 2 %, and the drag test about 0.5 %.")],
        {"reading": "k_eq_u", "textbook": "phd_tw_kappa", "tol": 0.04}, "Optical trapping", CH_LAS)


BUILDERS = (lockin_detection, johnson_noise, shot_noise, noise_spectral_density, boxcar_averaging, hbt_g2, poisson_counting,
            heralded_antibunching, fabry_perot_cavity, optical_tweezers, langmuir_probe, paschen_curve)
