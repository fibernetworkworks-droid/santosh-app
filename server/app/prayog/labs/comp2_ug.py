"""Prayogshala lab pack: the B.Sc. "Computational physics" practicals, second set (spectra, quadrature, quantum
mechanics, special functions, linear algebra, dynamics, ...).

One rig serves them all - `app/static/prayog/exp/comp2-workstation.js`, the same real workstation as the first set
(desk, monitor, keyboard, method card) with plots for spectra, wavefunctions and iteration histories. The physics is the
`comp2_ug` kernel pack (never catalog.py / kernels.py). Every lab carries its own check: the kernel's answer against an
independent closed-form value, within 1 %. English only.
"""
from __future__ import annotations

from ..catalog import col, inst, lab
from .comp_ug import CHAP, DU22, DULOCF, GROUP, LEVEL, NR, SASTRY, SIM, _station

AS = {"title": "M. Abramowitz and I. A. Stegun, Handbook of Mathematical Functions (NBS)",
      "note": "recurrences and explicit forms of the Legendre, Laguerre, Hermite and Bessel functions; Gauss quadrature"}
ARFKEN = {"title": "G. B. Arfken, H. J. Weber, F. E. Harris, Mathematical Methods for Physicists",
          "note": "Fourier series, special functions, linear systems and eigenvalue problems"}
CT65 = {"title": "J. W. Cooley and J. W. Tukey, Math. Comput. 19, 297 (1965)",
        "note": "the fast Fourier transform algorithm"}
OPP = {"title": "A. V. Oppenheim and R. W. Schafer, Discrete-Time Signal Processing",
       "note": "the DTFT of a finite sequence and DFT samples with zero padding"}
CODATA = {"title": "CODATA 2022 recommended values (NIST): Hartree energy 27.211386245981 eV, mass ratios",
          "note": "physics.nist.gov/cuu/Constants"}
FLUGGE = {"title": "S. Fluegge, Practical Quantum Mechanics (Springer)",
          "note": "the Hulthen potential: the exactly solvable screened Coulomb potential, s-wave bound states"}
MORSE = {"title": "P. M. Morse, Phys. Rev. 34, 57 (1929)", "note": "the Morse potential and its exact vibrational levels"}
NIST_H2 = {"title": "NIST Chemistry WebBook, H2 ground state constants of diatomic molecules (Huber and Herzberg)",
           "note": "omega_e = 4401.213 cm^-1, omega_e x_e = 121.336 cm^-1; D0 is at most 36118.3 cm^-1"}

SAFE = ("A computational practical still has a discipline: write down the method, the setting of n and the error of "
        "every run before changing anything, and never report a number whose error you have not seen.")


def _cq(lab_id: str, title: str, topic: str, aim: str, kernel: str, params: dict, check_n: float, textbook: str,
        theory: str, steps: list[str], questions: list[dict], sources: list[dict], caption: str,
        unit: str = "", digits: int = 4, extra_check: dict | None = None) -> dict:
    chk = {"params": {"n": check_n}, "reading": "val", "textbook": textbook}
    if extra_check:
        chk["params"].update(extra_check)
    return lab(
        id=lab_id, rig="comp2-workstation", title=title, group=GROUP, level=LEVEL, topic=topic, chapter=CHAP,
        aim=aim, kernel=kernel, params=params, speed=1, speeds=[1],
        camera={"pos": [0.45, 0.42, 0.78], "look": [0.08, 0.17, -0.3]}, floor=-0.02,
        bodies=_station(caption),
        instruments=[inst("val", "readout", "Numerical answer", "val", unit=unit, digits=digits),
                     inst("exa", "readout", "Exact answer", "exact", unit=unit, digits=digits),
                     inst("err", "readout", "Relative error", "err", digits=6)],
        table={"columns": [col("n", "n (setting)", "manual", digits=0),
                           col("val", "Numerical answer", "manual", unit=unit, digits=digits),
                           col("err", "Relative error", "manual", digits=6)],
               "calc": "cq_best", "rows_min": 4, "result_digits": digits,
               "hint": "Run the method at several settings of n; the answer at the largest n is your result."},
        steps=steps, theory=theory, safety=SAFE, questions=questions, sources=sources, check=chk)


def _q(q, opts, ans, why):
    return {"q": q, "options": opts, "answer": ans, "why": why}


COMMON_STEPS = ["Read the method card: the problem, the methods allowed and the exact answer.",
                "Switch the workstation on.",
                "Choose the method and the setting n, then press Enter.",
                "Write down the answer and the error; change n and run again.",
                "Compare the runs: how does the error depend on n?"]


