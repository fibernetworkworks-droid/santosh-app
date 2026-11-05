"""Prayogshala lab pack: the M.Sc. / Ph.D. "Computational physics" practicals (University of Delhi PH-DSE5221 and PH-DSE5142
lists, and the standard research methods: Monte Carlo, molecular-lattice models, FDTD, PIC, N-body, MCMC).

One rig serves them all - `app/static/prayog/exp/comp3-workstation.js`, the same real workstation as the B.Sc. pack (desk
mat, monitor, keyboard, tower, printed method card) with a lattice / phase-space / orbit / band-structure / histogram view
in the corner of the screen. The student reads the card, switches the machine on, chooses a method and a size (grid,
step, number of samples, sweeps) and presses Enter. Each run is a reading in the record book: the answer, the reference
value and the error; the result of the practical is the run with the smallest error and the way the error falls.

Physics: the `comp3_adv` kernel pack (never catalog.py / kernels.py). Every lab carries its own check: the kernel's answer
against an exact analytic value, within 1 % - or, for a statistical result, within the tolerance stated on the lab (a
Binder-cumulant crossing is a few per cent). English only.
"""
from __future__ import annotations

import math

from ..catalog import B, col, inst, lab

SIM = {"title": "Hoola Prayogshala kernel", "note": "the numbers come from the simulation code; checked against the "
                                                    "reference value in Hoola's tests"}
DU25 = {"title": "University of Delhi, M.Sc. Physics (coursework with research) 2025-26, PH-DSE5221 Advanced Numerical Techniques / "
                 "PH-DSE5142 Computational Material Science",
        "note": "the syllabus lists these methods; the formulas here are the standard textbook forms"}
SASTRY = {"title": "S. S. Sastry, Introductory Methods of Numerical Analysis, PHI",
          "note": "standard interpolation, root-finding and finite-difference formulas; cited from the textbook, not re-fetched"}
NR = {"title": "W. H. Press, S. A. Teukolsky, W. T. Vetterling, B. P. Flannery, Numerical Recipes, 3rd ed. (Cambridge University Press)",
      "note": "Thomas algorithm, Numerov, Jacobi, golden-section, Lanczos and Metropolis methods in their standard forms; cited, not re-fetched"}
NB = {"title": "M. E. J. Newman and G. T. Barkema, Monte Carlo Methods in Statistical Physics (Oxford University Press, 1999)",
      "note": "Metropolis and Wolff algorithms, Binder cumulant; cited from the book, not re-fetched"}
ONSAGER = {"title": "L. Onsager, Phys. Rev. 65, 117 (1944); C. N. Yang, Phys. Rev. 85, 808 (1952)",
           "note": "exact energy and spontaneous magnetisation of the 2-D Ising model; Tc = 2/ln(1+sqrt 2) J/kB. Formulas cited, not re-fetched"}
FS = {"title": "D. Frenkel and B. Smit, Understanding Molecular Simulation, 2nd ed. (Academic Press, 2002)", "note": "cited, not re-fetched"}
GIORDANO = {"title": "N. J. Giordano and H. Nakanishi, Computational Physics, 2nd ed. (Pearson, 2006)", "note": "cited, not re-fetched"}

GROUP = "Physics · Computational"
CHAP = "Computational physics"


def _station(caption: str) -> list[dict]:
    """The workstation as LSL data. The realistic bench is the studio rig; this keeps the lab openable on its own."""
    return [
        B("mat", "box", name="Desk mat", size=[0.9, 0.004, 0.45], pos=[0.05, 0.002, -0.12], color="black", cut=False),
        B("foot", "box", name="Monitor stand", size=[0.22, 0.012, 0.14], pos=[0.08, 0.008, -0.42], color="#2b2f36"),
        B("neck", "cylinder", r=0.016, h=0.1, pos=[0.08, 0.06, -0.42], color="#2b2f36"),
        B("bezel", "box", name="Monitor", info="The plot, the picture in the corner and the run log appear here.",
          size=[0.36, 0.235, 0.016], pos=[0.08, 0.225, -0.4], color="#17181b"),
        B("screen", "plane", name="Screen", info="Left: the reference and what the method built. Right: the run log.",
          size=[0.33, 0.2], pos=[0.08, 0.228, -0.391], color="#0d1b2a"),
        B("kbd", "box", name="Keyboard", info="Enter runs the method at the settings you chose.",
          size=[0.33, 0.014, 0.12], pos=[0.08, 0.007, -0.1], color="#1b1b1d"),
        B("mouse", "box", name="Mouse", size=[0.058, 0.022, 0.095], pos=[0.31, 0.011, -0.1], color="#1b1b1d"),
        B("tower", "box", name="Workstation", info="The computer that runs the method you choose.",
          size=[0.17, 0.34, 0.36], pos=[-0.56, 0.17, -0.45], color="#2b2f36"),
        B("card", "plane", name="Method card", info="The printed card on the bench: the problem and the formulas.",
          size=[0.15, 0.21], pos=[0.52, 0.001, -0.04], rot=[-1.5708, 0, 0], color="white"),
        B("cap", "text", text=caption, size=0.018, pos=[0.08, 0.37, -0.4]),
    ]


def _cr(lab_id: str, title: str, topic: str, aim: str, kernel: str, params: dict, check_n: float, textbook: str,
        theory: str, steps: list[str], questions: list[dict], sources: list[dict], caption: str,
        unit: str = "", digits: int = 5, level: str = "M.Sc.", tol: float = 0.01, extra_check: dict | None = None) -> dict:
    chk = {"params": {"n": check_n}, "reading": "val", "textbook": textbook}
    if tol != 0.01:
        chk["tol"] = tol
    if extra_check:
        chk["params"].update(extra_check)
    return lab(
        id=lab_id, rig="comp3-workstation", title=title, group=GROUP, level=level, topic=topic, chapter=CHAP,
        aim=aim, kernel=kernel, params=params, speed=1, speeds=[1],
        camera={"pos": [0.45, 0.42, 0.78], "look": [0.08, 0.17, -0.3]}, floor=-0.02,
        bodies=_station(caption),
        instruments=[inst("val", "readout", "Computed answer", "val", unit=unit, digits=digits),
                     inst("exa", "readout", "Reference value", "exact", unit=unit, digits=digits),
                     inst("err", "readout", "Relative error", "err", digits=6)],
        table={"columns": [col("n", "n (size / samples)", "manual", digits=0),
                           col("val", "Computed answer", "manual", unit=unit, digits=digits),
                           col("err", "Relative error", "manual", digits=6)],
               "calc": "cr_best", "rows_min": 4, "result_digits": digits,
               "hint": "Run the method at several settings of n; report the run with the smallest error."},
        steps=steps, theory=theory,
        safety="A computational practical still has a discipline: write down the method, the setting of n, the seed and the "
               "error of every run before changing anything, and never report a number whose error you have not seen.",
        questions=questions, sources=sources, check=chk,
    )


