"""Prayogshala lab pack: B.Sc. "Computational physics" practicals, wave 8 (University of Delhi UGCF-2022 Mathematical
Physics I and SEC 7 Scilab lists; LOCF-2019 Quantum Mechanics, Statistical Mechanics, Applied Dynamics, Digital Signal
Processing and Advanced Mathematical Physics I labs).

One rig serves them all - `app/static/prayog/exp/comp4-workstation.js`, a real workstation (desk mat, monitor, keyboard
with a live Enter key, mouse, tower and a printed method card) with a phase plot, a particle box, a fractal, a pole-zero
diagram or a drawn object in the corner of the screen. The student reads the card, switches the machine on, chooses the
method and the size (steps, samples, grid, length, level) and presses Enter; each run is a reading in the record book
with its answer, the reference and the error.

Physics: the `ug_comp_w8` kernel pack (never catalog.py / kernels.py). Every lab carries its own check: the kernel's
answer against an exact or independent reference, within 1 % - or within the tolerance stated on the lab for a
statistical result (molecular dynamics, the chaos game, a random profile). Model (dimensionless) units are named as
model units wherever they are used. English only.
"""
from __future__ import annotations

import math

from ..catalog import B, col, inst, lab

SIM = {"title": "Hoola Prayogshala kernel", "note": "the numbers come from the simulation code; checked against the "
                                                    "reference value in Hoola's tests"}
DU22 = {"title": "Undergraduate Programme in Physics under UGCF-2022 (NEP), B.Sc. (Hons.) Physics, University of Delhi "
                 "(22 July 2022)", "note": "DSC 1 Mathematical Physics I practical and SEC 7 Introduction to Scilab Programming"}
DULOCF = {"title": "B.Sc. (Honours) Physics LOCF syllabus 2019-20, Department of Physics and Astrophysics, University of Delhi",
          "note": "the practical lists of C-XI, C-XIV and the DSE Applied Dynamics, Digital Signal Processing and "
                  "Advanced Mathematical Physics I labs (fetched and read for this wave)"}
SASTRY = {"title": "S. S. Sastry, Introductory Methods of Numerical Analysis, PHI",
          "note": "finite differences, Simpson's rule, Runge-Kutta and Numerov in their standard forms; cited, not re-fetched"}
NR = {"title": "W. H. Press, S. A. Teukolsky, W. T. Vetterling, B. P. Flannery, Numerical Recipes, 3rd ed. (Cambridge University Press)",
      "note": "Jacobi rotations, bisection, relaxation and the DFT in their standard forms; cited, not re-fetched"}
SI2019 = {"title": "BIPM, The International System of Units (SI), 9th edition (2019)",
          "note": "kB = 1.380649e-23 J/K, NA = 6.02214076e23 /mol and e = 1.602176634e-19 C are exact by definition"}
PATHRIA = {"title": "R. K. Pathria and P. D. Beale, Statistical Mechanics, 3rd ed. (Elsevier, 2011)",
           "note": "Maxwell, Fermi-Dirac and Bose-Einstein distributions, Einstein and Debye models; cited, not re-fetched"}
OPPENHEIM = {"title": "A. V. Oppenheim and R. W. Schafer, Discrete-Time Signal Processing, 3rd ed. (Pearson, 2010)",
             "note": "convolution, the DFT, difference equations and window design; cited, not re-fetched"}
GOLDSTEIN = {"title": "H. Goldstein, C. Poole and J. Safko, Classical Mechanics, 3rd ed. (Pearson, 2002)",
             "note": "Lagrange multipliers, the Atwood machine and the bead on a rotating hoop; cited, not re-fetched"}
MODEL = {"title": "Model units", "note": "the numbers of this exercise are dimensionless parameters stated on the method card, "
                                        "not measured constants"}

GROUP = "Physics · Computational"
CHAP = "Computational physics"
LEVEL = "B.Sc."


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


def _cw(lab_id: str, title: str, topic: str, aim: str, kernel: str, params: dict, check_n: float, theory: str,
        steps: list[str], questions: list[dict], sources: list[dict], caption: str, unit: str = "", digits: int = 6,
        tol: float = 0.01) -> dict:
    chk = {"params": {"n": check_n}, "reading": "val", "textbook": kernel + "_v"}
    if tol != 0.01:
        chk["tol"] = tol
    return lab(
        id=lab_id, rig="comp4-workstation", title=title, group=GROUP, level=LEVEL, topic=topic, chapter=CHAP,
        aim=aim, kernel=kernel, params=params, speed=1, speeds=[1],
        camera={"pos": [0.45, 0.42, 0.78], "look": [0.08, 0.17, -0.3]}, floor=-0.02,
        bodies=_station(caption),
        instruments=[inst("val", "readout", "Computed answer", "val", unit=unit, digits=digits),
                     inst("exa", "readout", "Reference value", "exact", unit=unit, digits=digits),
                     inst("err", "readout", "Relative error", "err", digits=6)],
        table={"columns": [col("n", "n (size / steps / samples)", "manual", digits=0),
                           col("val", "Computed answer", "manual", unit=unit, digits=digits),
                           col("err", "Relative error", "manual", digits=6)],
               "calc": "cw8_best", "rows_min": 4, "result_digits": digits,
               "hint": "Run the method at several settings of n; report the run with the smallest error."},
        steps=steps, theory=theory,
        safety="A computational practical still has a discipline: write down the method, the setting of n, the seed and the "
               "error of every run before changing anything, and never report a number whose error you have not seen.",
        questions=questions, sources=sources, check=chk,
    )


def _q(q: str, options: list[str], why: str) -> dict:
    return {"q": q, "options": options, "answer": 0, "why": why}


def _steps(read: str, last: str) -> list[str]:
    return [read, "Switch the workstation on.", "Choose the method and the size n, then press Enter.",
            "Write down the answer and the error; change n and run again, at four settings or more.", last]