# ============================================================================================= Fourier series
def fourier_coefficients() -> dict:
    return _cq("cq-fourier-coefficients", "Fourier coefficients of periodic functions", "Fourier analysis",
               "Compute a Fourier coefficient of a square, triangle or rectified wave by numerical integration and "
               "compare it with its closed form.",
               "cq_fourier", {"cas": 0.0, "cidx": 0.0, "n": 64.0, "A": 1.0}, 256, "cq_fourier_c",
               "A periodic function f(t) of period 2 pi is a sum of sines and cosines, f = a0/2 + sum (ak cos kt + bk sin kt), "
               "with ak = (1/pi) integral of f cos kt and bk = (1/pi) integral of f sin kt over one period. A computer "
               "has only N samples of f, so each integral becomes a sum, ak ~ (2/N) sum f(tj) cos k tj. For a periodic "
               "function this trapezoid sum converges as 1/N^2 (faster if f is smooth). The waves in this practical have "
               "known coefficients, for example bk = 4A/(k pi) for the odd harmonics of a square wave, so the error of "
               "every run is real. The screen also adds up nine harmonics, and the overshoot near a jump (the Gibbs "
               "effect) shows that adding terms does not remove it.",
               COMMON_STEPS, [_q("A square wave of amplitude 1 has b1 equal to", ["4/pi", "2/pi", "1"], 0,
                                 "bk = 4A/(k pi) for odd k, so b1 = 4/pi = 1.273."),
                              _q("Doubling the number of samples divides the error by about", ["4", "2", "16"], 0,
                                 "The periodic trapezoid rule is second order: error ~ N^-2.")],
               [DU22, ARFKEN, SIM], "FOURIER COEFFICIENTS", digits=6)


def fourier_transform() -> dict:
    return _cq("cq-fourier-transform", "Fourier transform of common functions by DFT and FFT", "Fourier analysis",
               "Sample a square pulse, a cosine or a Gaussian, transform it with the direct DFT and with the FFT, and "
               "compare the spectrum with the exact Fourier transform.",
               "cq_dft", {"cas": 0.0, "method": 1.0, "n": 64.0, "L": 16.0, "a": 1.0, "f0": 0.55, "sg": 0.5, "nu": 0.25,
                          "numax": 1.0}, 512, "cq_dft_F",
               "Sampling f(t) at N points a distance dt apart turns the Fourier integral into the discrete Fourier "
               "transform, Xm = sum xj exp(-2 pi i j m / N), and F(nu_m) ~ dt Xm at nu_m = m/L where L = N dt is the "
               "window. The defining sum costs N^2 multiplications; the fast Fourier transform of Cooley and Tukey "
               "gives the same numbers in N log2 N. Two errors are real: the pulse has sharp edges, so the sum is only "
               "first or second order; and a function that is not periodic in the window leaks into neighbouring bins. "
               "A Gaussian is smooth, so its spectrum is almost exact until the sample spacing is too coarse and the "
               "tails fold back (aliasing).",
               COMMON_STEPS, [_q("The FFT and the direct DFT give", ["the same spectrum, the FFT far faster", "different spectra",
                                 "the same spectrum, the DFT faster"], 0, "The FFT is an exact rearrangement of the same sum."),
                              _q("The Fourier transform of a Gaussian is", ["a Gaussian", "a sinc", "a delta"], 0,
                                 "exp(-t^2/2s^2) transforms to s sqrt(2 pi) exp(-2 pi^2 s^2 nu^2).")],
               [DU22, CT65, ARFKEN, SIM], "DFT AND FFT", digits=6)


def dft_zero_padding() -> dict:
    return _cq("cq-dft-zero-padding", "DFT of a short sequence with zero padding", "Digital signal processing",
               "Take the DFT of the sequence 1, 1, 1, 1 padded with zeros to 4, 8 and 16 points and see how padding "
               "reveals the side-lobes of its spectrum.",
               "cq_dft", {"cas": 3.0, "method": 1.0, "n": 16.0}, 256, "cq_dft_F",
               "A finite sequence x[n] has one continuous spectrum, its DTFT X(w) = sum x[n] exp(-i w n). An N-point DFT "
               "only samples X(w) at w = 2 pi k / N. For x = 1, 1, 1, 1 the DTFT is |sin 2w / sin (w/2)|, a main lobe "
               "and side-lobes. The 4-point DFT lands exactly on the zeros of this curve and shows nothing but the "
               "main peak; padding with zeros to 8, 16 and more points samples the same curve more finely and the "
               "side-lobes appear. Padding adds no information, it interpolates the spectrum. The practical reads the "
               "largest side-lobe from the DFT and compares it with the maximum of the exact DTFT.",
               COMMON_STEPS, [_q("Zero padding a sequence to more points", ["samples its spectrum more finely", "improves the resolution of two close tones",
                                 "adds new information"], 0, "The DTFT is fixed by the data; padding only reads it at more points."),
                              _q("The 4-point DFT of 1, 1, 1, 1 is", ["4, 0, 0, 0", "1, 1, 1, 1", "0, 0, 0, 4"], 0,
                                 "A constant sequence has all its energy in the zero-frequency bin.")],
               [DULOCF, OPP, CT65, SIM], "DFT WITH ZERO PADDING", digits=6)