def _q(q: str, options: list[str], why: str) -> dict:
    return {"q": q, "options": options, "answer": 0, "why": why}


def _steps(read: str, last: str) -> list[str]:
    return [read, "Switch the workstation on.", "Choose a method and a size n, then press Enter.",
            "Write down the answer and the error; change n and run again, at four settings or more.", last]


# ============================================================================================ M.Sc.
def interpolation() -> dict:
    return _cr("cr-interpolation", "Lagrange and cubic-spline interpolation", "Numerical methods",
               "Interpolate a function from n + 1 equally spaced values by a Lagrange polynomial and by a cubic spline, "
               "and compare both with the exact value.", "cr_interp",
               {"cas": 0.0, "method": 0.0, "n": 8.0, "x": 1.3, "xa": 0.0, "xb": math.pi}, 8, "cr_interp_f",
               "Given f at n + 1 nodes, the Lagrange polynomial is the one polynomial of degree n through all of them. For a "
               "smooth function its error is f^(n+1)(xi)/(n+1)! times the product of (x - x_i), which falls quickly with n for "
               "sin x but not for every function: through equally spaced nodes the polynomial of 1/(1+25x^2) oscillates "
               "wildly near the ends and gets worse as n grows (Runge's phenomenon). A cubic spline joins n cubic pieces so "
               "that f, f' and f'' are continuous; its error falls as h^4 and never oscillates.",
               _steps("Read the function, the interval and the point x from the method card.",
                      "Compare the two methods at the same n, and note which one improves smoothly."),
               [_q("A cubic spline has continuous", ["value, slope and curvature", "value only", "all derivatives"],
                   "Matching f, f' and f'' at every node gives the n - 1 conditions that, with the two end slopes, fix the spline."),
                _q("Raising the degree of an equal-spaced Lagrange polynomial can make the error larger because",
                   ["the product of (x - x_i) grows near the ends", "the nodes move", "rounding disappears"],
                   "The interpolation error contains the node polynomial, which is large near the ends for equal spacing.")],
               [DU25, SASTRY, SIM], "INTERPOLATION", digits=8)


def finite_difference_pde() -> dict:
    return _cr("cr-finite-difference-pde", "Finite-difference heat and wave equations", "Numerical methods",
               "Solve the heat equation and the wave equation on a string or rod by an explicit and an implicit "
               "(Crank-Nicolson) scheme, and find the stability limit.", "cr_pde",
               {"cas": 0.0, "method": 0.0, "n": 40.0, "tend": 0.5, "c": 0.1, "r": 0.4, "xp": 0.3}, 80, "cr_pde_u",
               "Replace u_xx by (u_(j+1) - 2u_j + u_(j-1))/dx^2. The explicit heat scheme u' = u + r(...) with r = c dt/dx^2 is "
               "easy but stable only for r <= 1/2; above that the highest mode grows by |1 - 4r| every step and wrecks the "
               "answer. Crank-Nicolson averages the old and new levels, needs a tridiagonal solve each step, and is stable for "
               "every r. The wave equation behaves the same way: the explicit leapfrog needs the Courant number nu = c dt/dx "
               "<= 1 and the implicit (Newmark) average of three time levels does not. Both are second order in dx.",
               _steps("Read the equation, the stability number and the point x from the method card.",
                      "Repeat with the other method, and see what a stability number above the limit does to the explicit one."),
               [_q("The explicit heat scheme is stable only if", ["c dt/dx^2 <= 1/2", "dt is as large as possible", "dx is as large as possible"],
                   "Von Neumann analysis gives an amplification factor 1 - 4r sin^2(k dx/2), which must stay within 1."),
                _q("Crank-Nicolson is called unconditionally stable because", ["its amplification factor never exceeds 1 in size", "it is explicit", "it needs no boundary"],
                   "The averaged scheme has factor (1 - 2r s)/(1 + 2r s) with s = sin^2(k dx/2), always between -1 and 1.")],
               [DU25, SASTRY, SIM], "FINITE DIFFERENCES", digits=6)


def finite_element_intro() -> dict:
    return _cr("cr-finite-element-intro", "Introduction to the finite element method", "Numerical methods",
               "Solve the 1-D Poisson equation -u'' = f with linear elements on meshes of n cells and see how the error "
               "falls with the mesh size.", "cr_fem", {"cas": 0.0, "method": 0.0, "n": 8.0, "xp": 0.4}, 32, "cr_fem_u",
               "Multiply -u'' = f by a test function, integrate by parts and expand u in hat functions: this gives the matrix "
               "equation K u = b with K_ii = 2/h, K_i,i+1 = -1/h and b_i = integral of f times the i-th hat function. The "
               "matrix is tridiagonal, so it is solved at once by the Thomas algorithm. Between nodes the solution is the "
               "straight line through the nodal values, so the error of linear elements is second order, falling as h^2. For "
               "f = 1 the nodal values are exact (a special property of 1-D linear elements), and the whole error is the "
               "interpolation between them.",
               _steps("Read the equation and the point x from the method card.", "Halve h several times and watch the error fall by four."),
               [_q("Doubling the number of linear elements changes the error by about", ["a factor 4 smaller", "a factor 2 smaller", "nothing"],
                   "The piecewise-linear interpolation error is proportional to h^2."),
                _q("Why is the stiffness matrix tridiagonal?", ["a hat function overlaps only its two neighbours", "the equation is linear", "the mesh is uniform"],
                   "The integral of the product of two hat functions is zero unless they share an element.")],
               [DU25, NR, SIM], "FINITE ELEMENTS", digits=8)