# ============================================================================================ Mathematical Physics I
def factorial_arrangements() -> dict:
    return _cw("cw8-factorial-arrangements", "Factorials and counting arrangements: Stirling's formula", "Numerical methods",
               "Compute ln N! and the number of arrangements C(N, K) exactly by summing logarithms, and measure how good "
               "Stirling's approximation is as N grows.", "cw8_fact", {"cas": 0.0, "method": 1.0, "n": 20.0, "frac": 0.5}, 50,
               "N! counts the arrangements of N different objects, and N! / (K! (N - K)!) counts the ways to choose which K "
               "of N places are occupied - the number of microstates of a two-state system, the heart of statistical "
               "physics. N! overflows a computer quickly (171! is beyond double precision), so physicists work with ln N!, "
               "summed exactly as ln 2 + ln 3 + ... + ln N. Stirling's formula approximates it: ln N! = N ln N - N, better "
               "with ln sqrt(2 pi N) added, better still with 1/(12 N). Each added term removes the leading error of the "
               "previous one, so its relative error falls faster with N.",
               _steps("Read the quantity (ln N! or ln C(N, K)) and the form of Stirling's formula from the method card.",
                      "Compare the three forms of Stirling's formula at the same N."),
               [_q("Why compute ln N! instead of N! itself?", ["N! overflows double precision beyond 170", "ln N! is more accurate", "N! cannot be summed"],
                   "171! is about 1.2e309, larger than the largest double; the logarithm of it is only about 711."),
                _q("Adding ln sqrt(2 pi N) to N ln N - N", ["removes the leading error, leaving about 1/(12 N)", "makes it exact", "doubles the error"],
                   "The next term of the asymptotic series is 1/(12 N), which is what remains.")],
               [DU22, SASTRY, SIM], "STIRLING: ln N!", digits=6)


def frame_transformations() -> dict:
    return _cw("cw8-frame-transformations", "Galilean, Lorentz and rotation transformations of observables", "Mathematical physics",
               "Build a finite Galilean boost, Lorentz boost and rotation of axes from n small steps of their generators, apply "
               "each to an observable (a velocity, or a coordinate) and compare with the finite transformation formula.",
               "cw8_frame", {"cas": 0.0, "method": 0.0, "n": 16.0, "u": 0.6, "v": 0.5, "x": 1.0, "y": 0.5, "th": 0.8}, 256,
               "A transformation of the frame changes what an observer measures. A Galilean boost by v sends x to x - v t, so "
               "a velocity u becomes u - v; boosts simply add. A Lorentz boost (c = 1) sends t to gamma (t - v x) and x to "
               "gamma (x - v t); the velocity becomes (u - v) / (1 - u v), which never exceeds 1, and it is the rapidity "
               "atanh(v), not v, that adds. A rotation of the axes by theta sends x to x cos theta + y sin theta. Each finite "
               "transformation can be built from many small ones: X -> X + d G X repeated n times, with G the generator and "
               "d = parameter / n. For the Galilean boost G squared is zero, so the product is exact for any n; for the "
               "Lorentz boost and the rotation the small steps only tend to the exact transformation as n grows.",
               _steps("Read the transformation, the observable and its parameter from the method card.",
                      "Check that the Lorentz-transformed velocity stays below c, and that t^2 - x^2 stays the same."),
               [_q("Under a Lorentz boost the quantity that is unchanged is", ["t^2 - x^2 (with c = 1)", "t + x", "x alone"],
                   "The interval is invariant; boosts are 'rotations' that keep t^2 - x^2 fixed."),
                _q("Why is the Galilean result exact for any number of small steps?", ["Its generator squared is zero, so the steps add exactly", "The velocities are small", "It uses c = 1"],
                   "x -> x - d t with t unchanged: n such steps give exactly x - v t.")],
               [DU22, GOLDSTEIN, MODEL, SIM], "FRAME TRANSFORMATIONS", digits=8)


def vector_field_operators() -> dict:
    return _cw("cw8-vector-field-operators", "Gradient, divergence and curl of a vector field, numerically", "Mathematical physics",
               "Compute the gradient of a scalar field, the divergence and the curl of vector fields at a point by central and "
               "forward differences, and compare them with the analytic derivatives.", "cw8_vfield",
               {"cas": 0.0, "method": 0.0, "n": 16.0, "x0": 0.7, "y0": 0.4, "z0": 0.3}, 64,
               "A plot of a vector field shows arrows; the operators of vector calculus turn them into numbers. The gradient "
               "of phi points uphill with a length equal to the steepest slope; the divergence of F measures how much the "
               "field spreads out of a point; the z component of the curl measures how much it circulates round the z axis. "
               "On a computer every partial derivative becomes a difference quotient: the forward difference (f(x + h) - f(x)) "
               "/ h has an error proportional to h, the central difference (f(x + h) - f(x - h)) / 2h one proportional to h^2. "
               "Halving h should therefore halve the forward error and quarter the central one, until round-off takes over.",
               _steps("Read the field, the operator and the point from the method card.",
                      "Compare central and forward differences at the same step h."),
               [_q("Halving h in a central difference changes its error by about", ["a factor 4", "a factor 2", "nothing"],
                   "The central difference is second order: the error goes as h^2."),
                _q("A field with zero divergence everywhere", ["has as much flux in as out of every small volume", "has no curl", "is constant"],
                   "That is the divergence theorem applied to a small box.")],
               [DU22, SASTRY, MODEL, SIM], "GRAD, DIV, CURL", digits=7)