# ============================================================================================= Gauss quadrature
def gauss_quadrature() -> dict:
    return _cq("cq-gauss-quadrature", "Gauss-Legendre, Gauss-Laguerre and Gauss-Hermite quadrature", "Numerical integration",
               "Integrate with n well-chosen nodes and weights over a finite interval, a half line and the whole line, "
               "and watch the error fall away with n.",
               "cq_gauss", {"cas": 0.0, "method": 0.0, "n": 4.0, "wl": 1.0, "wh": 1.0}, 12, "cq_gauss_I",
               "A Gauss rule replaces the integral of w(x) f(x) by sum wi f(xi), choosing both the n nodes xi and the n "
               "weights wi so that every polynomial up to degree 2n-1 is integrated exactly. The nodes are the zeros of "
               "an orthogonal polynomial and depend on the weight function w(x): 1 on [-1, 1] (Legendre), exp(-x) on "
               "[0, infinity) (Laguerre) and exp(-x^2) on the whole line (Hermite). The nodes here are found by Newton's "
               "method on the three-term recurrence. For a smooth f the error falls faster than any power of n, so each "
               "added node gains roughly a constant number of digits.",
               COMMON_STEPS, [_q("An n-point Gauss rule is exact for polynomials up to degree", ["2n-1", "n", "n-1"], 0,
                                 "n nodes and n weights give 2n free numbers."),
                              _q("Gauss-Laguerre is the rule for integrals over", ["0 to infinity with weight exp(-x)", "the whole line", "-1 to 1"], 0,
                                 "Its weight function is exp(-x) on the half line.")],
               [DULOCF, AS, NR, SIM], "GAUSS QUADRATURE", digits=10)


# ============================================================================================= Schrodinger
def _sch_steps(what: str) -> list[str]:
    return ["Read the method card: the potential, the units and the exact energy.", "Switch the workstation on.",
            f"Choose the number of grid points N, then press Enter: the machine finds {what}.",
            "Write down the energy and the error; double N and run again.",
            "Compare the plotted wavefunction with the exact one, and note how the error falls with N."]


SCH_THEORY = ("For a central potential the radial function u(r) = r R(r) obeys -u'' /(2 mu) + [V + l(l+1)/(2 mu r^2)] u = E u "
              "with u = 0 at r = 0 and far away. On a grid r = jh the second derivative becomes (u[j+1] - 2u[j] + u[j-1])/h^2, "
              "and the equation is a tridiagonal matrix eigenvalue problem. The eigenvalues are found here without any "
              "library: the Sturm count says how many eigenvalues lie below a trial energy, and 100 bisections then "
              "home in on the one wanted; the wavefunction follows by inverse iteration. The discretisation error "
              "falls as h^2, that is as N^-2. ")


def schrodinger_hydrogen() -> dict:
    return _cq("cq-schrodinger-hydrogen", "Radial Schrodinger equation: hydrogen atom ground and first excited states",
               "Quantum mechanics by computation",
               "Solve the radial Schrodinger equation for the Coulomb potential on a grid and compare the energy with "
               "-13.6057 eV for the ground state.",
               "cq_schro", {"cas": 0.0, "kst": 0.0, "ll": 0.0, "n": 400.0, "mu": 1.0, "rmax": 40.0, "xd0": 0.0, "xd1": 14.0},
               1600, "cq_schro_E",
               SCH_THEORY + "For hydrogen the exact levels are En = -13.6057 eV / n^2 (infinite nuclear mass; a finite "
               "nucleus scales every level by the reduced mass).",
               _sch_steps("the ground state"),
               [_q("The ground-state energy of hydrogen is", ["-13.6 eV", "-27.2 eV", "-3.4 eV"], 0, "E1 = -13.6057 eV (half a Hartree)."),
                _q("Which levels share the energy -3.40 eV?", ["2s and 2p", "1s and 2s", "2p and 3p"], 0,
                   "En depends on n only for a pure Coulomb potential.")],
               [DULOCF, CODATA, SIM], "HYDROGEN ATOM, E", unit="eV", digits=6)


def schrodinger_screened() -> dict:
    return _cq("cq-schrodinger-screened", "Radial Schrodinger equation: screened Coulomb potential", "Quantum mechanics by computation",
               "Solve the radial equation for the screened Coulomb (Hulthen) potential and compare the energy with its "
               "exact value.",
               "cq_schro", {"cas": 1.0, "kst": 0.0, "ll": 0.0, "n": 800.0, "g": 10.0, "aa": 5.0, "rmax": 10.0, "xd0": 0.0, "xd1": 2.0},
               3200, "cq_schro_E",
               SCH_THEORY + "Screening by other charges turns the Coulomb potential into one that dies exponentially. The "
               "Hulthen potential V = -V0 exp(-r/a) / (1 - exp(-r/a)) is Coulomb-like near the nucleus and screened beyond "
               "a, and it is one of the few screened potentials with an exact s-wave solution: En = -(hbar^2/2ma^2)[(g - n^2)/2n]^2 "
               "with g = 2mV0a^2/hbar^2. The plain Yukawa potential has no closed form and is not used here.",
               _sch_steps("the lowest s level"),
               [_q("As the screening length a grows the levels", ["approach the hydrogen levels", "move to zero", "grow without limit"], 0,
                   "When a is large the potential is Coulomb over the whole atom."),
                _q("A bound level exists only while", ["g > n^2", "g < n^2", "g = 0"], 0, "Screening removes the highest levels first.")],
               [DULOCF, FLUGGE, CODATA, SIM], "SCREENED COULOMB, E", unit="eV", digits=6)