def least_squares_fit() -> dict:
    return _cr("cr-least-squares-fit", "Least-squares fitting with and without errors", "Data analysis",
               "Fit a straight line (equal and unequal errors) and a parabola to seeded noisy data and measure how the "
               "error of the fitted parameter falls with the number of points.", "cr_fit",
               {"cas": 0.0, "method": 0.0, "n": 200.0, "seed": 4242.0, "a": 2.0, "b": 1.0, "sig": 0.5, "xmax": 10.0}, 4000, "cr_fit_p",
               "For data y_i = f(x_i; beta) + noise with known errors sigma_i, the best parameters minimise chi^2 = sum "
               "((y_i - f)/sigma_i)^2. For a model linear in its parameters the normal equations (A^T W A) beta = A^T W y solve "
               "it exactly, and the covariance matrix is (A^T W A)^-1: the parameter errors come out of the same calculation. "
               "A parabola is still 'linear' in its coefficients (general linear least squares). When the errors differ along the "
               "data, the weights 1/sigma^2 make precise points count for more and give a smaller scatter of the fitted "
               "parameter than the unweighted fit. The reference value is the parameter the data were made with, so the "
               "error shown is statistical and falls as N^-1/2.",
               _steps("Read the model, the true parameters and the noise from the method card.",
                      "Compare the weighted and the unweighted fit on the unequal-error data."),
               [_q("Weighting each point by 1/sigma^2 is right because", ["it is the maximum-likelihood fit for Gaussian errors", "it makes the line steeper", "it removes outliers"],
                   "The log-likelihood of Gaussian data is -chi^2/2 with chi^2 weighted by 1/sigma^2."),
                _q("A good fit has a reduced chi-square of about", ["1", "0", "10"], "Each point is about one sigma from the fit, so chi^2 is about the degrees of freedom.")],
               [DU25, NR, SIM], "LEAST SQUARES", digits=5, tol=0.01)


def maximum_likelihood() -> dict:
    return _cr("cr-maximum-likelihood", "Maximum likelihood and Pearson chi-square", "Data analysis",
               "Estimate a Poisson mean, a Gaussian width and an exponential lifetime by maximising the likelihood "
               "numerically, and test the fit with Pearson's chi-square.", "cr_mle",
               {"cas": 0.0, "method": 0.0, "n": 1000.0, "seed": 777.0, "lam": 4.0}, 200000, "cr_mle_p",
               "The likelihood L(theta) is the probability of the whole data set as a function of the unknown parameter; the "
               "estimate is the theta that maximises ln L. Here the maximum is found by a golden-section search, which "
               "does not need a formula (for these three laws the answer happens to be the sample mean, but the code does not "
               "use that). The estimate is consistent: its error falls as N^-1/2, at the Cramer-Rao bound. Goodness of fit is "
               "judged by Pearson's chi^2 = sum (O - E)^2/E over a histogram, which for a correct model is close to its number "
               "of degrees of freedom. The reference value is the parameter the data were generated from.",
               _steps("Read the distribution and its true parameter from the method card.",
                      "Check that chi-square per degree of freedom stays near 1 at every N."),
               [_q("The maximum-likelihood estimate of a Poisson mean is", ["the sample mean", "the sample median", "the largest count"],
                   "Setting d(ln L)/d(lambda) = sum k_i/lambda - N = 0 gives lambda = mean of k."),
                _q("For a Gaussian the maximum-likelihood variance divides by N, not N - 1, so it is", ["slightly biased low", "exactly unbiased", "biased high"],
                   "It is biased by a factor (N-1)/N, which matters only for small N.")],
               [DU25, NB, SIM], "MAXIMUM LIKELIHOOD", digits=5)


def random_deviates() -> dict:
    return _cr("cr-random-deviates", "Random numbers from arbitrary distributions", "Monte Carlo",
               "Generate exponential, Gaussian and binomial deviates by the inverse transform and by acceptance-rejection, "
               "and compare the histogram with the target.", "cr_dev",
               {"cas": 0.0, "method": 0.0, "n": 20000.0, "seed": 31415.0, "lam": 1.0, "xb": 1.0}, 100000, "cr_dev_f",
               "A computer gives uniform numbers u in (0, 1). If F is the cumulative distribution of the target, x = F^-1(u) has "
               "exactly that distribution (the inverse transform); for the exponential this is -ln(u)/lambda, for the Gaussian "
               "a tabulated inverse of the error function. When F cannot be inverted, acceptance-rejection throws a point "
               "uniformly in a box around f and keeps x if the point lies under the curve. The price is the rejected throws: "
               "the efficiency is the area under f over the area of the box. Either way the fraction of samples in an interval "
               "converges to the exact probability as N^-1/2.",
               _steps("Read the target distribution and the interval from the method card.", "Compare the two methods at the same N, and their efficiency."),
               [_q("The inverse-transform method needs", ["the cumulative distribution F and its inverse", "a rejection box", "a normal generator"], "x = F^-1(u) with u uniform has distribution F."),
                _q("The efficiency of acceptance-rejection is", ["area under f / area of the box", "always 1", "the number of samples"], "Only the throws that land under the curve are kept.")],
               [DU25, NR, SIM], "RANDOM DEVIATES", digits=6)


def random_walk() -> dict:
    return _cr("cr-random-walk", "Random walk in 1, 2, 3 and n dimensions", "Monte Carlo",
               "Follow unit-step random walks on a cubic lattice and measure the mean square displacement and the "
               "probability to be back at the origin.", "cr_walk",
               {"cas": 0.0, "method": 0.0, "n": 4000.0, "seed": 2718.0, "dim": 3.0, "steps": 16.0}, 20000, "cr_walk_v",
               "At each step the walker moves one unit along one of the 2d lattice directions chosen at random. Every step is "
               "independent and has squared length 1, and the mean of the cross terms vanishes, so the mean square displacement "
               "after N steps is exactly <R^2> = N, in any dimension. The probability to be back at the origin after N steps "
               "(N even) is an exact lattice sum, C(N, N/2)/2^N in one dimension and its square in two. Simulated with W "
               "walkers, both estimates have a statistical error that falls as W^-1/2.",
               _steps("Read the dimension and the number of steps from the method card.", "Look at one walker in the corner of the screen."),
               [_q("The mean square displacement of an unbiased random walk grows", ["linearly with the number of steps", "as the square of the steps", "not at all"],
                   "The squared steps add: <R^2> = N a^2. The rms distance grows only as the square root."),
                _q("The statistical error of <R^2> from W walkers falls as", ["W^-1/2", "W^-1", "W^2"], "It is the error of a mean of W independent numbers.")],
               [DU25, GIORDANO, SIM], "RANDOM WALK", digits=5)


