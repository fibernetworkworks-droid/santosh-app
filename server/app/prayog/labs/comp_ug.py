"""Prayogshala lab pack: the B.Sc. "Computational physics" practicals (DU UGCF-2022 / LOCF-2019 lists).

One rig serves them all - `app/static/prayog/exp/comp-workstation.js`, a real lab WORKSTATION: desk mat, monitor,
keyboard, mouse, tower and a printed method card. The student reads the card, switches the machine on, chooses the
method and the step size / sample count, presses Enter, and the MONITOR DRAWS the computation: the exact curve, what
the method built, and the nodes it used. Each run is a reading in the record book - the numerical answer, the exact
analytic answer and the error - and the result of the practical is the error at the finest setting together with the
way the error falls as the step gets smaller.

Physics: the `comp_ug` kernel pack (never catalog.py / kernels.py). Every lab carries its own check: the kernel's
answer against the closed-form value, within 1 %. English only.
"""
from __future__ import annotations

from ..catalog import B, col, inst, lab

SIM = {"title": "Hoola Prayogshala kernel", "note": "the numbers come from the simulation code; checked against the "
                                                    "closed-form value in Hoola's tests"}
DU22 = {"title": "Undergraduate Programme in Physics under UGCF-2022 (NEP), B.Sc. (Hons.) Physics, University of Delhi"}
DULOCF = {"title": "B.Sc. (Honours) Physics LOCF syllabus 2019-20, Department of Physics and Astrophysics, University of Delhi"}
SASTRY = {"title": "S. S. Sastry, Introductory Methods of Numerical Analysis, PHI",
          "note": "the standard forms of the bisection, Newton-Raphson, secant, trapezoidal, Simpson, Euler and "
                  "Runge-Kutta formulas and their orders of accuracy"}
NR = {"title": "W. H. Press, S. A. Teukolsky, W. T. Vetterling, B. P. Flannery, Numerical Recipes",
      "note": "Gauss-Legendre nodes and weights by Newton's method on the Legendre recurrence (gauleg)"}
CRC = {"title": "CRC Handbook of Chemistry and Physics, densities of solids and liquids"}
NUBASE = {"title": "NUBASE2020 evaluation of nuclear physics properties (Chinese Physics C 45, 030001) - half-lives",
          "note": "the decay constants used here are lam = ln2 / T(1/2) from the evaluated half-life of each nuclide"}

GROUP = "Physics · Computational"
LEVEL = "B.Sc. (Hons.) Physics"
CHAP = "Computational physics"