def schrodinger_morse() -> dict:
    return _cq("cq-schrodinger-morse", "Radial Schrodinger equation: Morse potential (H2 vibrations)", "Quantum mechanics by computation",
               "Solve the vibrational Schrodinger equation for the Morse potential with the constants of H2 and compare "
               "the level with the exact Morse formula.",
               "cq_schro", {"cas": 2.0, "kst": 0.0, "n": 800.0, "lam": 18.13647, "ymin": -0.6, "rmax": 2.5, "e0": 121.336,
                            "xd0": -0.5, "xd1": 1.5}, 3200, "cq_schro_E",
               SCH_THEORY + "The Morse potential V = De (1 - exp(-a(r - re)))^2 describes a bond that can break. In units of "
               "eps0 = hbar^2 a^2 / 2 mu the only parameter is lambda = sqrt(De/eps0), and the exact levels lie below "
               "dissociation by eps0 (lambda - v - 1/2)^2. The constants of H2 give lambda = we/(2 we xe) and eps0 = we xe; "
               "the model D0 comes out about 4 % above the measured one, which is the limit of the Morse model, not of the solver.",
               _sch_steps("the lowest vibrational level"),
               [_q("A Morse oscillator has", ["unequally spaced levels that crowd together", "equally spaced levels", "one level"], 0,
                   "The anharmonic term lowers the energy of high levels."),
                _q("The binding energy of the v = 0 level is called", ["D0", "De", "omega_e"], 0, "D0 = De minus the zero-point energy.")],
               [DULOCF, MORSE, NIST_H2, SIM], "MORSE POTENTIAL, H2", unit="cm-1", digits=6)


# ============================================================================================= special functions
def legendre_recurrence() -> dict:
    return _cq("cq-legendre-recurrence", "Legendre polynomials from their recurrence relation", "Special functions",
               "Build Pn(x) from the three-term recurrence and compare it with the explicit polynomial.",
               "cq_special", {"cas": 0.0, "method": 0.0, "n": 6.0, "x": 0.6, "xa": -1.0, "xb": 1.0}, 12, "cq_special_v",
               "The Legendre polynomials satisfy (k+1)P(k+1) = (2k+1) x P(k) - k P(k-1) with P0 = 1 and P1 = x. Starting from "
               "two values, every higher degree costs one multiplication and one subtraction, so a program needs no "
               "formula for P12. The same polynomial has the explicit sum Pn = 2^-n sum (-1)^k C(n,k) C(2n-2k,n) x^(n-2k), which "
               "is used here as the reference. For |x| <= 1 the recurrence is stable: the two curves lie on top of "
               "each other and the error is round-off.",
               COMMON_STEPS, [_q("P2(x) equals", ["(3x^2 - 1)/2", "x^2", "3x/2"], 0, "From the recurrence: 3x*x - 1 over 2."),
                              _q("P(n)(1) equals", ["1 for every n", "n", "0"], 0, "Every Legendre polynomial equals 1 at x = 1.")],
               [DU22, AS, ARFKEN, SIM], "LEGENDRE RECURRENCE", digits=10)


def legendre_orthogonality() -> dict:
    return _cq("cq-legendre-orthogonality", "Orthogonality of Legendre polynomials", "Special functions",
               "Integrate Pn squared and Pn times Pn+2 numerically and compare with 2/(2n+1) and 0.",
               "cq_special", {"cas": 1.0, "method": 1.0, "n": 8.0, "deg": 4.0, "x": 0.6}, 256, "cq_special_v",
               "Legendre polynomials are orthogonal on [-1, 1]: the integral of Pm Pn is 0 for m different from n and "
               "2/(2n+1) for m = n. A program can only test this with a quadrature rule. The trapezoid rule (order 2) and "
               "Simpson's rule (order 4) need many strips; Gauss-Legendre needs only n+1 nodes for Pn squared, because the "
               "integrand is a polynomial of degree 2n. With exactly n nodes the rule samples Pn only at its own zeros and "
               "the integral comes out as zero: a good reminder that a quadrature rule must be matched to the integrand.",
               COMMON_STEPS, [_q("The integral of P3 squared over [-1, 1] is", ["2/7", "2/3", "1"], 0, "2/(2n+1) with n = 3."),
                              _q("Gauss-Legendre with n nodes is exact up to degree", ["2n-1", "n", "n+1"], 0,
                                 "So P4 squared (degree 8) needs 5 nodes.")],
               [DU22, AS, ARFKEN, NR, SIM], "ORTHOGONALITY OF Pn", digits=8)