def mc_decay_chain() -> dict:
    return _cr("cr-mc-decay-chain", "Monte Carlo radioactive decay chain", "Monte Carlo",
               "Give every nucleus of a parent-daughter chain a random decay time and compare the populations with the "
               "Bateman equations.", "cr_decay",
               {"cas": 0.0, "method": 0.0, "n": 20000.0, "seed": 1234.0, "l1": 0.5, "l2": 1.5, "tend": 3.0}, 100000, "cr_decay_v",
               "A nucleus decays at a random time with density lambda e^(-lambda t), so t = -ln(u)/lambda for a uniform u. "
               "Drawing a decay time for the parent and, from that moment, one for its daughter simulates the chain nucleus by "
               "nucleus. The expected populations are the Bateman solutions N_A = N0 e^(-l1 t) and N_B = N0 l1/(l2 - l1) "
               "(e^(-l1 t) - e^(-l2 t)). When the parent lives longer than the daughter, N_B/N_A settles at l1/(l2 - l1): "
               "equilibrium. The simulated count of N nuclei fluctuates by about the square root of the number counted.",
               _steps("Read the decay constants and the time of counting from the method card.", "Choose the case: one nuclide, the chain, or the ratio."),
               [_q("The decay time of a single nucleus is generated as", ["-ln(u)/lambda", "u/lambda", "lambda u"], "It is the inverse transform of the exponential law."),
                _q("In transient equilibrium the daughter activity compared with the parent's is", ["larger by l2/(l2 - l1)", "equal", "smaller"], "A_B/A_A = l2/(l2 - l1) > 1 when the daughter decays faster.")],
               [DU25, SIM], "DECAY CHAIN", digits=6)


def mc_two_level_spin() -> dict:
    return _cr("cr-mc-two-level-spin", "Monte Carlo two-level spin system", "Statistical mechanics",
               "Simulate independent two-level spins in a field by Metropolis updates and compare the magnetisation and the "
               "specific heat with the Boltzmann results.", "cr_twolevel",
               {"cas": 0.0, "method": 0.0, "n": 4000.0, "seed": 9001.0, "x": 1.0, "ns": 40.0}, 4000, "cr_two_v",
               "A spin with energy -mu B s (s = +1 or -1) in equilibrium at temperature T has mean orientation <s> = tanh x with "
               "x = mu B/kT, and each spin contributes c/k = x^2 sech^2 x to the specific heat (the Schottky anomaly). "
               "The Metropolis algorithm reaches this equilibrium: propose to flip a spin, accept always if the energy falls "
               "and with probability e^(-dE/kT) if it rises. The specific heat is found here from the fluctuation of the energy, "
               "c = (<e^2> - <e>^2)/(kT)^2, not by differentiating.",
               _steps("Read x = mu B/kT and the number of spins from the method card.", "Compare the magnetisation and the specific-heat versions."),
               [_q("Metropolis accepts an energy-raising flip with probability", ["e^(-dE/kT)", "0", "1/2"], "That ratio of Boltzmann factors makes the chain's stationary distribution the Boltzmann one."),
                _q("A two-level system has a maximum in its specific heat because", ["at low T the upper level is empty, at high T both are equally full", "the field vanishes", "the spins interact"],
                   "The energy changes fastest in the temperature range where the populations are changing.")],
               [DU25, NB, SIM], "TWO-LEVEL SPINS", digits=6)


def mc_ising() -> dict:
    return _cr("cr-mc-ising", "Ising model by Monte Carlo", "Statistical mechanics",
               "Simulate the Ising model on a 1-D chain and a 2-D lattice by the Metropolis algorithm and compare the "
               "magnetisation and energy with the exact results.", "cr_ising",
               {"cas": 0.0, "method": 0.0, "n": 1000.0, "seed": 60221.0, "dim": 2.0, "L": 16.0, "T": 1.8, "what": 0.0}, 1000, "cr_ising_v",
               "The Ising energy is E = -J sum s_i s_j over neighbouring spins s = +-1. In one dimension the model has no order "
               "at any T > 0, and the transfer matrix gives its energy per spin exactly. In two dimensions Onsager found an exact "
               "solution with a transition at kTc/J = 2/ln(1 + sqrt 2) = 2.2692 and a spontaneous magnetisation "
               "(1 - sinh^-4(2J/kT))^(1/8) below it. The Metropolis algorithm flips a random spin with probability "
               "min(1, e^(-dE/kT)); the Wolff algorithm flips a whole correlated cluster, which avoids critical slowing down. "
               "A finite periodic lattice differs slightly from the infinite one, which is why a small lattice is used well "
               "away from Tc.",
               _steps("Read the lattice, the temperature and the quantity from the method card.", "Look at the lattice in the corner and at the running estimate."),
               [_q("Below Tc the 2-D Ising model has a nonzero", ["spontaneous magnetisation", "energy gap", "critical exponent only above Tc"], "Onsager's exact solution shows long-range order up to Tc."),
                _q("Metropolis updates slow down near Tc because", ["correlated regions grow large", "the temperature is low", "the lattice is small"], "Single-spin flips move a domain wall by only one site.")],
               [DU25, NB, ONSAGER, SIM], "ISING MODEL", digits=5)