def wave_group_dispersion() -> dict:
    return _cw("cw8-wave-group-dispersion", "Superposition of waves: wave groups and dispersion", "Waves",
               "Superpose two waves of nearby wave numbers, locate the peak of the beat envelope after a time T, and measure "
               "the group velocity it moves with, for normal dispersion (deep-water waves) and anomalous dispersion "
               "(capillary waves).", "cw8_group", {"cas": 0.0, "method": 0.0, "n": 4.0, "k0": 1.0, "w": 0.8, "T": 4.0, "g": 1.0, "s": 1.0}, 16,
               "Two waves cos(k1 x - w1 t) + cos(k2 x - w2 t) add into a fast carrier inside a slow envelope 2 cos((dk x - dw t)/2). "
               "The carrier moves with the phase velocity w/k; the envelope - the group, which carries the energy - moves with "
               "dw/dk. For two waves the envelope speed is exactly dw/dk as a difference quotient; as the two wave numbers "
               "approach each other it becomes the derivative, the group velocity. In a dispersive medium the two speeds "
               "differ: deep-water waves (w^2 = g k) have v_g = v_p / 2 (normal dispersion), capillary ripples (w^2 = (sigma/rho) k^3) "
               "have v_g = 3 v_p / 2 (anomalous dispersion). The program finds the envelope peak on a fine grid, refines it "
               "with a parabola and divides its distance by T. Model units: g = 1 and sigma/rho = 1.",
               _steps("Read the dispersion relation, k0 and the time T from the method card.",
                      "Compare the group velocity with the phase velocity printed beside it."),
               [_q("In normal dispersion the group velocity is", ["smaller than the phase velocity", "larger than the phase velocity", "zero"],
                   "dv_p/dk < 0, so v_g = v_p + k dv_p/dk is below v_p (deep-water waves: half)."),
                _q("The energy of a wave group travels with", ["the group velocity", "the phase velocity", "the speed of light"],
                   "The envelope, where the amplitude is large, carries the energy.")],
               [DU22, {"title": "F. S. Crawford, Waves, Berkeley Physics Course Vol. 3 (McGraw-Hill)", "note": "group velocity and the dispersion of water waves; cited, not re-fetched"}, MODEL, SIM],
               "WAVE GROUPS", digits=6)


def graphics_transformations() -> dict:
    return _cw("cw8-graphics-transformations", "Translation, reflection, shear and rotation of a drawn object", "Mathematical physics",
               "Draw a circle as an n-sided polygon, move every vertex by a translation, reflection, shear or rotation, and read "
               "the moved drawing back: its signed area by the shoelace formula and the position of its centroid.",
               "cw8_gfx", {"cas": 0.0, "method": 0.0, "what": 1.0, "n": 24.0, "r": 1.0, "cx0": 1.5, "cy0": 0.5,
                           "tx": 2.0, "ty": 1.0, "al": 0.5, "sh": 0.6, "th": 0.7}, 96,
               "Computer graphics moves a drawing by applying one operator to all its points. A translation adds a vector; a "
               "rotation and a reflection are orthogonal matrices; a shear x -> x + k y slides each line by an amount that grows "
               "with its height. What the operator does to the whole figure is read off its determinant: the area is multiplied "
               "by det A, so translation, rotation and shear (det = 1) keep the area and a reflection (det = -1) reverses the "
               "orientation, which flips the sign of the shoelace area. The centroid of the drawing moves exactly like any other "
               "point: c -> A c + t. A polygon of n sides has area (n/2) r^2 sin(2 pi/n), which approaches pi r^2 as n grows; "
               "the centroid of a regular polygon is its centre for every n.",
               _steps("Read the operator, its parameter and the quantity read back from the method card.",
                      "Plot the old and the new figure together and check the sign of the area."),
               [_q("A reflection changes the signed area of a figure by", ["a factor -1", "nothing", "a factor 2"],
                   "Its determinant is -1: the figure is traversed the other way round."),
                _q("A shear x -> x + k y", ["keeps the area of every figure", "doubles it", "makes it zero"],
                   "Its matrix [[1, k], [0, 1]] has determinant 1.")],
               [DU22, DULOCF, MODEL, SIM], "GRAPHICS OPERATORS", digits=8)


# ============================================================================================ Quantum mechanics
def schrodinger_anharmonic() -> dict:
    return _cw("cw8-schrodinger-anharmonic", "Radial Schrodinger equation: anharmonic oscillator", "Quantum mechanics",
               "Solve the s-wave radial equation for V(r) = k r^2 / 2 + b r^3 / 3 (m c^2 = 940 MeV, k = 100 MeV fm^-2, b = 0, 10 and "
               "30 MeV fm^-3) by Numerov shooting, and find the ground-state energy and the mean square radius of its wave function.",
               "cw8_anharm", {"cas": 0.0, "method": 0.0, "what": 0.0, "n": 200.0, "hbarc": 197.3269804, "mc2": 940.0,
                              "kk": 100.0, "bb": 10.0, "rmax": 7.0, "Elo": 0.5, "Ehi": 3.0}, 400,
               "For a particle of mass m in a central potential, the s-wave radial function u(r) = r R(r) obeys u'' = (2m/h-bar^2)"
               "(V - E) u with u(0) = 0. Only special energies give a solution that also dies away at large r. In oscillator units "
               "(lengths in a = (h-bar^2/(m k))^(1/4), energies in h-bar omega = h-bar sqrt(k/m)) the equation is u'' = 2 (r^2/2 + b' r^3/3 - E) u. "
               "The program integrates outward with the Numerov formula on n steps and bisects on E: below the eigenvalue u ends "
               "positive, above it u has crossed zero. For b = 0 the answer is exactly E = 3/2 h-bar omega = 96.54 MeV and <r^2> = 3/2 a^2. "
               "For b > 0 there is no formula, so the reference is an independent method: a Rayleigh-Ritz diagonalisation in the "
               "lowest 18 oscillator states, with its matrix elements computed on a fine grid. The two methods agree to better "
               "than 1e-8. The University of Delhi practical expects the ground state between 90 and 110 MeV in all three cases.",
               _steps("Read m c^2, k, b and h-bar c from the method card; note h-bar omega and the length unit a.",
                      "Repeat for b = 0, 10 and 30 MeV fm^-3, and look at the wave function on the screen."),
               [_q("Numerov's method has an error per unit length of order", ["h^4", "h", "h^2"],
                   "It is a fourth-order scheme for equations of the form u'' = f(r) u."),
                _q("Adding the cubic term b r^3 / 3 with b > 0", ["raises the energy and pulls the wave function inward", "lowers the energy", "changes nothing"],
                   "The extra potential is positive and grows with r, so the particle is confined more tightly.")],
               [DULOCF, NR, {"title": "CODATA 2018: h-bar c = 197.3269804 MeV fm", "note": "the syllabus itself uses 197.3 MeV fm"}, SIM],
               "s-WAVE: V = kr^2/2 + br^3/3", unit="MeV", digits=6)