def special_functions() -> dict:
    return _cq("cq-special-functions", "Special functions and their recurrence relations", "Special functions",
               "Compute Bessel, Legendre, Laguerre and Hermite functions from their recurrences and see when a recurrence "
               "is stable and when it is not.",
               "cq_special", {"cas": 4.0, "method": 1.0, "n": 6.0, "x": 2.0, "xa": 0.1, "xb": 8.0}, 10, "cq_special_v",
               "Each family has a three-term recurrence: Bessel J(k+1) = (2k/x) J(k) - J(k-1), Laguerre (k+1)L(k+1) = (2k+1-x)L(k) - kL(k-1), "
               "Hermite H(k+1) = 2xH(k) - 2kH(k-1). Run upward from the first two members, a recurrence is cheap, but it is "
               "only safe if the wanted solution is the dominant one. For Bessel functions with n larger than x the "
               "solution J(n) is the minor one, so rounding errors in J0 and J1 grow like the other solution Y(n) and "
               "the upward result is ruined. Miller's trick runs the recurrence downward from far above n and normalises "
               "with J0 + 2 sum J(2k) = 1; the reference is the power series.",
               COMMON_STEPS, [_q("Upward recurrence for J(n)(x) with n much larger than x is", ["unstable", "stable", "exact"], 0,
                                 "The wanted solution is the minor one; the error grows like Y(n)."),
                              _q("Miller's algorithm runs the recurrence", ["downward", "upward", "sideways"], 0,
                                 "Going down, J(n) is the dominant solution.")],
               [DULOCF, AS, ARFKEN, SIM], "SPECIAL FUNCTIONS", digits=10)


# ============================================================================================= linear algebra
def kirchhoff_linear_system() -> dict:
    return _cq("cq-kirchhoff-linear-system", "Mesh equations of a circuit by Gauss elimination and Gauss-Seidel", "Linear algebra",
               "Write Kirchhoff's voltage law for three loops as a 3 by 3 system and solve it by Gauss elimination and by "
               "the Gauss-Seidel iteration.",
               "cq_linsys", {"cas": 0.0, "method": 1.0, "n": 6.0, "pick": 0.0}, 40, "cq_linsys_x",
               "Kirchhoff's voltage law around each of three loops gives R I = E, where the diagonal of R is the total "
               "resistance in a loop and an off-diagonal entry is minus the resistance shared by two loops. Gauss "
               "elimination removes the unknowns one by one (with the largest pivot first) and back-substitutes; it is direct "
               "and finishes in a fixed number of steps. Gauss-Seidel instead updates each current from the latest values "
               "of the others and repeats; it converges for a diagonally dominant system, such as this one, by a constant "
               "factor each sweep. The reference is Cramer's rule, an independent route.",
               COMMON_STEPS, [_q("Gauss-Seidel is guaranteed to converge for a matrix that is", ["diagonally dominant", "symmetric only", "singular"], 0,
                                 "Strict diagonal dominance is a sufficient condition."),
                              _q("Partial pivoting in Gauss elimination avoids", ["dividing by a small number", "reading the data", "iterations"], 0,
                                 "It puts the largest entry on the diagonal.")],
               [DU22, ARFKEN, SASTRY, SIM], "KIRCHHOFF LOOP EQUATIONS", digits=8)


def coupled_spring_linear_system() -> dict:
    return _cq("cq-coupled-springs", "Coupled spring-mass system as a linear system", "Linear algebra",
               "Find the static displacements of three masses joined by springs from K x = F, by Gauss elimination and "
               "Gauss-Seidel.",
               "cq_linsys", {"cas": 1.0, "method": 1.0, "n": 6.0, "pick": 1.0}, 40, "cq_linsys_x",
               "Three masses hang between two walls on four springs. At equilibrium the net force on each mass is zero, "
               "which gives K x = F with K tridiagonal: the diagonal is the sum of the two springs that touch the mass and "
               "the off-diagonals are minus the shared spring constant. The matrix is symmetric and diagonally "
               "dominant, so Gauss-Seidel converges, and the error of the iteration falls by a fixed factor every sweep. "
               "The reference is Cramer's rule. The same matrix, with the masses, gives the normal modes of the chain.",
               COMMON_STEPS, [_q("The stiffness matrix of a spring chain is", ["symmetric and tridiagonal", "diagonal", "antisymmetric"], 0,
                                 "Each mass touches only its two neighbours."),
                              _q("Doubling every spring constant makes every displacement", ["half as large", "twice as large", "unchanged"], 0,
                                 "x = K^-1 F, and K doubles.")],
               [DU22, ARFKEN, SASTRY, SIM], "COUPLED SPRINGS, K x = F", digits=8)