def mc_integration() -> dict:
    return _cr("cr-mc-integration", "Monte Carlo integration and the central limit theorem", "Monte Carlo",
               "Estimate an integral by hit-or-miss, by the sample mean and by importance sampling, and measure how the "
               "error falls with N.", "cr_mcint", {"cas": 0.0, "method": 1.0, "n": 20000.0, "seed": 24680.0}, 100000, "cr_mcint_I",
               "The integral of f over [a, b] is (b - a) times the mean of f, so the average of f at N random points estimates it, "
               "with a standard error sigma_f (b - a)/sqrt(N) given by the central limit theorem. Hit-or-miss throws points "
               "in a box and counts those under the curve - simple, but noisier. Importance sampling draws the points from a "
               "density p that resembles f and averages f/p, which varies less and so has a smaller sigma. The exponent -1/2 "
               "is the same for every method and every dimension; only the constant changes.",
               _steps("Read the integrand and the interval from the method card.", "Compare the three methods at the same N and see their standard errors."),
               [_q("Importance sampling lowers the error by making", ["f/p vary less", "N larger", "the integral smaller"], "The standard error is the spread of the quantity that is averaged, divided by sqrt(N)."),
                _q("The error of any Monte Carlo integral falls with N as", ["N^-1/2", "N^-1", "N^-2"], "It is the central limit theorem for a mean of N independent samples.")],
               [DU25, NR, SIM], "MC INTEGRATION", digits=6)


def mc_scattering() -> dict:
    return _cr("cr-mc-scattering", "Toy Monte Carlo of scattering", "Monte Carlo",
               "Scatter projectiles with random impact parameters from a hard sphere and from a Coulomb field and compare "
               "the cross-section and the angular distribution with the exact results.", "cr_scatter",
               {"cas": 0.0, "method": 0.0, "n": 50000.0, "seed": 8128.0, "a": 1.0, "R": 1.5, "what": 0.0}, 100000, "cr_scatter_s",
               "A beam of uniform intensity is a set of projectiles with impact parameters b spread uniformly over a disc, so "
               "b^2 is uniform. Each b gives a scattering angle by classical mechanics. For a hard sphere of radius a, a "
               "projectile with b < a is reflected through theta with cos(theta) = 2b^2/a^2 - 1, so cos(theta) is uniform: the "
               "scattering is isotropic, dsigma/dOmega = a^2/4 and the total cross-section is pi a^2. For a Coulomb field "
               "tan(theta/2) = d/(2b), which gives Rutherford's cross-section pi (d/2)^2 cot^2(theta0/2) for scattering beyond "
               "theta0. The cross-section estimated from N projectiles has the error of a counted fraction.",
               _steps("Read the target and the beam radius from the method card.", "Look at the histogram of cos(theta) against the exact count in each bin."),
               [_q("A hard sphere scatters isotropically because", ["cos(theta) is uniform when b^2 is uniform", "it is smooth", "the force is central"], "cos(theta) is linear in b^2."),
                _q("The Rutherford cross-section is large at small angles because", ["distant projectiles are deflected a little", "the nucleus is large", "the force is weak"], "Large impact parameters cover a larger area of the beam.")],
               [DU25, GIORDANO, SIM], "SCATTERING", digits=5)


def polynomial_roots() -> dict:
    return _cr("cr-polynomial-roots", "Numerical solution of a polynomial", "Numerical methods",
               "Find a real root of a polynomial by bisection, Newton-Raphson and the secant method (and, for a double root, "
               "by the modified Newton method).", "cr_poly",
               {"cas": 0.0, "method": 0.0, "n": 8.0, "xa": 2.5, "xb": 3.5, "x0": 3.4, "x1": 3.3, "gx0": 0.5, "gx1": 3.6}, 20, "cr_poly_x",
               "Bisection halves a bracket around a sign change, so it gains one bit of accuracy per step and never fails. "
               "Newton-Raphson, x - p/p', uses the slope and, near a simple root, squares the error at every step. The secant "
               "method replaces the slope by a chord and converges with order 1.62. Polynomials are evaluated by Horner's "
               "rule, with p and p' in one pass. At a double root p' also vanishes and plain Newton slows to a factor of 2 per "
               "step; multiplying the step by the multiplicity restores quadratic convergence. The reference roots are known "
               "from the factorisation, or for x^3 - 2x - 5 from Cardano's formula.",
               _steps("Read the polynomial, the bracket and the starting values from the method card.", "Compare the speed of the three methods."),
               [_q("Bisection gains accuracy by a factor", ["2 per step", "10 per step", "squared per step"], "Each step halves the bracket."),
                _q("Plain Newton-Raphson at a double root converges", ["only linearly", "in one step", "never"], "p' vanishes at the root, so the usual quadratic argument fails.")],
               [DU25, SASTRY, SIM], "POLYNOMIAL ROOTS", digits=10)


def mc_photon_slab() -> dict:
    return _cr("cr-mc-photon-slab", "Monte Carlo multiple scattering of photons in a slab", "Radiation physics",
               "Follow photons through a scattering and absorbing slab, and compare the unscattered transmission and the "
               "first-collision statistics with the exact results; see where the dose is deposited.", "cr_photon",
               {"cas": 0.0, "method": 0.0, "n": 20000.0, "seed": 5551.0, "d": 2.0, "mus": 0.6, "mua": 0.15}, 50000, "cr_photon_v",
               "A photon travels a free path s = -ln(u)/mu_t, with mu_t = mu_s + mu_a, before it interacts. There it is absorbed "
               "with probability mu_a/mu_t and otherwise scattered into a new direction. The fraction that crosses a slab of "
               "thickness d without any interaction is exactly e^(-mu_t d) (Beer-Lambert), and the first collisions fall "
               "off as mu_t e^(-mu_t z); these are the exact results the code is checked against. Multiple scattering has "
               "no closed form, but the code must still conserve photons: transmitted + reflected + absorbed = 1. The "
               "coefficients here describe an illustrative turbid medium; they are NOT tabulated tissue data.",
               _steps("Read the thickness and the coefficients from the method card.", "Look at where photons first interact and where they are finally absorbed."),
               [_q("The fraction of photons that cross a slab without interacting is", ["e^(-mu_t d)", "1 - mu_t d", "mu_t d"], "The free path is exponentially distributed."),
                _q("Why must the three fractions add up to 1?", ["every photon is reflected, transmitted or absorbed exactly once", "the medium is lossless", "the slab is thin"], "A sum different from 1 would mean photons were lost or counted twice.")],
               [DU25, GIORDANO,
                {"title": "Optical coefficients of the slab: model values, unsourced / illustrative (not NIST XCOM or tissue data)"}, SIM],
               "PHOTON TRANSPORT", digits=5)