# ============================================================================================ Statistical mechanics
def lennard_jones_md() -> dict:
    return _cw("cw8-lennard-jones-md", "Particles in a box with Lennard-Jones interactions", "Statistical mechanics",
               "SIMULATED in reduced (model) units: follow 36 Lennard-Jones particles in a periodic 2-D box and measure their "
               "speed distribution against Maxwell's, the approach to equilibrium, and the local number density.",
               "cw8_ljmd", {"cas": 0.0, "method": 0.0, "what": 0.0, "n": 1000.0, "side": 6.0, "rho": 0.5, "T0": 1.0,
                            "dt": 0.01, "rc": 2.5, "neq": 1000.0, "seed": 2024.0}, 4000,
               "Each pair of particles interacts by the Lennard-Jones potential 4 eps ((sigma/r)^12 - (sigma/r)^6), cut and shifted "
               "at r = 2.5 sigma, in a square box with periodic walls. The velocity Verlet scheme advances positions and velocities "
               "and conserves the energy well (the drift is shown). Started on a lattice, the system forgets its start: after "
               "an equilibration time the speeds follow the Maxwell distribution, which in two dimensions gives <|v|> / sqrt(<v^2>) "
               "= sqrt(pi)/2 = 0.886 whatever the temperature; a start with all motion along x shares its energy until "
               "<v_y^2> = <v_x^2> (equipartition); and the density in any fixed half of the box averages to N / L^2, though it "
               "fluctuates from moment to moment (the Fano factor of the count is shown). These are time averages over n steps "
               "after the first 1000, so their error is statistical and falls slowly (36 particles share their energy between x and y in large swings); the lab's tolerance is 5 %. Units are reduced "
               "Lennard-Jones units (eps = sigma = m = kB = 1): model units, not a real gas.",
               _steps("Read the number of particles, the density, the time step and the quantity from the method card.",
                      "Watch the running average settle in the plot, and note the energy drift and the temperature."),
               [_q("In two dimensions the Maxwell distribution gives <|v|> / v_rms equal to", ["sqrt(pi)/2", "1", "sqrt(8/(3 pi))"],
                   "For f(v) ~ v exp(-v^2/2 sigma^2), <|v|> = sigma sqrt(pi/2) and v_rms = sigma sqrt 2."),
                _q("Why is velocity Verlet used for molecular dynamics?", ["It is time-reversible and keeps the energy from drifting", "It is fourth order", "It needs no forces"],
                   "A symplectic integrator conserves a nearby energy, so long runs stay physical.")],
               [DULOCF, {"title": "D. Frenkel and B. Smit, Understanding Molecular Simulation, 2nd ed. (Academic Press, 2002)", "note": "Lennard-Jones reduced units, Verlet integration; cited, not re-fetched"}, MODEL, SIM],
               "LENNARD-JONES MD (reduced units)", digits=5, tol=0.05)


def partition_function_levels() -> dict:
    return _cw("cw8-partition-function-levels", "Partition function, energy, heat capacity and entropy of few-level systems",
               "Statistical mechanics",
               "Sum the partition function of two particles on three equally spaced levels under Maxwell-Boltzmann, Fermi-Dirac "
               "and Bose-Einstein counting, and find the heat capacity as dU/dT and the entropy as -dF/dT by finite differences.",
               "cw8_levels", {"cas": 0.0, "method": 0.0, "what": 0.0, "n": 8.0, "L": 3.0, "eps": 1.0, "T": 0.8}, 64,
               "The partition function Z = sum over states of e^(-E/kT) holds the whole thermodynamics: U = kT^2 d(ln Z)/dT, "
               "F = -kT ln Z, S = (U - F)/T and C = dU/dT. For two particles on L levels the counting depends on the statistics: "
               "distinguishable particles (Maxwell-Boltzmann) have L^2 states, fermions may not share a level (L(L-1)/2 states), "
               "bosons may (L(L+1)/2 states). The program differentiates U(T) and -F(T) numerically with a step h = T/n. The "
               "reference needs no derivative at all: C = (<E^2> - <E>^2)/kT^2 from the energy fluctuations, and S = (U - F)/T, "
               "so the numerical derivative is checked against an independent formula. Energies are in units of the level spacing "
               "and kB = 1 (model units).",
               _steps("Read the statistics, the number of levels and the temperature from the method card.",
                      "Repeat for the three statistics, and look for the Schottky-like peak of the heat capacity."),
               [_q("Two fermions on three levels have", ["3 states", "9 states", "6 states"],
                   "They must be on different levels: C(3, 2) = 3 ways."),
                _q("The heat capacity of a few-level system at high temperature", ["falls to zero", "grows for ever", "stays at 3R"],
                   "Once all states are equally filled, more heat cannot raise the energy further.")],
               [DULOCF, PATHRIA, MODEL, SIM], "Z, U, C, S", digits=6)