def eigenvalue_power() -> dict:
    return _cq("cq-eigenvalue-power", "Largest and smallest eigenvalues by the power and inverse power methods", "Linear algebra",
               "Find the largest and smallest eigenvalues of the coupled-oscillator matrix by the power and the inverse "
               "power methods and compare them with the exact values.",
               "cq_eig", {"cas": 0.0, "method": 0.0, "n": 10.0, "mdim": 6.0}, 80, "cq_eig_l",
               "Repeated multiplication by a matrix A turns almost any vector toward the eigenvector of the largest "
               "eigenvalue, v -> Av / |Av|, and the Rayleigh quotient v.Av / v.v gives that eigenvalue. The error falls "
               "by the ratio of the second to the first eigenvalue each step. Solving A w = v instead of multiplying "
               "gives the inverse power method, which finds the smallest eigenvalue. The test matrix tridiag(-1, 2, -1) is "
               "the chain of equal masses and springs; its exact eigenvalues 2 - 2 cos(k pi/(M+1)) are the squared normal-mode "
               "frequencies.",
               COMMON_STEPS, [_q("The power method converges slowly when", ["the two largest eigenvalues are nearly equal", "the matrix is small", "the start vector is long"], 0,
                                 "The error factor per step is lambda2 / lambda1."),
                              _q("The inverse power method finds the", ["smallest eigenvalue", "largest eigenvalue", "trace"], 0,
                                 "A^-1 has the largest eigenvalue 1/lambda_min.")],
               [DULOCF, ARFKEN, NR, SIM], "POWER METHOD", digits=8)


def principal_axes() -> dict:
    return _cq("cq-principal-axes", "Principal axes of a moment of inertia tensor by diagonalisation", "Linear algebra",
               "Diagonalise the inertia tensor of a tilted block by Jacobi rotations and compare the smallest principal "
               "moment with the exact one.",
               "cq_eig", {"cas": 2.0, "method": 0.0, "n": 2.0, "mass": 1.0, "sa": 1.0, "sb": 2.0, "sc": 3.0,
                          "th1": 0.6, "th2": 0.4, "th3": 0.9}, 5, "cq_eig_l",
               "Rotating a body changes the nine numbers of its inertia tensor but not its principal moments, which are the "
               "eigenvalues. A uniform cuboid of sides a, b, c has principal moments m(b^2+c^2)/12 and its two cyclic "
               "partners about the three axes through its centre; turning the axes by three Euler angles hides them in a full "
               "matrix. Jacobi's method removes the off-diagonal entries one at a time by plane rotations; each sweep "
               "through the three pairs makes the off-diagonal part much smaller, and the diagonal then holds the "
               "eigenvalues. The exact answer is known from the sides.",
               COMMON_STEPS, [_q("The principal moments of a body are the", ["eigenvalues of its inertia tensor", "diagonal entries in any axes", "masses"], 0,
                                 "In the principal axes the tensor is diagonal."),
                              _q("A Jacobi rotation is chosen to", ["zero one off-diagonal entry", "scale the matrix", "invert the matrix"], 0,
                                 "It is a plane rotation by the angle that kills a(p,q).")],
               [DULOCF, ARFKEN, NR, SIM], "PRINCIPAL AXES", digits=8)


# ============================================================================================= nonlinear dynamics
MAY = {"title": "R. M. May, Nature 261, 459 (1976): Simple mathematical models with very complicated dynamics"}
FEIG = {"title": "M. J. Feigenbaum, J. Stat. Phys. 19, 25 (1978): Quantitative universality for a class of nonlinear transformations",
        "note": "delta = 4.669201609... (OEIS A006890)"}
LORENZ = {"title": "E. N. Lorenz, J. Atmos. Sci. 20, 130 (1963): Deterministic nonperiodic flow",
          "note": "sigma = 10, beta = 8/3, rho = 28 and the strange attractor"}
STROG = {"title": "S. H. Strogatz, Nonlinear Dynamics and Chaos", "note": "the logistic map, the Lorenz equations and the divergence of a flow"}


def logistic_map() -> dict:
    return _cq("cq-logistic-map", "Period-doubling route to chaos in the logistic map", "Nonlinear dynamics",
               "Find the parameter at which the logistic map x -> r x (1 - x) first doubles its period, and compare it with r = 3.",
               "cq_map", {"cas": 0.0, "n": 1000.0}, 4000, "cq_map_r",
               "The logistic map x -> r x (1 - x) has a fixed point that is stable for r < 3. At r = 3 it loses stability and "
               "an orbit of period 2 takes over; at r = 1 + sqrt(6) = 3.4495 this doubles again, and the doublings pile up "
               "geometrically towards chaos, the ratio of successive intervals tending to Feigenbaum's delta = 4.6692. The program "
               "cannot see an instability, only an orbit: it iterates T times, asks whether the orbit has settled to period 1 "
               "(or 2), and bisects on r. Close to the bifurcation the orbit settles very slowly (critical slowing down), so "
               "the value found lies below the true point by about 16/T: it approaches r = 3 only as T grows.",
               ["Read the method card: the map and the quantity to find.", "Switch the workstation on.",
                "Choose T, the number of iterations given to each trial value of r, then press Enter.",
                "Write down the r found and its error; double T and run again.",
                "Look at the bifurcation diagram: the branch points are where the dots split."],
               [_q("The first period doubling of the logistic map is at r =", ["3", "2", "4"], 0, "At r = 3 the slope of the map at the fixed point is -1."),
                _q("Why does a short run give a value below 3?", ["near r = 3 the orbit settles very slowly", "the map is wrong", "round-off"], 0,
                   "Critical slowing down: the error shrinks only as (1 - epsilon)^T.")],
               [DULOCF, MAY, STROG, SIM], "LOGISTIC MAP", digits=6)