# ============================================================================================ Ph.D. / research
def ising_binder() -> dict:
    return _cr("cr-ising-binder", "2-D Ising model: critical temperature from the Binder cumulant", "Statistical mechanics",
               "Find the critical temperature of the 2-D Ising model from the crossing of the Binder cumulants of two lattice "
               "sizes, by Metropolis and by Wolff cluster updates.", "cr_binder",
               {"cas": 0.0, "method": 1.0, "n": 300.0, "seed": 1066.0, "L1": 8.0, "L2": 16.0, "Tlo": 2.1, "Thi": 2.45, "nT": 6.0}, 400,
               "cr_binder_T",
               "The Binder cumulant U4 = 1 - <m^4>/(3<m^2>^2) tends to 2/3 in the ordered phase and to 0 in the disordered phase. "
               "Near Tc finite-size scaling says U4 depends only on L/xi, and since xi is infinite at Tc the curves for all "
               "sizes cross there. The crossing of two sizes is therefore an estimate of Tc, and Onsager's exact value "
               "2/ln(1 + sqrt 2) = 2.2692 J/kB is the reference. Because the cumulant is a ratio of fluctuations the crossing "
               "carries a statistical error of about a per cent from a few hundred sweeps, and small lattices add a small shift "
               "from corrections to scaling, so this check allows 2 %. The Wolff algorithm flips a whole cluster and removes "
               "the critical slowing down that makes Metropolis poor near Tc.",
               _steps("Read the two lattice sizes and the temperature range from the method card.", "Compare Metropolis with Wolff at the same number of sweeps."),
               [_q("The Binder cumulants of different sizes cross at Tc because", ["there U4 does not depend on L", "both equal 2/3", "the energy is minimal"], "At Tc the correlation length is infinite, so U4 depends on no length scale."),
                _q("The Wolff update is better than Metropolis near Tc because", ["it flips correlated clusters", "it uses a lower temperature", "it needs fewer spins"], "It decorrelates the lattice in a few updates.")],
               [DU25, NB, ONSAGER, SIM], "BINDER CUMULANT", level="Ph.D.", digits=5, tol=0.02)


def xy_heisenberg() -> dict:
    return _cr("cr-xy-heisenberg-mc", "Monte Carlo of the XY and Heisenberg models", "Statistical mechanics",
               "Simulate classical XY and Heisenberg spins by Metropolis and compare the energy and the helicity modulus at low "
               "temperature with spin-wave theory.", "cr_spin",
               {"cas": 0.0, "method": 0.0, "n": 800.0, "seed": 4711.0, "L": 8.0, "T": 0.1, "what": 0.0}, 800, "cr_spin_v",
               "Continuous spins s_i (unit vectors) with H = -J sum s_i . s_j have no long-range order at T > 0 in two dimensions "
               "(Mermin-Wagner), but at low T they are described by small spin waves, and for these the theory is exact "
               "because H is quadratic in the small angles. Each mode carries kT/2, so the energy per spin is e = e0 + "
               "(degrees of freedom per spin) T/2 (minus the global rotations), and the helicity modulus of the 2-D XY model "
               "is Y = 1 - T/4. The numerical values T_BKT = 0.89 J/kB and Tc(Heisenberg, 3-D) = 1.44 J/kB are not exact "
               "results and are not checked here; the corrections to the spin-wave line grow as T^2.",
               _steps("Read the model, the lattice and the temperature from the method card.", "Run at T = 0.1 and T = 0.2 and compare with the spin-wave line."),
               [_q("Each harmonic spin-wave mode carries an energy", ["kT/2", "kT", "0"], "Equipartition for a quadratic Hamiltonian."),
                _q("The helicity modulus measures", ["the stiffness against a twist of the boundary conditions", "the magnetisation", "the heat capacity"], "It is the second derivative of the free energy with respect to a twist.")],
               [DU25, NB,
                {"title": "Spin-wave limits (harmonic approximation) of the 2-D XY helicity modulus and energy",
                 "note": "derived in the harmonic approximation and cited from the standard literature, not re-fetched; the BKT and Heisenberg critical temperatures are not used"}, SIM],
               "XY / HEISENBERG", level="Ph.D.", digits=5)


def tight_binding() -> dict:
    return _cr("cr-tight-binding", "Tight-binding band structures", "Solid state",
               "Diagonalise the tight-binding Hamiltonian of a chain, a square lattice and graphene numerically and compare "
               "the band width, the ground-state energy and the density of states with the exact band.", "cr_tb",
               {"cas": 0.0, "method": 0.0, "n": 22.0, "t": 1.0, "what": 1.0}, 34, "cr_tb_E",
               "With one orbital per site and hopping -t between neighbours, a periodic chain has the bands E = -2t cos(ka): "
               "width 4t, and a density of states 1/(pi sqrt(4t^2 - E^2)) with van Hove singularities at the edges. The square "
               "lattice has E = -2t (cos kx + cos ky), width 8t. Graphene, with two atoms per cell, has E = +-t |1 + e^(ik.a1) "
               "+ e^(ik.a2)| and Dirac points where the bands touch. The code builds the Hamiltonian matrix and diagonalises "
               "it by Jacobi rotations (for graphene, the 2 x 2 Bloch Hamiltonian at each k). Filling the lowest N/2 orbitals "
               "twice gives a ground-state energy per site that approaches -4t/pi for the chain as N^-2.",
               _steps("Read the lattice and the hopping from the method card.", "Compare the computed band (dots) with the exact one (line) in the corner."),
               [_q("The density of states of a 1-D band is largest at the band edges because", ["E(k) is flat there", "more atoms sit there", "hopping is stronger"], "g(E) is proportional to 1/|dE/dk|."),
                _q("Graphene has a Dirac point because", ["the two sublattice terms cancel at K", "it is a metal with one band", "the hopping vanishes"], "At K the sum 1 + e^(ik.a1) + e^(ik.a2) is zero.")],
               [DU25,
                {"title": "Model hopping t = 1 (energy unit); no material value is used",
                 "note": "t is the unit of energy; for graphene t is of order a few eV but that number is not used or sourced here"},
                {"title": "N. W. Ashcroft and N. D. Mermin, Solid State Physics, ch. 10 (tight-binding method)", "note": "cited, not re-fetched"}, SIM],
               "TIGHT BINDING", level="Ph.D.", digits=6, tol=0.01)