def maxwell_speeds() -> dict:
    return _cw("cw8-maxwell-speeds", "Maxwell speed distribution: average, rms and most probable speeds", "Statistical mechanics",
               "Tabulate the Maxwell speed distribution of nitrogen at 300 K and compute its mean and rms speeds by Simpson's rule "
               "and its most probable speed from the peak of the table.", "cw8_maxwell",
               {"cas": 0.0, "method": 0.0, "what": 0.0, "n": 16.0, "M": 28.0134, "T": 300.0}, 64,
               "In a gas at temperature T the fraction of molecules with speeds between v and v + dv is f(v) dv with f(v) = "
               "4 pi (m/2 pi kT)^(3/2) v^2 e^(-m v^2/2kT). Its peak is the most probable speed sqrt(2kT/m); its mean is "
               "sqrt(8kT/pi m); the square root of its mean square is the rms speed sqrt(3kT/m). The program tabulates f on n "
               "intervals of [0, 6 v_p], integrates v f and v^2 f by Simpson's rule, and finds the peak of the table refined by a "
               "parabola through the three highest points. The molecular mass is M / NA with the exact SI value of NA; kB is exact too.",
               _steps("Read the gas, its molar mass and the temperature from the method card.",
                      "Check the order v_p < <v> < v_rms, and how the curve flattens at a higher temperature."),
               [_q("For any gas the three speeds are in the order", ["v_p < <v> < v_rms", "<v> < v_p < v_rms", "all equal"],
                   "sqrt 2 < sqrt(8/pi) < sqrt 3."),
                _q("Doubling the absolute temperature multiplies the rms speed by", ["sqrt 2", "2", "4"],
                   "v_rms = sqrt(3kT/m).")],
               [DULOCF, PATHRIA, SI2019,
                {"title": "IUPAC standard atomic weights: N2 28.0134 g/mol", "note": "from memory - verify against the IUPAC table"}, SIM],
               "MAXWELL SPEEDS", unit="m/s", digits=5)


def specific_heat_models() -> dict:
    return _cw("cw8-specific-heat-models", "Specific heat of solids: Dulong-Petit, Einstein and Debye", "Statistical mechanics",
               "Compute the molar heat capacity of copper at 100 K from the Debye model by Simpson's rule, and compare it with the "
               "Einstein and Dulong-Petit values.", "cw8_heatcap", {"cas": 0.0, "method": 2.0, "n": 8.0, "T": 100.0, "thD": 343.0,
                                                                  "thE": 265.7}, 64,
               "Dulong and Petit's law says every solid has C = 3R per mole: each atom is a classical three-dimensional oscillator "
               "with kT per degree of freedom. It fails at low temperature. Einstein quantised the vibrations at one frequency, "
               "C = 3R x^2 e^x/(e^x - 1)^2 with x = thE/T, which falls too fast. Debye used the whole sound-wave spectrum up to a "
               "cut-off, C = 9R (T/thD)^3 integral from 0 to thD/T of t^4 e^t/(e^t - 1)^2 dt, which gives the observed T^3 law at "
               "low temperature. The program evaluates the Debye integral by Simpson's rule on n intervals, and the Dulong-Petit "
               "and Einstein heat capacities as the numerical derivative dU/dT of their energies with h = T/n. The references are "
               "3R, Einstein's formula and the Debye integral by its exponential series (no quadrature). R = NA kB exactly. The "
               "Einstein temperature is taken as sqrt(3/5) thD, the frequency with the same mean square as the Debye spectrum.",
               _steps("Read the model, the solid's Debye temperature and the temperature from the method card.",
                      "Compare the three models at the same temperature, and on the C(T) curve on the screen."),
               [_q("At low temperature the Debye heat capacity goes as", ["T^3", "exp(-thE/T)", "a constant"],
                   "Only long-wavelength phonons with energy below kT are excited, and their number goes as T^3."),
                _q("At high temperature all three models give", ["3R per mole", "zero", "R per mole"],
                   "Every mode then has kT of energy: the classical Dulong-Petit value.")],
               [DULOCF, PATHRIA, SI2019,
                {"title": "C. Kittel, Introduction to Solid State Physics, 8th ed., Debye temperatures (Cu 343 K)",
                 "note": "from memory - verify against Kittel's table"}, SIM],
               "SPECIFIC HEAT OF SOLIDS", unit="J/(mol K)", digits=5)


def quantum_distributions() -> dict:
    return _cw("cw8-quantum-distributions", "Maxwell-Boltzmann, Fermi-Dirac and Bose-Einstein distributions", "Statistical mechanics",
               "Plot the three occupation functions against E/kT and compute the mean energy per particle of an ideal gas at zero "
               "chemical potential, non-relativistic and ultra-relativistic, by Simpson's rule.", "cw8_qdist",
               {"cas": 0.0, "method": 0.0, "n": 16.0, "T": 300.0}, 64,
               "The mean number of particles in a state of energy E is e^(-(E - mu)/kT) for classical particles, 1/(e^((E - mu)/kT) "
               "+ 1) for fermions and 1/(e^((E - mu)/kT) - 1) for bosons. The number of states per unit energy goes as E^(1/2) for "
               "non-relativistic particles (E = p^2/2m) and as E^2 for ultra-relativistic ones (E = p c). The mean energy per "
               "particle is the ratio of two integrals, computed here by Simpson's rule after the substitution E = kT t^2, which "
               "removes the Bose singularity at E = 0. At mu = 0 the exact answer is <E>/kT = (a + 1) X(a + 2)/X(a + 1) with a = 1/2 "
               "or 2 and X = 1, the Dirichlet eta function or the Riemann zeta function: 3/2 for a classical gas, 0.770 for "
               "non-relativistic bosons, 2.701 for photons (black-body radiation). kB and e are exact SI values.",
               _steps("Read the statistics, the density of states and the temperature from the method card.",
                      "Compare the three statistics on the screen at the same E/kT."),
               [_q("At energies E - mu much larger than kT all three distributions", ["approach e^(-(E - mu)/kT)", "become 1", "become zero at once"],
                   "The 1 in the denominator then hardly matters."),
                _q("The mean energy of a photon in black-body radiation is about", ["2.70 kT", "1.5 kT", "kT"],
                   "<E> = (pi^4/15) / (2 zeta(3)) kT = 2.701 kT.")],
               [DULOCF, PATHRIA, SI2019, SIM], "MB, FD, BE", unit="eV", digits=6)