def lorenz_attractor() -> dict:
    return _cq("cq-lorenz-attractor", "Attractors of the Lorenz equations", "Nonlinear dynamics",
               "Integrate the Lorenz equations together with their variational equations and check that phase-space volume "
               "shrinks exactly as exp(-(sigma + 1 + beta) t).",
               "cq_lorenz", {"n": 20.0, "sg": 10.0, "rho": 28.0, "be": 8.0 / 3.0, "T": 1.0}, 320, "cq_lorenz_det",
               "The Lorenz equations x' = sigma (y - x), y' = x (rho - z) - y, z' = x y - beta z have a flow with divergence "
               "-(sigma + 1 + beta), a constant. A small blob of initial conditions therefore shrinks in volume like "
               "exp(-(sigma + 1 + beta) t) whatever the trajectory does, which is why the attractor has zero volume and a "
               "fractal shape. The program integrates the 3 x 3 matrix Phi of the variational equation Phi' = J Phi beside "
               "the trajectory by fourth-order Runge-Kutta; det Phi(T) is the volume factor and is compared with the exact "
               "exponential. The screen shows the attractor (x against z) and its fixed points; for rho below 24.74 the "
               "orbit spirals into one of them instead.",
               ["Read the method card: the equations and the parameters.", "Switch the workstation on.",
                "Choose the number of Runge-Kutta steps n for the interval T, then press Enter.",
                "Write down det Phi(T) and its error; double n and run again.",
                "Compare the measured order with 4, the order of the Runge-Kutta method."],
               [_q("The divergence of the Lorenz flow is", ["-(sigma + 1 + beta)", "zero", "sigma"], 0, "Add the diagonal of the Jacobian: -sigma - 1 - beta."),
                _q("A flow whose divergence is negative has an attractor with", ["zero volume", "unit volume", "infinite volume"], 0,
                   "Volumes shrink to zero, so a strange attractor is a set of zero volume.")],
               [DULOCF, LORENZ, STROG, SIM], "LORENZ ATTRACTOR", digits=8)


# ============================================================================================= differential equations
def bvp_ode() -> dict:
    return _cq("cq-bvp-ode", "Boundary value problems by finite difference and shooting", "Differential equations",
               "Solve y'' + y = 0 with y(0) = 0 and y(L) = 1 by finite differences and by shooting, and compare y(L/2) with the exact solution.",
               "cq_bvp", {"cas": 0.0, "method": 0.0, "n": 8.0, "L": 1.5, "B": 1.0}, 64, "cq_bvp_y",
               "In a boundary value problem the conditions sit at two different points, so the equation cannot be marched "
               "forward from a start. The finite-difference method replaces y'' by (y[j+1] - 2y[j] + y[j-1])/h^2 at every grid "
               "point and solves the resulting tridiagonal system at once; its error is of order h^2. Shooting guesses the "
               "missing initial slope, integrates forward by Runge-Kutta, and corrects the guess until y(L) hits the boundary "
               "value; for a linear equation the secant rule needs only two shots. The test problem y'' + y = 0 has the solution "
               "sin x / sin L, and y'' - y = 0 (reaction-diffusion) has sinh x / sinh L.",
               COMMON_STEPS, [_q("Finite differences turn a boundary value problem into", ["a tridiagonal linear system", "a single number", "an integral"], 0,
                                 "One equation per interior grid point, each linking three neighbours."),
                              _q("Shooting for a linear equation needs", ["two trial shots", "one shot", "a thousand shots"], 0,
                                 "The end value is linear in the guessed slope, so two shots fix it.")],
               [DULOCF, NR, SASTRY, SIM], "BOUNDARY VALUE PROBLEM", digits=8)


def pde_laplace_heat_wave() -> dict:
    return _cq("cq-pde-laplace", "Laplace, wave and heat equations by finite differences", "Differential equations",
               "Solve Laplace's equation on a square plate by relaxation, and compare the centre value with the separable exact solution.",
               "cq_pde", {"cas": 0.0, "method": 2.0, "n": 10.0, "al": 1.0, "dt": 0.002, "T": 0.1, "cw": 1.0, "nu": 0.8}, 40, "cq_pde_u",
               "A potential in a charge-free region obeys Laplace's equation, which on a grid says that every value is the average "
               "of its four neighbours. Starting from zeros and sweeping over the grid until nothing changes is relaxation: Jacobi "
               "uses the old values, Gauss-Seidel the newest, and successive over-relaxation (SOR) overshoots each update by an optimal "
               "factor and needs far fewer sweeps. With the top edge at sin(pi x) and the other edges at 0 the exact solution is "
               "sin(pi x) sinh(pi y)/sinh(pi). The heat and wave equations of this practical use the same grid in space and "
               "march in time: explicit schemes are unstable beyond a limit on the time step, the implicit and Crank-Nicolson schemes are not.",
               COMMON_STEPS, [_q("SOR converges faster than Gauss-Seidel because it", ["over-corrects each update by a chosen factor", "uses fewer grid points", "changes the equation"], 0,
                                 "The optimal factor is near 2 for a fine grid."),
                              _q("An explicit scheme for the heat equation is unstable when", ["alpha dt / h^2 exceeds 1/2", "dt is very small", "h is large"], 0,
                                 "Finer grids need much smaller time steps.")],
               [DULOCF, NR, SIM], "LAPLACE, HEAT AND WAVE", digits=8)