def exact_diagonalisation() -> dict:
    return _cr("cr-exact-diagonalisation", "Exact diagonalisation of a quantum spin chain", "Quantum many-body",
               "Find the ground-state energy of a spin-1/2 ring by Lanczos diagonalisation and compare it with the exact "
               "free-fermion and Bethe-ansatz results.", "cr_ed", {"cas": 0.0, "method": 0.0, "n": 8.0, "h": 1.0}, 8, "cr_ed_E",
               "The Hilbert space of N spins-1/2 has 2^N states, but a Hamiltonian that connects each state to only a few others "
               "is never stored as a matrix: the Lanczos recursion builds a small tridiagonal matrix from repeated "
               "applications of H to one vector, and its lowest eigenvalue converges quickly to the ground-state energy. The "
               "transverse-field Ising ring maps to free fermions, so its energy for any N is exactly -sum sqrt(1 + h^2 - 2h cos k) "
               "over k = (2m+1)pi/N. The Heisenberg ring is solved by the Bethe ansatz: E0/N tends to 1/4 - ln 2 for N -> infinity, "
               "with a correction proportional to 1/N^2, so two small sizes already extrapolate to about 0.05 %.",
               _steps("Read the Hamiltonian and the size from the method card.", "Compare the transverse-field and Heisenberg chains."),
               [_q("Lanczos diagonalisation needs only", ["the product of H with a vector", "the full matrix in memory", "the eigenvectors"], "It builds a Krylov space from repeated applications of H."),
                _q("Why can two small chains give the energy at N -> infinity?", ["the leading finite-size correction is a known power of 1/N", "the energy does not depend on N", "N = 12 is infinite"], "With a known 1/N^2 law, two sizes remove the leading error.")],
               [DU25, {"title": "A. W. Sandvik, Computational Studies of Quantum Spin Systems, AIP Conf. Proc. 1297, 135 (2010)", "note": "Lanczos and the Heisenberg chain; cited, not re-fetched"},
                {"title": "P. Pfeuty, Ann. Phys. 57, 79 (1970)", "note": "exact solution of the transverse-field Ising chain; cited, not re-fetched"}, SIM],
               "EXACT DIAGONALISATION", level="Ph.D.", digits=8)


def fdtd_em() -> dict:
    return _cr("cr-fdtd-em", "Finite-difference time-domain electromagnetics", "Computational electromagnetics",
               "Send a pulse through a dielectric slab and a Bragg mirror by the 1-D FDTD method and compare the transmission "
               "spectrum with the exact characteristic-matrix result.", "cr_fdtd",
               {"cas": 0.0, "method": 0.0, "n": 40.0, "n1": 2.0, "n2": 1.5, "np": 3.0, "wr": 0.8}, 80, "cr_fdtd_T",
               "Yee's scheme stores E and H on interleaved grids and updates them in turn from the curl equations: H += (E_(i+1) - "
               "E_i), E += (H_i - H_(i-1))/eps. With a time step equal to the cell size divided by c a wave moves exactly one "
               "cell per step in vacuum, with no numerical dispersion; in glass the dispersion is small and falls as the second "
               "power of the cell size. A pulse is sent through the structure and through vacuum, and the ratio of the Fourier "
               "transforms of the signals behind them is the transmittance at every frequency. The exact answer multiplies "
               "2 x 2 characteristic matrices layer by layer. Only the slab and Bragg stack are built here (not a metal "
               "nanoparticle, which needs two or three dimensions).",
               _steps("Read the structure and the probe frequency from the method card.", "Increase the cells per wavelength and watch the error fall by four."),
               [_q("The 1-D Yee scheme with c dt = dz has no numerical dispersion in vacuum because", ["a wave moves exactly one cell per step", "the scheme is implicit", "there are no boundaries"], "Both finite differences are then exact for a travelling wave."),
                _q("A Bragg mirror reflects strongly near the design frequency because", ["the reflections from all interfaces add in phase", "the layers absorb", "the index is large"], "A quarter-wave path difference doubles to a half-wave, giving constructive reflection.")],
               [DU25, {"title": "A. Taflove and S. C. Hagness, Computational Electrodynamics: The Finite-Difference Time-Domain Method, 3rd ed. (Artech House, 2005)", "note": "cited, not re-fetched"},
                {"title": "Layer indices 2.0 and 1.5 are model values, unsourced / illustrative"}, SIM],
               "FDTD", level="Ph.D.", digits=6)


def pic_plasma() -> dict:
    return _cr("cr-pic-plasma", "Particle-in-cell simulation of a plasma", "Plasma physics",
               "Simulate a cold plasma oscillation and the two-stream instability with a 1-D particle-in-cell code and compare "
               "the frequency and the growth rate with theory.", "cr_pic",
               {"cas": 0.0, "method": 0.0, "n": 24.0, "np": 800.0}, 32, "cr_pic_v",
               "A particle-in-cell code moves charged macro-particles through a field that lives on a grid: the particles are "
               "weighted onto the grid (cloud-in-cell), Gauss's law dE/dx = rho gives the field, the field is interpolated back "
               "to the particles and they are advanced by leapfrog. In units where the plasma frequency is 1, a cold plasma "
               "displaced by a sine wave oscillates at exactly omega = omega_p. Two cold beams of speed +-v0 obey "
               "(w^2 - k^2 v0^2)^2 = wp^2 (w^2 + k^2 v0^2), and for k v0 < wp the smaller root is imaginary: the fields grow as e^(gamma t) with "
               "a maximum gamma = wp/(2 sqrt 2). The code measures the frequency from the zero crossings and the growth rate from "
               "the slope of ln|E| and compares them with these cold-fluid results. Units are normalised (wp = 1): no "
               "physical constant is needed.",
               _steps("Read the case, the particle number and the time step from the method card.", "Look at the phase space in the corner of the screen."),
               [_q("A displaced cold electron layer oscillates at", ["the plasma frequency", "the cyclotron frequency", "zero frequency"], "The charge separation field acts as a restoring force; omega_p^2 = n e^2/(eps0 m)."),
                _q("The two-stream instability grows because", ["a density ripple bunches the beams and strengthens the ripple", "the beams collide", "the field is static"], "The field of the bunches accelerates the particles to make more bunching.")],
               [DU25, {"title": "C. K. Birdsall and A. B. Langdon, Plasma Physics via Computer Simulation (McGraw-Hill, 1985)", "note": "cited, not re-fetched"}, SIM],
               "PARTICLE IN CELL", level="Ph.D.", digits=5)