# ============================================================================================ Applied dynamics
def fractals() -> dict:
    return _cw("cw8-fractals", "Fractal dimension: deterministic, self-similar and natural fractals", "Nonlinear dynamics",
               "Measure the fractal dimension of the Sierpinski triangle built deterministically and by the chaos game, by box "
               "counting, and of a rough random-walk profile (a model of a natural coastline or landscape) by its variogram.",
               "cw8_fractal", {"cas": 0.0, "method": 0.0, "n": 6.0, "kmax": 6.0, "seed": 4242.0}, 8,
               "A fractal looks alike at every magnification, so the number of boxes of side eps needed to cover it grows as "
               "eps^(-D) with a dimension D that need not be a whole number. Box counting measures D as the slope of log N(eps) "
               "against log(1/eps). The Sierpinski triangle is made of three copies of itself at half size, so D = log 3 / log 2 "
               "= 1.585. It can be built deterministically, by subdividing n times, or as a random self-similar set by the chaos "
               "game: jump half way to a randomly chosen corner, again and again. A natural rough profile - a coastline, a mountain "
               "skyline - is often a random curve whose height differences grow with distance as t^H; its graph then has "
               "dimension D = 2 - H, and for a random walk H = 1/2, D = 3/2. The program measures H from the variogram, the rms "
               "height difference at lags 1 to 32. The chaos game and the profile are statistical (seeded).",
               _steps("Read the fractal and the box sizes or lags from the method card.",
                      "See how the measured dimension settles once the set is fine enough for the smallest box."),
               [_q("A set made of N copies of itself scaled by 1/s has similarity dimension", ["log N / log s", "N / s", "N s"],
                   "N = s^D, so D = log N / log s."),
                _q("Why does box counting at small eps fail when the set has too few points?", ["Boxes that should be filled stay empty", "The boxes overlap", "The slope becomes integer"],
                   "The set must be resolved more finely than the smallest box, or N(eps) saturates.")],
               [DULOCF, {"title": "B. B. Mandelbrot, The Fractal Geometry of Nature (Freeman, 1982)", "note": "Sierpinski gasket and the dimension of Brownian profiles; cited, not re-fetched"}, MODEL, SIM],
               "FRACTAL DIMENSION", digits=5, tol=0.02)


def flow_visualisation() -> dict:
    return _cw("cw8-flow-visualisation", "Flow visualisation: streamlines, pathlines and streaklines", "Fluid dynamics",
               "For an unsteady flow, compute a pathline, a streakline and a streamline by fourth-order Runge-Kutta and compare "
               "each with the closed-form solution.", "cw8_flow",
               {"cas": 0.0, "method": 0.0, "n": 8.0, "a": 0.3, "b": 1.0, "w": 2.0, "x0": 0.5, "y0": 0.0, "T": 3.0, "tau": 1.0, "S": 3.0}, 64,
               "A streamline is everywhere tangent to the velocity field at one instant; a pathline is the track of one fluid "
               "particle; a streakline joins all the particles that have passed through one point, as dye from a nozzle does. In a "
               "steady flow all three are the same curve. In the unsteady flow u = a x, v = -a y + b cos(w t) - a stagnation-point "
               "flow with a sideways oscillation - they differ, and each is the solution of a first-order differential equation: "
               "the pathline of dx/dt = u(x, t), the streakline of the same equation started at later release times, the streamline "
               "of dx/ds = u(x, t0) with the time frozen. Because the equations are linear, all three have closed forms, so the "
               "Runge-Kutta error can be measured; it falls as n^-4. Model units.",
               _steps("Read the flow, the release point and the time from the method card.",
                      "Compare the three curves on the screen: in an unsteady flow they are different."),
               [_q("In a steady flow streamlines, pathlines and streaklines", ["coincide", "are perpendicular", "never meet"],
                   "The velocity at each point never changes, so a particle follows the streamline through it."),
                _q("Dye released continuously from a fixed nozzle traces", ["a streakline", "a pathline", "a streamline"],
                   "It marks every particle that has passed the nozzle.")],
               [DULOCF, {"title": "P. K. Kundu and I. M. Cohen, Fluid Mechanics (Academic Press)", "note": "streamlines, pathlines and streaklines; cited, not re-fetched"}, MODEL, SIM],
               "STREAM / PATH / STREAK", digits=7)


def game_theory() -> dict:
    return _cw("cw8-game-theory", "Examples from game theory: evolutionary and zero-sum games", "Nonlinear dynamics",
               "Find the evolutionarily stable mix of the Hawk-Dove game by integrating the replicator equation, and the optimal "
               "mixed strategy of a zero-sum game by fictitious play.", "cw8_game",
               {"cas": 0.0, "method": 0.0, "n": 40.0, "V": 2.0, "C": 5.0, "p0": 0.1, "tend": 60.0, "a": 2.0, "b": -1.0, "c": -1.0, "d": 1.0}, 160,
               "In the Hawk-Dove game two animals contest a resource of value V; two hawks fight and the loser pays a cost C > V. "
               "If the fraction p of hawks changes in proportion to how much better hawks do than the average (the replicator "
               "equation dp/dt = p(1 - p)(V - C p)/2), it settles at p* = V/C, the evolutionarily stable state, from any start. "
               "In a zero-sum game the row player's best guaranteed mix in [[a, b], [c, d]] is p = (d - c)/(a + d - b - c) "
               "(von Neumann's minimax). Fictitious play reaches it by learning: each round, each player best-responds to the "
               "other's past frequencies; Robinson (1951) proved the frequencies converge for every zero-sum game. The program "
               "integrates the replicator equation by Euler steps (tend / n each) or plays n rounds; the payoffs are model numbers.",
               _steps("Read the game, its payoffs and the starting mix from the method card.",
                      "Watch the hawk fraction or the strategy frequency settle on the screen."),
               [_q("The evolutionarily stable fraction of hawks is", ["V / C", "1/2", "C / V"],
                   "At p = V/C hawks and doves earn the same, and any deviation is pushed back."),
                _q("In matching-type zero-sum games the optimal strategy is usually", ["a mixture of the pure strategies", "always the first row", "random with equal chances"],
                   "A predictable pure strategy can be exploited, so the minimax strategy mixes in a definite ratio.")],
               [DULOCF, {"title": "J. Maynard Smith, Evolution and the Theory of Games (Cambridge University Press, 1982)", "note": "the Hawk-Dove game; cited, not re-fetched"},
                {"title": "J. Robinson, An iterative method of solving a game, Annals of Mathematics 54, 296 (1951)", "note": "cited, not re-fetched"}, MODEL, SIM],
               "GAME THEORY", digits=6)