# ============================================================================================= radiation
PLANCK_SRC = {"title": "SI Brochure (BIPM), 9th edition: h, k and c have exact values since 2019",
              "note": "h = 6.62607015e-34 J s, k = 1.380649e-23 J/K, c = 299792458 m/s"}
CODATA_W = {"title": "CODATA 2022 (NIST): Stefan-Boltzmann constant 5.670374419e-8 W m^-2 K^-4, Wien constant 2.897771955e-3 m K",
            "note": "both follow from the exact h, k and c"}


def planck_law() -> dict:
    return _cq("cq-planck-law", "Planck's law compared with Rayleigh-Jeans and Wien laws", "Radiation",
               "Find the peak of Planck's spectrum for a body at 5772 K by golden-section search and compare it with Wien's displacement law.",
               "cq_planck", {"cas": 1.0, "n": 40.0, "T": 5772.0}, 80, "cq_planck_v",
               "Planck's law gives the power a black body emits per unit area and wavelength, M = 2 pi h c^2 / (lambda^5 (exp(hc/lambda k T) - 1)). "
               "Its peak is where the derivative vanishes, which leads to (x - 5) e^x + 5 = 0 for x = hc/(lambda k T); the root x = 4.9651 gives "
               "Wien's displacement law lambda_max T = 2.8978e-3 m K. The program finds the peak without the algebra, by golden-section search, "
               "and the practical compares it with the root of that equation. At long wavelengths Planck's law becomes the Rayleigh-Jeans law and "
               "at short ones Wien's law: at the peak the first is 28.7 times too high and the second 0.7 % too low. Integrating over all "
               "wavelengths gives the Stefan-Boltzmann law, M = sigma T^4.",
               COMMON_STEPS, [_q("The peak wavelength of a body at 5772 K is about", ["500 nm", "5 um", "50 nm"], 0, "2.898e-3 m K divided by 5772 K."),
                              _q("The Rayleigh-Jeans law fails at short wavelengths because it", ["grows without limit (ultraviolet catastrophe)", "is too small", "has no peak"], 0,
                                 "It goes as 1/lambda^4, so the total power would be infinite.")],
               [DULOCF, PLANCK_SRC, CODATA_W, SIM], "PLANCK'S LAW", unit="m", digits=6)


# ============================================================================================= data analysis
def least_squares_fitting() -> dict:
    return _cq("cq-least-squares", "Least-squares fitting with parameter uncertainties", "Data analysis",
               "Fit a straight line to noisy data with weights from the known errors and compare the slope with the law the data were made from.",
               "cq_fit", {"cas": 0.0, "wt": 1.0, "n": 200.0, "seed": 2024.0, "sig": 0.04, "x0": 1.0, "x1": 10.0, "a0": 2.0, "b0": 3.0, "c0": 0.5},
               3000, "cq_fit_p",
               "Least squares chooses the parameters that minimise the sum of w_i (y_i - f(x_i))^2, with weights w_i = 1/sigma_i^2 when the "
               "error of each point is known. For a model linear in its parameters this leads to the normal equations (A^T W A) c = A^T W y, "
               "solved here by Gauss elimination; the diagonal of the inverse of A^T W A gives the uncertainty of each parameter. A power law "
               "y = A x^b becomes a straight line in ln y against ln x, and an exponential y = A exp(-x/tau) in ln y against x. The data are made by a "
               "seeded generator from a known law with 4 % noise, so the fitted parameter has a real error that shrinks as 1/sqrt(N).",
               COMMON_STEPS, [_q("The uncertainty of a fitted slope falls with the number of points N as", ["1/sqrt(N)", "1/N", "it does not change"], 0,
                                 "Averaging N independent points divides the scatter by sqrt(N)."),
                              _q("A power law y = A x^b becomes a straight line in", ["ln y against ln x", "y against x", "y against ln x"], 0,
                                 "ln y = ln A + b ln x.")],
               [DU22, ARFKEN, NR, SIM], "LEAST SQUARES", digits=6)


BUILDERS = (fourier_coefficients, fourier_transform, dft_zero_padding, gauss_quadrature,
            schrodinger_hydrogen, schrodinger_screened, schrodinger_morse,
            legendre_recurrence, legendre_orthogonality, special_functions,
            kirchhoff_linear_system, coupled_spring_linear_system, eigenvalue_power, principal_axes,
            logistic_map, lorenz_attractor, bvp_ode, pde_laplace_heat_wave, planck_law, least_squares_fitting)