def n_body() -> dict:
    return _cr("cr-n-body", "N-body gravitational simulation", "Computational mechanics",
               "Integrate a Kepler orbit and a small star cluster with Euler-Cromer, Verlet and Runge-Kutta methods; "
               "compare the orbital period with Kepler's third law and the cluster's virial ratio with the virial theorem.",
               "cr_nbody", {"cas": 0.0, "method": 1.0, "n": 200.0, "ecc": 0.5, "seed": 1999.0, "tend": 20.0, "ns": 16.0}, 400, "cr_nbody_v",
               "For two bodies the orbit is an ellipse, and Kepler's third law gives its period T = 2 pi sqrt(a^3/GM). The code "
               "starts the planet at pericentre and measures the time of the next pericentre passage. Euler-Cromer is first "
               "order, velocity Verlet second order and symplectic, Runge-Kutta 4 fourth order; the plot shows how their energy "
               "errors differ over several orbits. For many bodies the virial theorem 2<K> + <W> = 0 holds for the "
               "time average of any bounded system; a cluster started in virial equilibrium should keep a ratio 2K/|W| "
               "near 1 on average. The cluster is chaotic, so only this average, not the individual orbits, is reliable.",
               _steps("Read the eccentricity and the method from the method card.", "Compare the three integrators on the energy plot."),
               [_q("A symplectic integrator such as Verlet is used for long orbit runs because", ["its energy error stays bounded", "it is fourth order", "it needs no force"], "It conserves a nearby Hamiltonian, so the energy oscillates instead of drifting."),
                _q("For a bound system in the long run, 2K/|W| averages", ["1", "0", "2"], "That is the virial theorem for a 1/r potential.")],
               [DU25, GIORDANO, {"title": "Units: GM = 1 and semi-major axis 1; no physical constant is used"}, SIM],
               "N-BODY", level="Ph.D.", digits=6)


def mcmc_fitting() -> dict:
    return _cr("cr-mcmc-fitting", "Bayesian parameter estimation by MCMC", "Data analysis",
               "Fit a spectral line, a decay curve and a transit light curve by Metropolis Markov-chain Monte Carlo and "
               "compare the posterior with the exactly integrated one.", "cr_mcmc",
               {"cas": 0.0, "method": 0.0, "n": 8000.0, "seed": 3003.0, "what": 0.0, "sig": 0.3}, 20000, "cr_mcmc_v",
               "Bayes' theorem gives the probability of the parameters given the data, p(theta|y) proportional to exp(-chi^2/2) "
               "times the prior. A Metropolis chain proposes a random step and accepts it with probability min(1, p'/p); the "
               "visited points are samples of the posterior, from which the mean and the credible interval follow. The "
               "reference is not a formula for a nonlinear model but the same posterior integrated directly on a fine grid "
               "(exact to the quadrature), and for the model that is linear in its parameter (the transit depth) the posterior "
               "is exactly Gaussian. The chain's error falls as 1/sqrt of the number of independent samples, which is smaller "
               "than the chain length because neighbouring points are correlated.",
               _steps("Read the model, the noise and the parameters from the method card.", "Compare the histogram of the chain with the exact posterior."),
               [_q("A Metropolis chain accepts a step with probability", ["min(1, p'/p)", "1/2", "p'"], "That rule gives the posterior as its stationary distribution."),
                _q("The chain's samples are", ["correlated, so fewer than N are independent", "independent", "exact"], "Each point is near the previous one.")],
               [DU25, NB, {"title": "Noise level and model amplitudes are chosen for the exercise (model values, unsourced / illustrative)"}, SIM],
               "MCMC", level="Ph.D.", digits=5, tol=0.01)


def schrodinger_numerical() -> dict:
    return _cr("cr-schrodinger-numerical", "Numerical Schrodinger equation (shooting and split-step)", "Quantum mechanics",
               "Find energy levels of the harmonic oscillator, the infinite well and the hydrogen atom by the shooting method, "
               "and the oscillator's ground state by the split-step Fourier method.", "cr_schro",
               {"cas": 0.0, "method": 0.0, "n": 32.0, "lev": 0.0, "ell": 0.0}, 64, "cr_schro_E",
               "The stationary Schrodinger equation is a boundary-value problem: only special energies give a solution that "
               "vanishes at both ends. The shooting method integrates from one end with the Numerov formula, counts the nodes "
               "of the solution and bisects on E until the node count jumps: the n-th level has n nodes. In atomic units "
               "the oscillator has E = n + 1/2, a well of width 1 has E = n^2 pi^2/2 and hydrogen has E = -1/(2 n^2) hartree. The "
               "split-step method instead evolves a trial state in imaginary time, alternately multiplying by e^(-V dt) in "
               "space and e^(-T dt) in momentum space by FFT; every excited state decays faster than the ground state, which "
               "remains. Units are atomic or oscillator units, so no physical constant is needed.",
               _steps("Read the potential and the level from the method card.", "Compare shooting with split-step on the oscillator."),
               [_q("In the shooting method the number of nodes of the trial solution tells you", ["which side of an eigenvalue E is on", "the width of the well", "the mass"], "It jumps by one each time E passes an eigenvalue."),
                _q("Imaginary-time evolution finds the ground state because", ["higher states decay faster as e^(-E t)", "the energy is imaginary", "it is unitary"], "After a long time the lowest-energy component dominates.")],
               [DU25, GIORDANO, NR, {"title": "Units: oscillator units (hbar = m = omega = 1) and atomic units (hartree); no physical constant is used"}, SIM],
               "SCHRODINGER", level="Ph.D.", digits=7, tol=0.005)


BUILDERS = (interpolation, finite_difference_pde, finite_element_intro, least_squares_fit, maximum_likelihood,
            random_deviates, random_walk, mc_decay_chain, mc_two_level_spin, mc_ising, mc_integration, mc_scattering,
            polynomial_roots, mc_photon_slab, ising_binder, xy_heisenberg, tight_binding, exact_diagonalisation,
            fdtd_em, pic_plasma, n_body, mcmc_fitting, schrodinger_numerical)