# ============================================================================================ Digital signal processing
def dsp_convolution() -> dict:
    return _cw("cw8-dsp-convolution", "Discrete sequences and convolution sums", "Digital signal processing",
               "Convolve two exponential sequences (and a gate with itself) by the direct convolution sum and by circular "
               "convolution through the DFT, and find the DFT length needed for the circular result to equal the linear one.",
               "cw8_conv", {"cas": 0.0, "method": 0.0, "n": 16.0, "al": 0.8, "be": 0.5, "Lx": 12.0, "Lh": 10.0, "m": 3.0}, 32,
               "The output of a linear time-invariant system is the convolution sum y[m] = sum over j of x[j] h[m - j]. For x[k] = "
               "al^k and h[k] = be^k it is a finite geometric series with a closed form. The same result can be computed through "
               "the discrete Fourier transform: multiply the DFTs of x and h and transform back. But the DFT of length N computes "
               "the CIRCULAR convolution, in which the tail of y beyond N wraps round onto its start (time aliasing). It equals the "
               "linear convolution only when N >= Lx + Lh - 1, the length of y; zero-padding to that length is how linear "
               "convolution is done with an FFT. The program shows both, and the error of the circular result until N is long enough.",
               _steps("Read the two sequences, their lengths and the output sample m from the method card.",
                      "Find the smallest DFT length that gives the exact y[m], and compare it with Lx + Lh - 1."),
               [_q("A DFT of length N computes the linear convolution correctly when", ["N >= Lx + Lh - 1", "N = Lx", "N is a power of 2"],
                   "Shorter lengths fold the tail of y back onto its start."),
                _q("The convolution of a gate of length 5 with itself is", ["a triangle of length 9", "a gate of length 10", "a sine"],
                   "Sliding one gate over the other gives an overlap that rises to 5 and falls again.")],
               [DULOCF, OPPENHEIM, MODEL, SIM], "y = x * h", digits=8)


def dsp_lti() -> dict:
    return _cw("cw8-dsp-lti", "LTI system from a difference equation: response, poles and zeros", "Digital signal processing",
               "Run the difference equation y[k] = a1 y[k-1] + a2 y[k-2] + b0 x[k] + b1 x[k-1] sample by sample, and get its "
               "frequency response from the impulse response and its steady state from the step response.", "cw8_lti",
               {"cas": 0.0, "method": 0.0, "what": 0.0, "n": 32.0, "r": 0.8, "th": 0.6, "b0": 1.0, "b1": 0.5, "w0": 0.6}, 160,
               "A difference equation defines a system completely: feed it a unit impulse and it produces the impulse response "
               "h[k]; feed it a step and it produces the step response. Its transfer function is H(z) = (b0 + b1 z^-1)/(1 - a1 z^-1 "
               "- a2 z^-2); the roots of the denominator are the poles (here r e^(+-i th): a1 = 2 r cos th, a2 = -r^2), the root of the "
               "numerator the zero -b1/b0. The frequency response is H on the unit circle, H(e^iw) = sum of h[k] e^(-iwk); its "
               "magnitude at w0 is computed from the first n samples of h. The step response settles to H(1) = (b0 + b1)/(1 - a1 - a2). "
               "Both truncation errors fall as r^n: poles near the unit circle give long ringing and slow convergence, and a pole "
               "outside it would make the system unstable.",
               _steps("Read the coefficients, the pole radius and angle and the frequency w0 from the method card.",
                      "See the pole-zero plot in the corner, and how the error falls as r^n."),
               [_q("A causal LTI system is stable when", ["all its poles lie inside the unit circle", "its zeros lie inside the unit circle", "a1 is positive"],
                   "Each pole contributes p^k to h[k], which must die away."),
                _q("The steady-state value of the step response is", ["H(z) at z = 1", "h[0]", "zero"],
                   "A step is the zero-frequency input, and z = e^(i 0) = 1.")],
               [DULOCF, OPPENHEIM, MODEL, SIM], "DIFFERENCE EQUATION", digits=7)


def dsp_fir() -> dict:
    return _cw("cw8-dsp-fir", "FIR low-pass filter design by windowing", "Digital signal processing",
               "Design a low-pass FIR filter with cut-off 1000 Hz at a sampling frequency of 5 kHz by windowing the ideal impulse "
               "response with a rectangular, a Hann and a Hamming window, and measure where the designed response falls to one half.",
               "cw8_fir", {"cas": 0.0, "method": 0.0, "n": 17.0, "wc": 0.4 * math.pi}, 65,
               "An ideal low-pass filter passing |w| < wc has the infinite impulse response sin(wc t)/(pi t). An FIR filter keeps N "
               "samples of it, centred, and multiplies them by a window. The rectangular window (simple truncation) gives the sharpest "
               "edge but the largest ripple (Gibbs); Hann and Hamming windows taper the ends, trading a wider transition for much "
               "smaller ripple and deeper stop-band attenuation. However the window is chosen, the transition is centred on the ideal "
               "edge, so the response passes through one half at wc. The program designs the filter, computes its amplitude "
               "response, finds the half-amplitude frequency by a scan and bisection, and compares it with wc = 2 pi 1000/5000 = "
               "0.4 pi rad/sample. The University of Delhi practical uses the rectangular window with length 17.",
               _steps("Read the cut-off, the sampling frequency, the window and the length N from the method card.",
                      "Compare the ripple and the transition of the three windows on the screen."),
               [_q("A Hamming window compared with a rectangular window gives", ["smaller ripple but a wider transition", "a sharper edge", "no stop band"],
                   "Tapering the ends lowers the side lobes of the window's spectrum and widens its main lobe."),
                _q("A cut-off of 1000 Hz at 5000 samples per second is a digital frequency of", ["0.4 pi rad/sample", "1000 rad/sample", "0.2 rad/sample"],
                   "w = 2 pi f / fs = 2 pi 1000 / 5000.")],
               [DULOCF, OPPENHEIM, SIM], "FIR BY WINDOWING", unit="rad/sample", digits=6)