def _station(caption: str) -> list[dict]:
    """The workstation as LSL data. The realistic bench is the studio rig; this keeps the lab openable on its own."""
    return [
        B("mat", "box", name="Desk mat", size=[0.9, 0.004, 0.45], pos=[0.05, 0.002, -0.12], color="black", cut=False),
        B("foot", "box", name="Monitor stand", size=[0.22, 0.012, 0.14], pos=[0.08, 0.008, -0.42], color="#2b2f36"),
        B("neck", "cylinder", r=0.016, h=0.1, pos=[0.08, 0.06, -0.42], color="#2b2f36"),
        B("bezel", "box", name="Monitor", info="The plot and the printed numbers of every run appear here.",
          size=[0.36, 0.235, 0.016], pos=[0.08, 0.225, -0.4], color="#17181b"),
        B("screen", "plane", name="Screen", info="Left: the exact curve and what the method built. Right: the run log.",
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


def _cp(lab_id: str, title: str, topic: str, aim: str, kernel: str, params: dict, check_n: float, textbook: str,
        theory: str, steps: list[str], questions: list[dict], sources: list[dict], caption: str,
        unit: str = "", digits: int = 4, extra_check: dict | None = None) -> dict:
    chk = {"params": {"n": check_n}, "reading": "val", "textbook": textbook}
    if extra_check:
        chk["params"].update(extra_check)
    return lab(
        id=lab_id, rig="comp-workstation", title=title, group=GROUP, level=LEVEL, topic=topic, chapter=CHAP,
        aim=aim, kernel=kernel, params=params, speed=1, speeds=[1],
        camera={"pos": [0.45, 0.42, 0.78], "look": [0.08, 0.17, -0.3]}, floor=-0.02,
        bodies=_station(caption),
        instruments=[inst("val", "readout", "Numerical answer", "val", unit=unit, digits=digits),
                     inst("exa", "readout", "Exact answer", "exact", unit=unit, digits=digits),
                     inst("err", "readout", "Relative error", "err", digits=6)],
        table={"columns": [col("n", "n (step / sample setting)", "manual", digits=0),
                           col("val", "Numerical answer", "manual", unit=unit, digits=digits),
                           col("err", "Relative error", "manual", digits=6)],
               "calc": "cp_best", "rows_min": 4, "result_digits": digits,
               "hint": "Run the method at several settings of n; the answer at the largest n is your result."},
        steps=steps, theory=theory,
        safety="A computational practical still has a discipline: write down the method, the setting of n and the "
               "error of every run before changing anything, and never report a number whose error you have not seen.",
        questions=questions, sources=sources, check=chk,
    )


# ============================================================================================= root finding
ROOT_THEORY = ("A root of f(x) = 0 is found by repeating a step that shrinks the interval or improves the guess. "
               "Bisection halves a bracket in which f changes sign, so the error is halved every iteration and the "
               "method can never fail once the bracket is right. Newton-Raphson follows the tangent, "
               "x_(k+1) = x_k - f(x_k)/f'(x_k): it roughly squares the accuracy each step but needs f' and a good "
               "start. The secant method replaces the tangent by the chord through the last two points, so it needs "
               "no derivative. The practical is the comparison: the same root, the same accuracy, a different number "
               "of iterations.")
ROOT_STEPS = ["Read the method card: the equation, the bracket and the starting guess.",
              "Switch the workstation on.",
              "Choose the method and the number of iterations, then press Enter.",
              "Write down the root and its error. Repeat with more iterations.",
              "Compare the error after the same number of iterations for each method."]
ROOT_Q = [{"q": "Bisection halves the bracket each time. After 10 iterations an interval of 1.0 is known to about",
           "options": ["0.001", "0.1", "0.00001"], "answer": 0,
           "why": "1/2^10 = 1/1024, so about one part in a thousand."},
          {"q": "Newton-Raphson can fail where", "options": ["f'(x) is near zero", "f(x) is negative", "the bracket is wide"],
           "answer": 0, "why": "The tangent is nearly horizontal, so the next guess is thrown far away."}]


def root_finding() -> dict:
    return _cp("cp-root-finding", "Roots of equations: bisection, Newton-Raphson and secant",
               "Numerical methods", "Find a root of f(x) = 0 by bisection, by Newton-Raphson and by the secant "
               "method, and see how fast the error falls with each.",
               "cp_root", {"cas": 0.0, "method": 0.0, "n": 12.0, "a": 2.0, "m": 2.0, "xa": 0.5, "xb": 3.0,
                           "x0": 1.0, "x1": 2.0},
               60, "cp_root_x", ROOT_THEORY, ROOT_STEPS, ROOT_Q, [DU22, SASTRY, SIM], "ROOTS OF f(x) = 0", digits=6)


def sphere_depth() -> dict:
    return _cp("cp-sphere-depth", "Depth to which a floating sphere sinks",
               "Numerical methods", "A sphere of known radius and relative density floats in water: solve the cubic "
               "for the depth to which it sinks, and check it against the closed-form root.",
               "cp_root", {"cas": 1.0, "method": 0.0, "n": 14.0, "R": 0.05, "s": 0.917, "xa": 0.0, "xb": 0.1,
                           "x0": 0.02, "x1": 0.09},
               60, "cp_root_x",
               "A floating body displaces its own weight of water, so the submerged spherical cap of depth d must "
               "have the same volume as the sphere times its relative density s: pi d^2 (3R - d)/3 = s (4/3) pi R^3, "
               "that is d^3 - 3R d^2 + 4 s R^3 = 0. On 0 < d < 2R the left side falls steadily from +4sR^3 to "
               "(4s-4)R^3, so there is exactly one physical root and bisection on [0, 2R] always finds it. The cubic "
               "also has a closed form, d = R(1 + 2 cos(arccos(1-2s)/3 + 4pi/3)), which is what your answer is "
               "checked against.",
               ["Read the sphere's radius and relative density from the method card.",
                "Switch the workstation on.",
                "Choose a method and a number of iterations, then press Enter.",
                "Write down the depth and its error; repeat with more iterations.",
                "Check that the depth is less than the radius for a body lighter than water."],
               [{"q": "A sphere of relative density 0.5 sinks to a depth of", "options": ["exactly its radius",
                 "half its radius", "its whole diameter"], "answer": 0,
                 "why": "Half the volume must be under water, and a hemisphere is half the sphere."},
                {"q": "Why is bisection safe on [0, 2R] here?", "options": ["f changes sign once and only once there",
                 "f is a cubic", "the root is in the middle"], "answer": 0,
                 "why": "f is strictly decreasing on that interval, so there is a single sign change."}],
               [DU22, SASTRY, CRC, SIM], "FLOATING SPHERE: DEPTH d", unit="m", digits=5)


def alpha_tan() -> dict:
    return _cp("cp-alpha-tan", "Solutions of alpha = tan(alpha)",
               "Numerical methods", "Find the first root of the transcendental equation alpha = tan(alpha) beyond "
               "pi, the equation that fixes the dark fringes of single-slit diffraction.",
               "cp_root", {"cas": 2.0, "method": 0.0, "n": 16.0, "xa": 3.3, "xb": 4.6, "x0": 4.3, "x1": 4.6},
               60, "cp_root_x",
               "alpha = tan(alpha) cannot be solved in closed form; it has one root in each interval (n pi, n pi + "
               "pi/2). The first non-zero root, near 4.4934, is the one that fixes the position of the first "
               "secondary maximum in single-slit diffraction. tan(alpha) - alpha changes sign between 3.3 and 4.6, "
               "so bisection is safe there; Newton-Raphson needs a start close to the root, because the tangent "
               "near the pole at 3pi/2 throws the guess far away. Your answer is checked against the same equation "
               "solved to machine precision by 200 bisections.",
               ["Read the interval and the starting guess from the method card.",
                "Switch the workstation on.",
                "Run bisection with a few iterations, then with more.",
                "Run Newton-Raphson from the given start and compare the iteration counts.",
                "Write the root to five decimal places."],
               [{"q": "How many roots does alpha = tan(alpha) have?", "options": ["Infinitely many, one in each period of the tangent",
                 "Exactly two", "Only alpha = 0"], "answer": 0,
                 "why": "The line alpha cuts every branch of the tangent once."},
                {"q": "Where does this equation appear in optics?", "options": ["The secondary maxima of single-slit diffraction",
                 "Newton's rings", "The grating equation"], "answer": 0,
                 "why": "Differentiating the single-slit intensity (sin a / a)^2 gives a = tan a."}],
               [DU22, SASTRY, SIM], "alpha = tan(alpha)", digits=6)


def nth_root() -> dict:
    return _cp("cp-nth-root", "The n-th root of a number to a given accuracy",
               "Numerical methods", "Compute a cube root as the root of x^m - a = 0 and find how many iterations "
               "each method needs for a given number of correct digits.",
               "cp_root", {"cas": 0.0, "method": 1.0, "n": 8.0, "a": 7.0, "m": 3.0, "xa": 1.0, "xb": 3.0,
                           "x0": 2.0, "x1": 3.0},
               60, "cp_root_x",
               "The m-th root of a is the positive root of x^m - a = 0. Newton-Raphson on this function gives the "
               "classical iteration x_(k+1) = ((m-1) x_k + a / x_k^(m-1)) / m, which doubles the number of correct "
               "digits at every step; bisection on a bracket adds about one binary digit, that is about one third of "
               "a decimal digit, per iteration. Running both to the same accuracy and counting the iterations is the "
               "whole practical. The answer is checked against a^(1/m).",
               ["Read the number a and the root order m from the method card.",
                "Switch the workstation on.",
                "Run Newton-Raphson for 2, 3, 4 ... iterations and watch the digits settle.",
                "Run bisection to the same accuracy and count the iterations it needs.",
                "Report the root to the accuracy the card asks for."],
               [{"q": "Newton-Raphson for a square root doubles the correct digits each step. From 2 correct digits, "
                      "two more steps give about", "options": ["8", "4", "3"], "answer": 0,
                 "why": "2 -> 4 -> 8: the accuracy squares each time."},
                {"q": "One bisection adds about how many decimal digits?", "options": ["0.3", "1", "2"], "answer": 0,
                 "why": "It halves the error, and log10(2) = 0.30."}],
               [DU22, SASTRY, SIM], "x^m = a", digits=6)


# ============================================================================================= quadrature
QUAD_THEORY = ("A definite integral is a sum of strips. The trapezoidal rule joins neighbouring points by straight "
               "lines and has an error that falls as h^2; Simpson's 1/3 rule fits a parabola through every three "
               "points and Simpson's 3/8 rule a cubic through every four, both with an error that falls as h^4; "
               "Gauss-Legendre quadrature does not use equally spaced points at all, but n cleverly chosen nodes "
               "and weights that make the rule exact for every polynomial up to degree 2n-1. The practical is to "
               "integrate a function whose exact integral is known and watch each rule's error fall with n.")
QUAD_STEPS = ["Read the integrand and the limits from the method card.",
              "Switch the workstation on.",
              "Choose a rule and the number of strips n, then press Enter.",
              "Write down the value and the error; double n and run again.",
              "Compare the rules at the same n, and the error of each as n grows."]
QUAD_Q = [{"q": "Doubling the number of strips divides the trapezoidal error by about",
           "options": ["4", "2", "16"], "answer": 0, "why": "The error goes as h^2, and h is halved."},
          {"q": "Simpson's 1/3 rule needs", "options": ["an even number of strips", "an odd number of strips",
           "any number of strips"], "answer": 0, "why": "The strips are taken in pairs, one parabola per pair."}]


def integration() -> dict:
    return _cp("cp-integration", "Numerical integration: trapezoid, Simpson and Gauss",
               "Numerical methods", "Find ln(2) from its integral definition and compare the trapezoidal, Simpson "
               "and Gauss-Legendre rules at the same number of points.",
               "cp_quad", {"cas": 0.0, "method": 0.0, "n": 8.0, "xa": 1.0, "xb": 2.0},
               600, "cp_quad_I", QUAD_THEORY, QUAD_STEPS, QUAD_Q, [DU22, SASTRY, NR, SIM],
               "INTEGRAL of 1/x from 1 to 2", digits=8)


def integration_convergence() -> dict:
    return _cp("cp-integration-convergence", "Convergence rates of the quadrature rules",
               "Numerical methods", "Measure the ORDER of each quadrature rule: fit the slope of log(error) "
               "against log(n) and compare it with the 2 and 4 the formulas promise.",
               "cp_quad", {"cas": 1.0, "method": 0.0, "n": 6.0, "xa": 0.0, "xb": 2.0, "A": 4.0, "w": 1.5},
               600, "cp_quad_I",
               "Every quadrature rule has an order p: its error falls as h^p, that is as n^-p. Taking logs, "
               "log(error) = constant - p log(n), so a straight line through the points (log n, log error) has a "
               "slope of exactly -p. The trapezoidal rule should give p = 2 and both Simpson rules p = 4; "
               "Gauss-Legendre has no fixed p at all, because its error falls faster than any power of n for a "
               "smooth integrand. Measuring p is the honest test that a program really implements the rule it "
               "claims to, and it is the practical.",
               ["Read the integrand and the limits from the method card.",
                "Switch the workstation on.",
                "Run the trapezoidal rule at n = 4, 8, 16, 32 and 64 strips.",
                "Write down the error of each run.",
                "Read the slope of log(error) against log(n): it is minus the order of the rule."],
               [{"q": "A slope of -4 on the log-log error plot means", "options": ["the rule is fourth order",
                 "the rule is wrong", "the integral is four"], "answer": 0,
                 "why": "error ~ n^-4, which is what Simpson's rule promises."},
                {"q": "Why does Gauss-Legendre not give a straight line here?", "options": [
                 "Its error falls faster than any power of n for a smooth function", "It has no error",
                 "It uses equal spacing"], "answer": 0,
                 "why": "It is exact for polynomials up to degree 2n-1, so the error collapses much faster."}],
               [DU22, SASTRY, NR, SIM], "ORDER OF A QUADRATURE RULE", digits=8)


def position_from_acceleration() -> dict:
    return _cp("cp-position-from-acceleration", "Velocity from acceleration data by integration",
               "Mechanics by computation", "An accelerometer records a(t) = A sin(wt). Integrate the record "
               "numerically to get the velocity at a given time and compare it with the exact integral.",
               "cp_quad", {"cas": 1.0, "method": 1.0, "n": 10.0, "xa": 0.0, "xb": 3.0, "A": 2.5, "w": 2.0},
               600, "cp_quad_I",
               "Velocity is the integral of acceleration: v(T) - v(0) = integral of a(t) dt from 0 to T. For a "
               "recorded a(t) the integral has to be done numerically, strip by strip, exactly as for any other "
               "function - this is how a phone or an inertial sensor turns acceleration into speed and then into "
               "distance. For the test record a(t) = A sin(wt) the exact answer is A(1 - cos wT)/w, so the error of "
               "the numerical integration can be measured. Note how the error grows if the sampling is too coarse "
               "compared with the period of the motion: that is aliasing of the record, not a fault of the rule.",
               ["Read the recorded acceleration and the time T from the method card.",
                "Switch the workstation on.",
                "Integrate the record with Simpson's rule at n = 6, 12, 24 and 48 samples.",
                "Write down the velocity and the error each time.",
                "Compare with the exact value A(1 - cos wT)/w."],
               [{"q": "Integrating acceleration once gives", "options": ["velocity", "position", "jerk"], "answer": 0,
                 "why": "a = dv/dt, so the integral of a is the change in v."},
                {"q": "Too few samples per period of the motion gives", "options": [
                 "a large error, because the strips miss the shape", "no error", "a negative velocity"], "answer": 0,
                 "why": "The rule can only follow the curve it can see."}],
               [DU22, SASTRY, SIM], "VELOCITY FROM a(t)", unit="m/s", digits=6)


def delta_sequences() -> dict:
    return _cp("cp-delta-sequences", "The Dirac delta function as the limit of a sequence",
               "Mathematical physics", "Integrate a Lorentzian of width eps over a fixed interval and watch the "
               "integral tend to 1 as the width shrinks: the delta function as a limit, measured.",
               "cp_quad", {"cas": 3.0, "method": 1.0, "n": 60.0, "xa": -5.0, "xb": 5.0, "eps": 0.25},
               1200, "cp_quad_I",
               "The Dirac delta is not a function but the limit of a sequence of ever narrower, ever taller "
               "functions of unit area. One such sequence is the Lorentzian, f(x) = eps / (pi (x^2 + eps^2)), whose "
               "integral over the whole line is exactly 1 for every eps. Over the finite interval [-L, L] the "
               "integral is (2/pi) arctan(L/eps), which tends to 1 as eps gets small - and this is what the "
               "numerical integration has to reproduce. The practical shows the price of the limit too: the narrower "
               "the peak, the more strips the quadrature needs to see it at all.",
               ["Read the sequence and the interval from the method card.",
                "Switch the workstation on.",
                "Integrate the Lorentzian with Simpson's rule at n = 100, 200, 400 and 800 strips.",
                "Watch the integral settle on (2/pi) arctan(L/eps).",
                "Note how many strips are needed before the answer is steady."],
               [{"q": "The area under every member of a delta sequence is", "options": ["1", "eps", "infinite"],
                 "answer": 0, "why": "That is the defining property: unit area at every width."},
                {"q": "A narrower peak needs more strips because", "options": [
                 "the strips must be small compared with the width of the peak", "the area changes",
                 "Simpson's rule fails"], "answer": 0,
                 "why": "A rule can only follow a feature it samples several times."}],
               [DU22, SASTRY, SIM], "DELTA SEQUENCE: AREA", digits=6)


# ============================================================================================= first-order IVP
ODE_THEORY = ("For dy/dt = f(t, y) with y(0) known, every method takes the slope at points it can reach and steps "
              "forward by h. Euler uses the slope at the start of the step, so its global error falls only as h. "
              "RK2 (Heun) averages the slope at the start with the slope at a trial end point, giving h^2. RK4 "
              "combines four slope evaluations per step and gives h^4 - four times the work for an enormously "
              "smaller error. The practical runs them on a problem whose exact solution is known, so the error "
              "itself is a measured quantity.")
ODE_STEPS = ["Read the equation, the initial value and the end time from the method card.",
             "Switch the workstation on.",
             "Choose the method and the number of steps n, then press Enter.",
             "Write down the final value and the error; double n and run again.",
             "Compare Euler, RK2 and RK4 at the same n."]
ODE_Q = [{"q": "Halving the step size divides the RK4 error by about", "options": ["16", "2", "4"], "answer": 0,
          "why": "The error goes as h^4, and 2^4 = 16."},
         {"q": "Euler's method with too large a step can", "options": ["go unstable and grow without bound",
          "give the exact answer", "stop early"], "answer": 0,
          "why": "For decay, |1 - lam h| > 1 makes the computed solution grow instead of decaying."}]


def first_order_ivp() -> dict:
    return _cp("cp-first-order-ivp", "First-order initial value problems: Euler, RK2 and RK4",
               "Numerical methods", "Solve the decay of technetium-99m (half-life 6.0067 h, so lam = 0.11540 per hour) "
               "numerically by Euler, RK2 and RK4, and measure each method's error against the exact exponential.",
               "cp_ode1", {"cas": 0.0, "method": 0.0, "n": 20.0, "y0": 100.0, "lam": 0.11539630, "tmax": 24.0},
               2000, "cp_ode1_y", ODE_THEORY, ODE_STEPS, ODE_Q, [DU22, SASTRY, NUBASE, SIM],
               "dN/dt = -lam N", digits=6)


def ivp_error_comparison() -> dict:
    return _cp("cp-ivp-error", "Errors of the numerical ODE methods against a known solution",
               "Numerical methods", "Measure the ORDER of Euler, RK2 and RK4 from the slope of log(error) against "
               "log(n), and compare it with the 1, 2 and 4 the formulas promise.",
               "cp_ode1", {"cas": 2.0, "method": 0.0, "n": 10.0, "y0": 90.0, "Ts": 30.0, "kk": 0.02, "tmax": 120.0},
               2000, "cp_ode1_y",
               "A method of order p has a global error proportional to h^p, so on a plot of log(error) against "
               "log(n) the points lie on a line of slope -p. Measuring that slope is the only honest way to tell "
               "whether a program really implements RK4 and not, say, RK2 with four evaluations: a wrong "
               "coefficient leaves the answer plausible but drops the order. Here the test problem is Newton's law "
               "of cooling, whose exact solution Ts + (T0 - Ts) e^(-kt) is known, so the error of every run is a "
               "real measured number and the slope can be read off the table.",
               ["Read the test problem and its exact solution from the method card.",
                "Switch the workstation on.",
                "Run Euler at n = 10, 20, 40, 80 and 160 steps and record every error.",
                "Read the slope of log(error) against log(n): it should be close to -1.",
                "Repeat with RK2 and RK4 and look for -2 and -4."],
               [{"q": "A measured slope of -2 on the log-log error plot means the method is",
                 "options": ["second order", "second degree", "unstable"], "answer": 0,
                 "why": "error ~ n^-2 is the definition of second order."},
                {"q": "Why does the slope stop at about -4 even for a very fine step?", "options": [
                 "Round-off in the arithmetic takes over from truncation", "RK4 is only fourth order on paper",
                 "The clock runs out"], "answer": 0,
                 "why": "Below about 1e-14 relative error the floating-point noise is bigger than the method error."}],
               [DU22, SASTRY, SIM], "ORDER OF AN ODE METHOD", digits=6)


def population_models() -> dict:
    return _cp("cp-population-models", "Population models: exponential and logistic growth",
               "Applied dynamics", "Integrate the logistic equation numerically and compare it with its exact "
               "solution: growth that is exponential at first and saturates at the carrying capacity.",
               "cp_ode1", {"cas": 3.0, "method": 2.0, "n": 20.0, "y0": 10.0, "rr": 0.5, "Kk": 1000.0, "tmax": 20.0},
               2000, "cp_ode1_y",
               "Unchecked growth obeys dN/dt = rN and grows without bound. The logistic model adds the crowding "
               "term, dN/dt = rN(1 - N/K), so the rate falls to zero as the population approaches the carrying "
               "capacity K. It is one of the few non-linear equations with a closed-form solution, "
               "N(t) = K N0 e^(rt) / (K + N0(e^(rt) - 1)), which makes it an ideal test problem: the numerical "
               "solution can be checked at every step. The same equation describes an autocatalytic reaction and "
               "the spread of an infection.",
               ["Read the growth rate and the carrying capacity from the method card.",
                "Switch the workstation on.",
                "Integrate with RK4 at n = 10, 20, 40 and 80 steps.",
                "Write down the final population and the error each time.",
                "Compare the curve with the exact logistic solution on the screen."],
               [{"q": "In the logistic model the growth rate is largest when N is",
                 "options": ["half the carrying capacity", "near zero", "equal to K"], "answer": 0,
                 "why": "rN(1 - N/K) is a downward parabola in N, with its peak at N = K/2."},
                {"q": "As t grows, the logistic solution tends to", "options": ["K", "0", "infinity"], "answer": 0,
                 "why": "The crowding term switches the growth off at the carrying capacity."}],
               [DULOCF, SASTRY, SIM], "dN/dt = r N (1 - N/K)", digits=5)


def rate_equations() -> dict:
    return _cp("cp-rate-equations", "Rate equation of an autocatalytic reaction",
               "Applied dynamics", "Integrate the rate equation of the autocatalytic reaction A + X -> 2X and "
               "compare the numerical concentration with its exact solution.",
               "cp_ode1", {"cas": 3.0, "method": 1.0, "n": 20.0, "y0": 0.02, "rr": 1.2, "Kk": 1.0, "tmax": 10.0},
               2000, "cp_ode1_y",
               "In the autocatalytic step A + X -> 2X the product is also the catalyst, so the rate is proportional "
               "both to how much X there already is and to how much A is left: dx/dt = k x (a0 - x). With the "
               "substitution K = a0 this is the logistic equation, whose closed-form solution gives the "
               "S-shaped curve typical of autocatalysis - a long quiet induction period, a sudden rise, then "
               "saturation when A runs out. Comparing the numerical integration with that exact solution shows how "
               "coarse a step may be before the sharp rise is placed at the wrong time.",
               ["Read the rate constant and the initial concentrations from the method card.",
                "Switch the workstation on.",
                "Integrate with RK2 at n = 10, 20, 40 and 80 steps.",
                "Write down the final concentration and the error each time.",
                "Find how coarse a step moves the sudden rise visibly off the exact curve."],
               [{"q": "Autocatalysis is slow at first because", "options": ["there is very little of the catalyst X",
                 "A is used up", "the temperature is low"], "answer": 0,
                 "why": "The rate is proportional to x, which starts almost at zero."},
                {"q": "The reaction stops when", "options": ["A is exhausted", "X is exhausted", "the rate constant falls"],
                 "answer": 0, "why": "The factor (a0 - x) goes to zero."}],
               [DULOCF, SASTRY, SIM], "AUTOCATALYSIS: dx/dt = k x (a0 - x)", digits=6)


# ============================================================================================= differentiation
DIFF_THEORY = ("A derivative from a table of values is a difference divided by a step. The forward and backward "
               "differences, (f(x+h) - f(x))/h and (f(x) - f(x-h))/h, are first order in h; the central difference, "
               "(f(x+h) - f(x-h))/2h, is second order because the first error terms cancel; the five-point formula "
               "is fourth order. But a difference of two nearly equal numbers loses significant figures, so below "
               "some h the round-off error grows faster than the truncation error falls, and the total error has a "
               "minimum. Finding that best step size is the point of the practical.")
DIFF_STEPS = ["Read the function and the point x from the method card.",
              "Switch the workstation on.",
              "Choose a difference formula and the step setting n (h = h0/n), then press Enter.",
              "Write down the derivative and the error; make the step smaller and run again.",
              "Find the step at which the total error stops falling."]
DIFF_Q = [{"q": "The central difference is more accurate than the forward difference because",
           "options": ["the first error terms cancel by symmetry", "it uses a smaller step", "it divides by 2h"],
           "answer": 0, "why": "The odd Taylor terms cancel, leaving an error in h^2."},
          {"q": "A very small step makes the answer worse because", "options": [
           "round-off in f(x+h) - f(x-h) swamps the difference", "the derivative changes", "h^2 is too small"],
           "answer": 0, "why": "Subtracting two nearly equal numbers throws away significant figures."}]


def differentiation() -> dict:
    return _cp("cp-differentiation", "Numerical differentiation and round-off against step size",
               "Numerical methods", "Differentiate a known function by forward, backward, central and five-point "
               "differences, and find the step size at which round-off takes over from truncation.",
               "cp_diff", {"cas": 0.0, "method": 2.0, "n": 10.0, "x": 1.0, "h0": 0.4, "A": 1.0, "w": 2.0},
               200, "cp_diff_d", DIFF_THEORY, DIFF_STEPS, DIFF_Q, [DU22, SASTRY, SIM],
               "DERIVATIVE FROM DIFFERENCES", digits=6)


def velocity_from_position() -> dict:
    return _cp("cp-velocity-from-position", "Velocity and acceleration from position data",
               "Mechanics by computation", "A body oscillates as x(t) = A sin(wt). Get its velocity at an instant "
               "from the tabulated positions and compare it with A w cos(wt).",
               "cp_diff", {"cas": 0.0, "method": 2.0, "n": 8.0, "x": 0.35, "h0": 0.4, "A": 0.05, "w": 6.2832},
               200, "cp_diff_d",
               "A motion record is a table of positions at equal time intervals, and the velocity has to be taken "
               "from it by differences. The central difference (x(t+h) - x(t-h))/2h is the natural choice: it is "
               "second order and it uses the two readings on either side of the instant, exactly as a ticker-tape "
               "or a video frame analysis does. For the test motion x = A sin(wt) the exact velocity is A w cos(wt), "
               "so the error of the tabulated estimate can be measured - and it is largest where the velocity "
               "changes fastest, that is near the ends of the swing.",
               ["Read the motion and the instant t from the method card.",
                "Switch the workstation on.",
                "Take the velocity by central differences at n = 4, 8, 16 and 32 (h = h0/n).",
                "Write down the velocity and the error each time.",
                "Compare with the exact A w cos(wt)."],
               [{"q": "For a motion record the central difference is preferred because", "options": [
                 "it uses the readings on both sides of the instant and is second order",
                 "it needs only one reading", "it is faster"], "answer": 0,
                 "why": "The symmetric difference cancels the first error term."},
                {"q": "The error of the tabulated velocity is largest", "options": [
                 "where the acceleration is largest", "at the centre of the swing", "where the speed is zero"],
                 "answer": 0, "why": "The error term carries the third derivative, which peaks with the curvature."}],
               [DU22, SASTRY, SIM], "VELOCITY FROM A MOTION RECORD", unit="m/s", digits=6)


def difference_tables() -> dict:
    return _cp("cp-difference-tables", "Forward and backward difference tables",
               "Numerical methods", "Build the forward and backward differences of a tabulated function and take "
               "the derivative at the ends of the table, where no central difference exists.",
               "cp_diff", {"cas": 2.0, "method": 0.0, "n": 8.0, "x": 2.0, "h0": 0.8, "A": 1.0, "kk": 3.0},
               200, "cp_diff_d",
               "A table of equally spaced values has a forward difference at every row, delta f = f(x+h) - f(x), "
               "and a backward difference, nabla f = f(x) - f(x-h). Repeating them builds the difference table, "
               "whose columns give the derivatives: f'(x) = delta f / h to first order and f'(x) = nabla f / h at "
               "the other end. At the FIRST row of a table only forward differences exist, and at the LAST row "
               "only backward ones, which is exactly why both formulas are needed even though the central "
               "difference is better. For the tabulated function A x^k the exact derivative A k x^(k-1) lets the "
               "error of each be measured.",
               ["Read the tabulated function and the step from the method card.",
                "Switch the workstation on.",
                "Take the derivative by forward differences at n = 2, 4, 8 and 16.",
                "Repeat with backward differences and compare the signs of the errors.",
                "Note that the two errors are nearly equal and opposite: their average is the central difference."],
               [{"q": "At the first row of a table you can use", "options": ["only forward differences",
                 "only backward differences", "the central difference"], "answer": 0,
                 "why": "There is no row before it."},
                {"q": "The forward and backward errors are nearly equal and opposite, so their mean is",
                 "options": ["the central difference, which is more accurate", "zero", "the second derivative"],
                 "answer": 0, "why": "Averaging the two one-sided formulas gives the symmetric one."}],
               [DULOCF, SASTRY, SIM], "DIFFERENCE TABLE", digits=6)


# ============================================================================================= series / interpolation
def taylor_series() -> dict:
    return _cp("cp-taylor-series", "Taylor series approximation and truncation error",
               "Mathematical physics", "Sum the first n terms of a Maclaurin series and measure the truncation "
               "error against the function itself.",
               "cp_approx", {"cas": 0.0, "method": 0.0, "n": 4.0, "x": 1.0, "xa": 0.0, "xb": 2.0},
               30, "cp_approx_f",
               "A Taylor series replaces a function near a point by a polynomial: e^x = 1 + x + x^2/2! + ..., "
               "sin x = x - x^3/3! + ..., ln(1+x) = x - x^2/2 + ... . Stopping after n terms leaves the truncation "
               "error, which is the first term left out, so for the exponential and the sine it falls factorially "
               "fast and for ln(1+x) only as x^n/n - very slowly when x is close to 1. The practical measures that "
               "error directly: sum n terms, subtract the true value, and watch how many terms each function and "
               "each x really needs.",
               ["Read the function and the point x from the method card.",
                "Switch the workstation on.",
                "Sum 2, 4, 6, 8 and 12 terms of the series, pressing Enter each time.",
                "Write down the partial sum and the error each time.",
                "Find how many terms give five correct decimal places."],
               [{"q": "The truncation error of a Taylor sum is about", "options": ["the first term left out",
                 "the last term kept", "zero"], "answer": 0, "why": "That is the leading term of the remainder."},
                {"q": "The series for ln(1+x) converges slowly near x = 1 because", "options": [
                 "its terms fall only as 1/n", "it has no factorials in the numerator", "ln is not analytic"],
                 "answer": 0, "why": "The term is x^n/n, which at x = 1 is just 1/n."}],
               [DU22, SASTRY, SIM], "TAYLOR PARTIAL SUM", digits=8)


def lagrange_interpolation() -> dict:
    return _cp("cp-lagrange-interpolation", "The Lagrange interpolating polynomial",
               "Numerical methods", "Fit the Lagrange polynomial through n+1 tabulated points, read the function "
               "between the points, and measure the interpolation error.",
               "cp_approx", {"cas": 1.0, "method": 1.0, "n": 3.0, "x": 0.77, "xa": 0.0, "xb": 3.1416},
               18, "cp_approx_f",
               "Through any n+1 points there is exactly one polynomial of degree n, and Lagrange writes it down "
               "directly: P(x) = sum of f(x_i) times the product of (x - x_j)/(x_i - x_j) over all j not equal to i. "
               "Each of those products is 1 at its own node and 0 at every other node, so P passes exactly through "
               "every tabulated point. Between the points there is an interpolation error, which falls as nodes are "
               "added - but only up to a point: with many equally spaced nodes a high-degree polynomial begins to "
               "oscillate near the ends of the range, which is why real tables are interpolated with a few nodes "
               "around the wanted value rather than all of them.",
               ["Read the tabulated function, the range and the wanted point from the method card.",
                "Switch the workstation on.",
                "Interpolate with n = 2, 3, 5 and 8 (that is n+1 nodes), pressing Enter each time.",
                "Write down the interpolated value and the error each time.",
                "Watch the polynomial on the screen pass through every node."],
               [{"q": "Through 5 points passes exactly one polynomial of degree", "options": ["4", "5", "6"],
                 "answer": 0, "why": "n+1 points fix a polynomial of degree n."},
                {"q": "Each Lagrange basis polynomial is", "options": ["1 at its own node and 0 at the others",
                 "0 everywhere", "the same for every node"], "answer": 0,
                 "why": "That is what makes the sum pass through the data."}],
               [DU22, SASTRY, SIM], "LAGRANGE INTERPOLATION", digits=8)



# ============================================================================================= second-order IVP
ODE2_THEORY = ("m x\u2033 + c x\u2032 + k x = F cos(wt) is the same equation for a mass on a spring and for charge in "
               "an LCR circuit (m -> L, c -> R, k -> 1/C). To integrate it numerically it is written as two "
               "first-order equations, x\u2032 = v and v\u2032 = (F cos wt - c v - k x)/m, and the step methods are "
               "then exactly the ones used for a single equation. Free motion has a closed form in each damping "
               "regime - undamped, underdamped, critically damped and overdamped - fixed by gamma = c/2m against "
               "omega0 = sqrt(k/m), so the numerical solution can be checked at any time.")
ODE2_STEPS = ["Read m, c, k and the initial conditions from the method card; note which damping regime they give.",
              "Switch the workstation on.",
              "Choose the method and the number of steps, then press Enter.",
              "Write down x at the end of the run and its error; double the steps and run again.",
              "Compare the numerical curve on the screen with the exact one."]
ODE2_Q = [{"q": "Critical damping is the case", "options": ["gamma = omega0", "gamma = 0", "gamma much greater than omega0"],
           "answer": 0, "why": "At gamma = omega0 the two roots coincide and the motion returns fastest without overshooting."},
          {"q": "Euler's method applied to an undamped oscillator typically",
           "options": ["gains amplitude run after run", "loses amplitude", "is exact"], "answer": 0,
           "why": "Plain Euler does not conserve energy; the computed amplitude grows."}]


def second_order_ivp() -> dict:
    return _cp("cp-second-order-ivp", "Second-order IVP: the damped harmonic oscillator",
               "Numerical methods", "Integrate m x'' + c x' + k x = 0 as a pair of first-order equations and "
               "compare the motion with the closed form of its damping regime.",
               "cp_ode2", {"cas": 0.0, "method": 2.0, "n": 200.0, "mm": 1.0, "cc": 0.6, "kk": 4.0, "FF": 0.0,
                           "wf": 1.0, "x0": 0.1, "tmax": 10.0},
               2000, "cp_ode2_x", ODE2_THEORY, ODE2_STEPS, ODE2_Q, [DU22, SASTRY, SIM],
               "m x\u2033 + c x\u2032 + k x = 0", unit="m")


def oscillator_regimes() -> dict:
    return _cp("cp-oscillator-regimes", "Displacement of undamped, under-, critically and over-damped oscillators",
               "Oscillations by computation", "Integrate the same oscillator with four different dampings and see "
               "the four regimes the closed form predicts.",
               "cp_ode2", {"cas": 0.0, "method": 2.0, "n": 200.0, "mm": 1.0, "cc": 0.0, "kk": 4.0, "FF": 0.0,
                           "wf": 1.0, "x0": 0.1, "tmax": 10.0},
               2000, "cp_ode2_x",
               "One equation gives four quite different motions, and which one appears is decided by gamma = c/2m "
               "against omega0 = sqrt(k/m) alone. With c = 0 the motion is a pure cosine. With gamma < omega0 it "
               "oscillates inside a decaying envelope at the shifted frequency sqrt(omega0^2 - gamma^2). At "
               "gamma = omega0 the two roots of the auxiliary equation coincide and the motion returns to rest in "
               "the shortest time without crossing over - the case a galvanometer or a door closer is built for. "
               "With gamma > omega0 it creeps back as a sum of two exponentials. The practical is to produce all "
               "four from one program by changing c alone.",
               ["Read m, k and the damping of this run from the method card.",
                "Switch the workstation on.",
                "Integrate with RK4 at several step counts and record x at the end.",
                "Look at the shape on the screen: does it cross the axis, and how often?",
                "Name the regime from gamma against omega0 and check it against the shape."],
               [{"q": "Which damping returns the body to rest in the shortest time without overshoot?",
                 "options": ["critical", "under", "over"], "answer": 0,
                 "why": "That is the definition of critical damping."},
                {"q": "The frequency of a lightly damped oscillator is", "options": [
                 "a little below the undamped one", "the same", "a little above"], "answer": 0,
                 "why": "sqrt(omega0^2 - gamma^2) is less than omega0."}],
               [DU22, SASTRY, SIM], "FOUR DAMPING REGIMES", unit="m")


def forced_resonance() -> dict:
    return _cp("cp-forced-resonance", "Forced oscillator and resonance",
               "Oscillations by computation", "Drive the damped oscillator, let the transient die, and measure the "
               "steady-state amplitude against the resonance formula.",
               "cp_ode2", {"cas": 1.0, "method": 2.0, "n": 500.0, "mm": 1.0, "cc": 0.4, "kk": 4.0, "FF": 1.0,
                           "wf": 2.0, "x0": 0.0, "tmax": 120.0},
               4000, "cp_ode2_x",
               "A driven oscillator settles, after its transient has died away, into a motion at the DRIVING "
               "frequency with amplitude A = (F/m) / sqrt((omega0^2 - omega^2)^2 + (2 gamma omega)^2). The "
               "amplitude is largest near omega = omega0, and the smaller the damping the taller and narrower that "
               "resonance peak is. Numerically the whole motion is integrated from rest; the steady amplitude is "
               "read from the last part of the run, once the transient is gone, and compared with the formula. The "
               "same curve is the response of an LCR circuit, where it decides the sharpness of a tuned receiver.",
               ["Read the drive and the damping from the method card.",
                "Switch the workstation on.",
                "Integrate for the full run at several step counts; the transient must die before the amplitude is read.",
                "Write down the steady amplitude and its error each time.",
                "Compare with A = (F/m) / sqrt((omega0^2 - omega^2)^2 + (2 gamma omega)^2)."],
               [{"q": "At resonance the steady amplitude is limited by", "options": ["the damping", "the mass",
                 "the drive frequency"], "answer": 0,
                 "why": "With gamma = 0 the formula would give an unbounded amplitude."},
                {"q": "After the transient dies the oscillator moves at", "options": ["the driving frequency",
                 "its own natural frequency", "both at once"], "answer": 0,
                 "why": "The particular solution has the driving frequency; the homogeneous part has decayed."}],
               [DU22, SASTRY, SIM], "FORCED OSCILLATOR: AMPLITUDE", unit="m")


def laplace_lcr() -> dict:
    return _cp("cp-laplace-lcr", "LCR circuit: the Laplace-transform solution against the integration",
               "Circuits by computation", "Solve the LCR loop equation numerically and compare it with the closed "
               "form the Laplace transform gives for the same initial conditions.",
               "cp_ode2", {"cas": 0.0, "method": 2.0, "n": 400.0, "mm": 0.1, "cc": 20.0, "kk": 10000.0,
                           "FF": 0.0, "wf": 1.0, "x0": 0.001, "tmax": 0.06},
               4000, "cp_ode2_x",
               "For the LCR loop, L q'' + R q' + q/C = 0, the Laplace transform turns the differential equation "
               "into an algebraic one: (L s^2 + R s + 1/C) Q(s) = L s q0, so Q(s) is a ratio of polynomials whose "
               "poles are the roots of L s^2 + R s + 1/C = 0. Inverting it gives exactly the same closed form the "
               "auxiliary equation gives - a decaying oscillation when R < 2 sqrt(L/C), a creeping return when it "
               "is larger - which is why the transform is a method of solution and not a different physics. The "
               "practical checks the numerical integration of the loop equation against that inverse transform.",
               ["Read L, R and C from the method card and work out whether the circuit will ring or creep.",
                "Switch the workstation on.",
                "Integrate the loop equation with RK4 at several step counts.",
                "Write down the charge at the end of the run and its error.",
                "Compare the computed curve with the inverse-Laplace closed form on the screen."],
               [{"q": "The Laplace transform helps because it turns the differential equation into",
                 "options": ["an algebraic equation in s", "an integral equation", "a difference equation"],
                 "answer": 0, "why": "Differentiation becomes multiplication by s."},
                {"q": "The circuit stops ringing when R is bigger than", "options": ["2 sqrt(L/C)", "sqrt(LC)",
                 "1/sqrt(LC)"], "answer": 0, "why": "That is the critical-damping condition for the LCR loop."}],
               [DULOCF, SASTRY, SIM], "LCR: L q\u2033 + R q\u2032 + q/C = 0", unit="C", digits=8)


# ============================================================================================= Monte Carlo
MC_THEORY = ("A Monte Carlo method answers a question by sampling. Its error has nothing to do with a step size: "
             "it falls as 1/sqrt(N), whatever the problem and however many dimensions it has, which is why Monte "
             "Carlo loses to Simpson's rule in one dimension and wins in ten. The random numbers here come from a "
             "seeded Lehmer generator, so the whole run repeats exactly - a computational practical has to be "
             "repeatable, and a result that cannot be reproduced is not a result.")
MC_STEPS = ["Read the problem and the seed from the method card.",
            "Switch the workstation on.",
            "Run with N samples, then with four times as many, and again.",
            "Write down the estimate and the error each time.",
            "Check that the error falls roughly as 1/sqrt(N): four times the samples, half the error."]
MC_Q = [{"q": "To halve the error of a Monte Carlo estimate you need", "options": ["four times the samples",
         "twice the samples", "a better random number generator"], "answer": 0,
         "why": "The error goes as 1/sqrt(N), so N must be multiplied by four."},
        {"q": "Why is the generator seeded?", "options": ["So that the run can be repeated exactly",
         "To make it more random", "To make it faster"], "answer": 0,
         "why": "A practical must be reproducible; the seed is part of the record."}]


def monte_carlo_pi() -> dict:
    return _cp("cp-monte-carlo-pi", "Monte Carlo acceptance-rejection: the value of pi",
               "Statistical methods", "Throw random points into a square, count those inside the quarter circle, "
               "and watch the estimate of pi close in as 1/sqrt(N).",
               "cp_mc", {"cas": 0.0, "method": 0.0, "n": 4000.0, "seed": 12345.0},
               200000, "cp_mc_v", MC_THEORY, MC_STEPS, MC_Q, [DU22, SASTRY, SIM],
               "pi BY ACCEPTANCE-REJECTION", digits=6)


def random_clt() -> dict:
    return _cp("cp-random-clt", "Random numbers and the central limit theorem",
               "Statistical methods", "Average m uniform random numbers many times and measure the spread of "
               "those averages against the 1/sqrt(12m) the central limit theorem predicts.",
               "cp_mc", {"cas": 4.0, "method": 0.0, "n": 4000.0, "seed": 20251105.0, "mtoss": 10.0},
               200000, "cp_mc_v",
               "A single uniform random number on (0, 1) has mean 1/2 and standard deviation 1/sqrt(12) = 0.2887. "
               "The central limit theorem says that the MEAN of m such numbers is distributed almost normally, "
               "whatever the shape of the parent distribution, with the same mean and a standard deviation smaller "
               "by sqrt(m): sigma_mean = 1/sqrt(12 m). That is the whole reason a measurement is repeated and "
               "averaged, and it can be measured here: draw N such means and take their standard deviation. Both "
               "numbers then converge - the spread to its theoretical value, and the estimate of that spread as "
               "1/sqrt(N).",
               ["Read m, the number of uniform numbers in each mean, from the method card.",
                "Switch the workstation on.",
                "Run with N samples, then with four times as many.",
                "Write down the measured spread of the means and its error.",
                "Compare with 1/sqrt(12 m), and note that the parent distribution is not normal at all."],
               [{"q": "The mean of m uniform numbers has a standard deviation smaller than one number's by",
                 "options": ["sqrt(m)", "m", "m squared"], "answer": 0,
                 "why": "sigma_mean = sigma/sqrt(m) is the standard error of the mean."},
                {"q": "The central limit theorem requires the parent distribution to be",
                 "options": ["of finite variance, but any shape", "normal", "uniform"], "answer": 0,
                 "why": "That is what makes it so useful: the shape of the parent hardly matters."}],
               [DU22, SASTRY, SIM], "CENTRAL LIMIT THEOREM", digits=6)


def coin_toss() -> dict:
    return _cp("cp-coin-toss", "Macrostate probabilities in coin tossing",
               "Statistical mechanics by computation", "Toss m coins N times, count how often a macrostate "
               "appears, and compare with C(m,k)/2^m - the simplest statistical mechanics there is.",
               "cp_mc", {"cas": 3.0, "method": 0.0, "n": 4000.0, "seed": 777.0, "mtoss": 10.0, "khead": 5.0},
               200000, "cp_mc_v",
               "Tossing m coins, a MICROSTATE is which particular coins came up heads and a MACROSTATE is only how "
               "many did. Every microstate is equally likely, so the probability of the macrostate with k heads is "
               "the number of microstates in it divided by the total: C(m,k)/2^m. The most probable macrostate is "
               "k = m/2, and it is more sharply peaked the larger m is - which is exactly why a gas of 10^23 "
               "particles is never found far from its most probable state, and why the second law looks absolute "
               "although nothing forbids the opposite. Counting the macrostate frequency by simulation is the "
               "measurement.",
               ["Read m and the macrostate k from the method card.",
                "Switch the workstation on.",
                "Run N trials, then four times as many, and again.",
                "Write down the measured frequency of the macrostate and its error.",
                "Compare with C(m,k)/2^m, and think about how sharp the peak is for m = 10^23."],
               [{"q": "The most probable macrostate of m tossed coins is", "options": ["k = m/2", "k = 0",
                 "k = m"], "answer": 0, "why": "C(m,k) is largest in the middle."},
                {"q": "A microstate and a macrostate differ in that", "options": [
                 "a macrostate counts only how many heads, not which coins", "a microstate is more probable",
                 "a macrostate has fewer coins"], "answer": 0,
                 "why": "Many microstates belong to one macrostate; that count is the probability."}],
               [DULOCF, SASTRY, SIM], "COIN-TOSS MACROSTATES", digits=6)


def descriptive_statistics() -> dict:
    return _cp("cp-descriptive-statistics", "Sampling a distribution: mean, median and mode",
               "Statistical methods", "Draw N waiting times from an exponential population by the inverse "
               "transform and compare the sample mean with the population mean 1/lambda.",
               "cp_mc", {"cas": 5.0, "method": 0.0, "n": 4000.0, "seed": 4242.0, "rate": 0.5},
               200000, "cp_mc_v",
               "A distribution is described by its mean, its median and its mode, and for a skewed distribution "
               "these are three different numbers. The exponential distribution with rate lambda, which gives the "
               "waiting time between random events such as radioactive decays, has mean 1/lambda, median "
               "ln2/lambda = 0.693/lambda and mode 0 - so the most likely waiting time is the shortest one, while "
               "the average is far to the right of the median. Samples are drawn here by the inverse transform, "
               "x = -ln(u)/lambda for a uniform u, and the sample mean is compared with 1/lambda; the difference "
               "falls as 1/sqrt(N).",
               ["Read the rate lambda from the method card and work out the mean, the median and the mode.",
                "Switch the workstation on.",
                "Draw N samples, then four times as many, and again.",
                "Write down the sample mean and its error each time.",
                "Note that the mean is larger than the median: the distribution is skewed."],
               [{"q": "For an exponential distribution the mean is", "options": ["larger than the median",
                 "equal to the median", "smaller than the median"], "answer": 0,
                 "why": "1/lambda is larger than 0.693/lambda: the long tail pulls the mean up."},
                {"q": "The inverse transform x = -ln(u)/lambda works because", "options": [
                 "u is uniform, so the transformed variable follows the wanted distribution",
                 "the logarithm is random", "lambda is small"], "answer": 0,
                 "why": "Setting the cumulative distribution equal to a uniform number and inverting it is the standard method."}],
               [DU22, SASTRY, SIM], "SAMPLING A DISTRIBUTION", digits=6)


def error_propagation() -> dict:
    return _cp("cp-error-propagation", "Error propagation in a function of two variables",
               "Error analysis", "Test the propagation formula itself: draw correlated pairs with known "
               "uncertainties and measure the scatter of f = x y.",
               "cp_mc", {"cas": 6.0, "method": 0.0, "n": 4000.0, "seed": 31415.0, "mx": 4.0, "my": 2.5,
                         "sx": 0.08, "sy": 0.05, "rho": 0.0},
               200000, "cp_mc_v",
               "The usual rule for a function of two measured quantities, sigma_f^2 = (df/dx)^2 sigma_x^2 + "
               "(df/dy)^2 sigma_y^2 + 2 (df/dx)(df/dy) sigma_xy, is a first-order Taylor result, and the last term "
               "- the covariance - is the one most often forgotten. If x and y were measured together on the same "
               "instrument their errors are correlated, and ignoring that term can make the quoted uncertainty far "
               "too small or far too large. Here the formula is TESTED: correlated pairs are drawn with known "
               "sigma_x, sigma_y and correlation rho, and the scatter of f = x y is measured directly. For f = x y "
               "the formula reads sigma_f = sqrt(y^2 sigma_x^2 + x^2 sigma_y^2 + 2 x y rho sigma_x sigma_y).",
               ["Read x, y, their uncertainties and the correlation from the method card.",
                "Switch the workstation on.",
                "Draw N pairs, then four times as many, and again.",
                "Write down the measured spread of f and its error.",
                "Compare with the propagation formula, and repeat with the correlation set to zero."],
               [{"q": "Two quantities measured on the same instrument usually have", "options": [
                 "correlated errors, so the covariance term matters", "independent errors", "no errors"],
                 "answer": 0, "why": "A shared systematic effect correlates them."},
                {"q": "The propagation formula is", "options": ["a first-order Taylor result",
                 "exact for every function", "only for sums"], "answer": 0,
                 "why": "It keeps only the linear terms, so it needs the errors to be small."}],
               [DU22, SASTRY, SIM], "ERROR PROPAGATION", digits=6)


# ============================================================================================= projectile
def projectile() -> dict:
    return _cp("cp-projectile", "Projectile trajectory: range, greatest height and time of flight",
               "Mechanics by computation", "Integrate the equations of a projectile step by step and compare the "
               "range, the greatest height and the time of flight with the textbook formulas.",
               "cp_proj", {"cas": 0.0, "method": 2.0, "n": 100.0, "u": 30.0, "th": 0.7854, "g": 9.8},
               500, "cp_proj_v",
               "A projectile under gravity alone obeys two second-order equations, x'' = 0 and y'' = -g, which are "
               "written as four first-order ones in [x, y, vx, vy] and stepped forward together. Nothing about the "
               "method knows that the answer is a parabola: the range, the greatest height and the time of flight "
               "have to be READ OFF the computed trajectory, the landing point by interpolating the step in which y "
               "changes sign. That is why the step size matters, and why the three measured numbers can be compared "
               "with R = u^2 sin2theta/g, H = u^2 sin^2theta/2g and T = 2u sin theta/g. The same program with a "
               "drag term has no closed form at all, which is the real reason to write it.",
               ["Read the launch speed, the angle and g from the method card.",
                "Switch the workstation on.",
                "Integrate with RK4 at 10, 20, 50, 100, 200 and 500 steps.",
                "Write down the quantity this run measures and its error each time.",
                "Compare with the textbook formula; note that the coarse runs miss the landing point."],
               [{"q": "The range is largest at a launch angle of", "options": ["45 degrees", "30 degrees",
                 "60 degrees"], "answer": 0, "why": "sin 2theta is largest at theta = 45 degrees."},
                {"q": "Why must the landing step be interpolated?", "options": [
                 "The trajectory crosses the ground between two computed points", "The method is unstable",
                 "g changes"], "answer": 0,
                 "why": "No computed point lands exactly on y = 0, so the crossing is found between two of them."}],
               [DU22, SASTRY, SIM], "PROJECTILE: R, H AND T", unit="m", digits=5)



BUILDERS = (root_finding, sphere_depth, alpha_tan, nth_root,
            integration, integration_convergence, position_from_acceleration, delta_sequences,
            first_order_ivp, ivp_error_comparison, population_models, rate_equations,
            differentiation, velocity_from_position, difference_tables,
            taylor_series, lagrange_interpolation,
            second_order_ivp, oscillator_regimes, forced_resonance, laplace_lcr,
            monte_carlo_pi, random_clt, coin_toss, descriptive_statistics, error_propagation,
            projectile)