# ============================================================================================ Advanced mathematical physics
def geodesics() -> dict:
    return _cw("cw8-geodesics", "Geodesics in Euclidean and curved spaces", "Mathematical physics",
               "Find the shortest path between two points in a plane and on the surface of a sphere by relaxing a trial path "
               "(the variational principle, done numerically), and compare its length with the straight line and the great circle.",
               "cw8_geod", {"cas": 0.0, "method": 0.0, "n": 8.0, "xa": 0.0, "ya": 0.0, "xb": 3.0, "yb": 1.0, "bump": 1.0,
                            "R": 1.0, "la1": 10.0, "lo1": 0.0, "la2": 50.0, "lo2": 100.0}, 32,
               "A geodesic makes the length integral stationary. Instead of solving the Euler-Lagrange equations, the program "
               "minimises the length directly: a path of n straight pieces starts as a wrong curve (a bump in the plane, a line of "
               "steady latitude-longitude change on the sphere), and every inner point is moved again and again to the midpoint of "
               "its neighbours - pushed back onto the sphere when there is one - until nothing moves. In the plane the result is "
               "the straight line; on the sphere it is the arc of the great circle through the two points, of length R times the "
               "angle between them. The chords of n pieces are slightly shorter than the arc, by a relative amount of about "
               "(angle/n)^2/24: that is the error measured. The sphere has unit radius (model units).",
               _steps("Read the two end points and the surface from the method card.",
                      "Compare the relaxed path with the starting path on the screen, and with the great circle."),
               [_q("On a sphere the shortest path between two points lies on", ["a great circle", "a line of latitude", "a line of longitude"],
                   "A great circle is the intersection with a plane through the centre; it is the sphere's 'straight line'."),
                _q("Why is the sum of n chords shorter than the arc?", ["A chord is shorter than the arc it spans", "Round-off", "The sphere is not round"],
                   "Each chord cuts across its arc; the difference falls as (angle/n)^2.")],
               [DULOCF, GOLDSTEIN, MODEL, SIM], "GEODESICS", digits=7)


def constrained_lagrangian() -> dict:
    return _cw("cw8-constrained-lagrangian", "Lagrangian mechanics with constraints", "Mechanics by computation",
               "Integrate a pendulum as a particle held on a circle by a Lagrange multiplier, an Atwood machine and a bead on a "
               "rotating hoop by fourth-order Runge-Kutta, and compare the measured period, acceleration or tension with theory.",
               "cw8_constr", {"cas": 0.0, "method": 0.0, "what": 0.0, "n": 32.0, "g": 9.80665, "L": 1.0, "th0": 30.0,
                              "m1": 0.3, "m2": 0.2, "R": 0.2, "w": 10.0, "amp": 0.0001, "periods": 3.0}, 128,
               "A constraint such as 'the bob stays at distance L from the pivot' can be removed by a good choice of coordinates, "
               "or kept, with a Lagrange multiplier lambda that supplies the constraint force: for a pendulum in Cartesian "
               "coordinates x'' = -lambda x, y'' = -lambda y - g, with lambda = (v^2 - g y)/r^2 found by differentiating the "
               "constraint twice - lambda times L is the string tension per unit mass. The program integrates this by Runge-Kutta, "
               "times the period from the zero crossings of x, and compares it with the exact 4 sqrt(L/g) K(sin(theta0/2)) (K by the "
               "arithmetic-geometric mean). For an Atwood machine the multiplier is the string tension, 2 m1 m2 g/(m1 + m2), and "
               "the acceleration is (m1 - m2) g/(m1 + m2). For a bead on a vertical hoop spun at w > sqrt(g/R) the constraint leaves "
               "one angle; the bead rests off the axis at cos theta0 = g/(w^2 R) and oscillates about it with angular frequency "
               "w sin theta0. g = 9.80665 m/s^2 (standard gravity, exact by definition).",
               _steps("Read the system, its constraint and the quantity from the method card.",
                      "Check how well the constraint is kept (the drift of r is shown) as the step shrinks."),
               [_q("The Lagrange multiplier of a pendulum's constraint is", ["the string tension (per unit mass and length)", "the angle", "the energy"],
                   "It is the force needed to keep the bob on the circle."),
                _q("A large-amplitude pendulum has a period that is", ["longer than 2 pi sqrt(L/g)", "shorter than 2 pi sqrt(L/g)", "the same"],
                   "K(k) > pi/2 for k > 0.")],
               [DULOCF, GOLDSTEIN, SASTRY,
                {"title": "CGPM 1901: standard acceleration of gravity 9.80665 m/s^2", "note": "exact by definition"}, SIM],
               "CONSTRAINED LAGRANGIAN", digits=6)


BUILDERS = (factorial_arrangements, frame_transformations, vector_field_operators, wave_group_dispersion,
            graphics_transformations, schrodinger_anharmonic, lennard_jones_md, partition_function_levels, maxwell_speeds,
            specific_heat_models, quantum_distributions, fractals, flow_visualisation, game_theory, dsp_convolution,
            dsp_lti, dsp_fir, geodesics, constrained_lagrangian)
