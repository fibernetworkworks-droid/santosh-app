"""Prayogshala lab pack `ug_mech_w7`: B.Sc. oscillation, elasticity, heat and harmonic-analysis set-ups of
`syllabus/physics/ug.json` (chapters Mechanics, Properties of matter, Oscillations / waves, Heat and thermodynamics).

Physics: the `ug_mech_w7` kernel pack (and its JavaScript twin). Three studio rigs draw the benches:
    rig `w7-oscillation-bench`  pendulums (simple, bar, Kater, coupled), loaded springs, coupled gliders on an air track,
                                Maxwell's needle and Searle's two bars: release, time N oscillations or read the decay
    rig `w7-heat-bench`         Stefan's law lamp, Callendar and Barnes' tube, Angstrom's bar, the method of cooling and a
                                thermocouple data logger
    rig `w7-harmonics-bench`    function generator, tunable filter and CRO
    rig `capillary-rise`        (existing) reused for capillary rise at several temperatures
Every lab's `check` compares a reading the kernel finds by its own simulated measurement with the textbook relation (1 %).
Constants: where a value is a material property its source is named; values recalled and not looked up are marked
"from memory - verify". Generic items (a damper vane, a coupling spring) are said to be generic. English only.
"""
from __future__ import annotations

from ..catalog import B, board, inst, knob, lab

SIM = {"title": "Hoola Prayogshala kernel", "note": "readings come from the simulation code; checked against the textbook formula in Hoola's tests"}
DU = {"title": "University of Delhi B.Sc. (Hons) Physics practical syllabus (Mechanics, Waves and Oscillations, Thermal Physics, Applied Dynamics labs)"}
HNB = {"title": "HNBGU four-year UG Physics (NEP) practical list - Waves and Acoustics, Thermal Physics"}
IP = {"title": "Practical Physics, Indu Prakash and Ramakrishna (Kater's pendulum, Maxwell's needle, Searle's method, method of cooling)"}
KL = {"title": "Kaye and Laby, Tables of Physical and Chemical Constants: elastic moduli of metals",
      "note": "from memory - verify: mild steel E 211.9 GPa, G 82.2 GPa; brass (70/30) E 100.6 GPa, G 37.3 GPa"}
GENERIC = {"title": "Generic apparatus", "note": "the damper vane, coupling spring, loads and bars are ordinary lab items, not named materials; their values are settings of this bench"}

G_OSC = "Physics · Oscillations"
G_PM = "Physics · Properties of matter"
G_HEAT = "Physics · Heat"
LEVEL = "B.Sc."
CH_MECH = "Mechanics"
CH_PM = "Properties of matter: elasticity, viscosity, surface tension"
CH_OSC = "Oscillations, waves and acoustics"
CH_HEAT = "Heat and thermodynamics"
DEG = 0.017453292519943295


def _q(q, opts, why):
    return {"q": q, "options": opts, "answer": 0, "why": why}


def _mk(id, rig, title, group, chapter, aim, kernel, params, knobs, insts, theory, steps, questions, sources, check,
        safety="Keep the stand clamped firmly and the swing small. Do not stand in the path of a swinging pendulum."):
    return lab(
        id=id, rig=rig, title=title, group=group, level=LEVEL, topic=chapter, chapter=chapter, aim=aim, kernel=kernel,
        params=params, autorun=False, camera={"pos": [0.6, 0.6, 1.4], "look": [0, 0.3, 0]}, floor=-0.03,
        bodies=[board(1.2, 0.6),
                B("stand", "cylinder", name="Stand", info="Holds the apparatus rigidly.", r=0.008, h=0.8, pos=[-0.2, 0.4, 0], color="steel"),
                B("body", "box", name="Apparatus", info="The oscillating body of this experiment.", size=[0.04, 0.3, 0.02], pos=[0, 0.4, 0], color="brass")],
        knobs=knobs, instruments=insts, steps=steps, theory=theory, safety=safety,
        tour=[{"say": "The apparatus is on the bench with a stopwatch and the record book."}],
        questions=questions, sources=sources, check=check)


_SW = inst("sw", "stopwatch", "Stopwatch")


def _ang():
    return inst("ang", "readout", "Displacement", "th_deg", unit="°", digits=1)


# =============================================================================================== PENDULUMS
def simple_damping() -> dict:
    return _mk(
        "w7-simple-pendulum-damping", "w7-oscillation-bench", "Damping coefficient, relaxation time and Q of a simple pendulum",
        G_OSC, CH_OSC,
        "Let a simple pendulum with a light card vane swing, read its amplitude every ten oscillations and find the "
        "damping coefficient, the relaxation time and the quality factor.",
        "w7_pend", {"kind": 0.0, "L": 1.0, "th0": 10 * DEG, "gam": 0.006, "mode": 1.0},
        [knob("gam", "Damper vane (hidden)", "gam", 0.002, 0.05, 0.0005, 0.006, "1/s", hidden=True)],
        [_ang(), _SW],
        "A lightly damped oscillator obeys θ'' + 2γ θ' + ω0² θ = 0, so its amplitude falls as A = A0 exp(−γ t). A graph "
        "of ln(A0 / A) against t is a straight line of slope γ, the damping coefficient. The energy falls as "
        "exp(−2γ t): the relaxation time is τ = 1 / (2γ), the time in which the energy falls to 1/e. The quality "
        "factor is Q = ω0 τ = π / (γ T).",
        ["Measure the length from the point of suspension to the centre of the bob.",
         "Pull the bob aside to about 10° and release it. Read the first amplitude on the scale under the bob.",
         "Read the amplitude after every 10 oscillations, up to 50, with the time on the stopwatch.",
         "Plot ln(A0 / A) against t. The slope is γ.", "τ = 1 / (2γ) and Q = π / (γ T)."],
        [_q("The amplitude of a lightly damped pendulum falls", ["exponentially with time", "linearly with time", "not at all"],
            "A = A0 exp(−γ t): equal times give equal ratios."),
         _q("A larger quality factor Q means", ["the oscillation dies away more slowly", "a shorter period", "a heavier bob"],
            "Q = ω0 τ counts how many radians of swing fit into one energy relaxation time.")],
        [HNB, GENERIC, SIM],
        {"params": {"gam": 0.006, "th0": 10 * DEG}, "reading": "gam", "textbook": "w7_pend_gam"})


def bar_damping() -> dict:
    return _mk(
        "w7-bar-pendulum-damping", "w7-oscillation-bench", "Damped oscillations of a bar pendulum with a damper vane",
        G_OSC, CH_OSC,
        "Fix a damper vane to a bar pendulum, read the falling amplitude of the swing and find the damping coefficient "
        "and the quality factor. Repeat with a vane of larger area.",
        "w7_pend", {"kind": 1.0, "Lb": 1.0, "h": 0.30, "th0": 8 * DEG, "gam": 0.010, "mode": 1.0},
        [knob("gam", "Damper vane (hidden)", "gam", 0.002, 0.08, 0.0005, 0.010, "1/s", hidden=True)],
        [_ang(), _SW],
        "A vane moving through the air adds a retarding couple proportional to the angular velocity, so "
        "θ'' + 2γ θ' + ω0² θ = 0 and the amplitude falls as A0 exp(−γ t). The slope of ln(A0 / A) against t is the "
        "damping coefficient γ. The quality factor is Q = ω0 / (2γ) = π / (γ T). A vane of larger area gives a larger "
        "γ and a smaller Q, while the period hardly changes.",
        ["Hang the bar on its knife edge through a hole 30 cm from the centre and fix the vane to its lower end.",
         "Draw the bar aside to about 8° and release it. Read the first amplitude on the scale behind the pointer.",
         "Read the amplitude after every 10 oscillations, up to 50, with the time.",
         "Plot ln(A0 / A) against t: the slope is γ. Then Q = π / (γ T).", "Change to the larger vane and repeat."],
        [_q("A damper vane of larger area makes", ["γ larger and Q smaller", "γ smaller and Q larger", "the period much longer"],
            "More air is pushed aside each swing, so the energy is lost faster."),
         _q("The damping coefficient is found from", ["the slope of ln(A0/A) against t", "the period alone", "the mass of the bar"],
            "A = A0 exp(−γ t) gives a straight line of slope γ.")],
        [DU, GENERIC, SIM],
        {"params": {"gam": 0.010, "th0": 8 * DEG}, "reading": "gam", "textbook": "w7_pend_gam"})


def bar_shm_limit() -> dict:
    return _mk(
        "w7-bar-pendulum-shm-limit", "w7-oscillation-bench", "Limit of angular amplitude for SHM in a bar pendulum",
        G_OSC, CH_OSC,
        "Time a bar pendulum at larger and larger amplitudes and find the amplitude up to which its period stays within "
        "1 % of the small-swing (simple harmonic) value.",
        "w7_pend", {"kind": 1.0, "Lb": 1.0, "h": 0.30, "th0": 5 * DEG, "gam": 0.0, "mode": 2.0, "eps": 0.01},
        [knob("amp", "Angular amplitude", "th0", 2, 40, 1, 5, "°", DEG)],
        [_ang(), _SW],
        "The restoring couple of a pendulum is proportional to sin θ, not θ. The motion is simple harmonic only while "
        "sin θ ≈ θ. For a finite amplitude θ0 the period is T = T0 (1 + θ0²/16 + 11 θ0⁴/3072 + ...), so T against θ0² is "
        "nearly a straight line of slope T0/16. The amplitude at which T has grown by 1 % is taken here as the limit "
        "of simple harmonic motion: about 0.40 rad (23°).",
        ["Hang the bar on its knife edge. Time 10 oscillations at 5°.", "Repeat at 10°, 15°, 20°, 25°, 30° and 35°.",
         "Plot T against θ0² (θ0 in radian).", "From the line find the amplitude at which T is 1 % above its small-swing value."],
        [_q("The period of a pendulum at a large amplitude is", ["longer than at a small amplitude", "shorter", "the same"],
            "sin θ is smaller than θ, so the restoring couple is weaker and the swing takes longer."),
         _q("Why is the knife edge kept sharp and clean?", ["So friction does not reduce the amplitude during timing", "To make the bar heavier", "To change g"],
            "The amplitude must stay close to its starting value while the oscillations are timed.")],
        [DU, SIM],
        {"params": {}, "reading": "th_lim", "textbook": "w7_pend_lim"})


def photogate() -> dict:
    return _mk(
        "w7-arduino-pendulum-photogate", "w7-oscillation-bench", "Bar pendulum period and g with an Arduino photo-gate",
        G_OSC, CH_MECH,
        "Let the lower end of a bar pendulum cut the beam of a photo-gate read by an Arduino, take the period from the "
        "display for several holes and find g.",
        "w7_pend", {"kind": 1.0, "Lb": 1.0, "h": 0.25, "th0": 3 * DEG, "gam": 0.0, "mode": 0.0, "g": 9.79},
        [knob("g", "Local g (hidden)", "g", 9.7, 9.9, 0.001, 9.79, "m/s²", hidden=True),
         knob("h", "Knife edge to centre h", "h", 15, 45, 5, 25, "cm", 0.01)],
        [_ang(), _SW],
        "A bar hung on a knife edge h from its centre of gravity is a compound pendulum of period "
        "T = 2π √((k² + h²) / (g h)), with k² = L²/12 for a uniform bar. The photo-gate's beam is cut twice in every "
        "oscillation; the Arduino times every second cut with its microsecond clock and shows the mean of ten "
        "periods. Then g = 4π² (k² + h²) / (h T²).",
        ["Hang the bar through the hole 25 cm from its centre. Place the photo-gate so the lower end cuts the beam at rest.",
         "Draw the bar aside about 3° and release it. Read the period from the display.",
         "Repeat for the holes at 20, 30, 35 and 40 cm.", "Work out g for each hole and take the mean."],
        [_q("Why does the Arduino time every second cut of the beam?", ["One full oscillation passes the gate twice", "The first cut is always wrong", "To save memory"],
            "The bar crosses its rest position twice in each period."),
         _q("What limits the accuracy of g here?", ["The measured lengths h and L", "The Arduino clock", "The colour of the bar"],
            "The clock resolves microseconds; the scale reads only to a millimetre.")],
        [DU, {"title": "g = 9.79 m/s² is a typical value for the north Indian plains", "note": "illustrative local value, hidden in the lab; not a surveyed figure"}, SIM],
        {"params": {"h": 0.25, "g": 9.79}, "reading": "g", "textbook": "w7_pend_g"})


def kater() -> dict:
    return _mk(
        "w7-kater-pendulum", "w7-oscillation-bench", "g with Kater's reversible pendulum", G_OSC, CH_OSC,
        "Time Kater's pendulum about each of its two knife edges, measure their distances from the centre of gravity "
        "and find g from Bessel's formula.",
        "w7_kater", {"h1": 0.60, "h2": 0.35, "k2": 0.2103, "th0": 0.05, "g": 9.8},
        [knob("g", "Local g (hidden)", "g", 9.7, 9.9, 0.001, 9.8, "m/s²", hidden=True)],
        [_ang(), _SW],
        "About a knife edge h from the centre of gravity the period is T = 2π √((k² + h²) / (g h)). If the periods "
        "about the two knife edges are exactly equal, the distance between them is the length of the equivalent "
        "simple pendulum and g = 4π² (h1 + h2) / T². Exact equality is hard to reach, so Bessel's formula is used: "
        "8π² / g = (T1² + T2²) / (h1 + h2) + (T1² − T2²) / (h1 − h2). It holds whether or not T1 equals T2.",
        ["Balance the pendulum on a wedge to find its centre of gravity; measure h1 and h2 to the two knife edges.",
         "Hang it from knife edge K1 and time 20 oscillations of small amplitude. Repeat.",
         "Turn the pendulum over, hang it from K2 and time 20 oscillations. Repeat.",
         "Work out g from Bessel's formula."],
        [_q("Why is Kater's pendulum made reversible?", ["So the awkward radius of gyration drops out", "To make it lighter", "To double the period"],
            "Two periods about two parallel axes eliminate k², leaving only lengths and times."),
         _q("In Bessel's formula the second term is small because", ["T1 and T2 are nearly equal", "h1 equals h2", "g is large"],
            "T1² − T2² is tiny, so the uncertain position of the centre of gravity hardly matters.")],
        [DU, IP, SIM],
        {"params": {"k2": 0.2103, "g": 9.8}, "reading": "g", "textbook": "w7_kater_g"})


def coupled_pendulums() -> dict:
    return _mk(
        "w7-coupled-pendulums", "w7-oscillation-bench", "Normal modes and beats of two coupled pendulums", G_OSC, CH_OSC,
        "Join two equal pendulums with a light spring, time the in-phase and out-of-phase normal modes, find the "
        "coupling coefficient and compare the beat period with the one the two modes predict.",
        "w7_coupled", {"kind": 0.0, "L": 0.6, "a": 0.3, "m": 0.2, "kc": 1.0, "A0": 0.08, "mode": 0.0},
        [knob("kc", "Coupling spring (hidden)", "kc", 0.2, 5, 0.05, 1.0, "N/m", hidden=True)],
        [inst("x1", "readout", "Pendulum A", "x1", k=57.29578, unit="°", digits=1), _SW],
        "Two equal pendulums joined by a spring have two normal modes. In phase, the spring is never stretched and "
        "ω1² = g / L. Out of phase, it is stretched twice over and ω2² = g / L + 2 k a² / (m L²). The coupling "
        "coefficient is κ = (ω2² − ω1²) / (ω2² + ω1²) = (T1² − T2²) / (T1² + T2²). If only one pendulum is displaced, "
        "both modes are excited and the energy passes to and fro: the beat period is Tb = T1 T2 / (T1 − T2).",
        ["Check that the two pendulums alone have the same period. Hook the spring 30 cm below the pivots.",
         "Draw both bobs aside the same way, release them together and time 20 oscillations: T1.",
         "Draw them aside in opposite ways, release and time 20 oscillations: T2.",
         "Hold one bob at rest, displace the other and release both: time from one standstill of that bob to the next: Tb.",
         "κ = (T1² − T2²) / (T1² + T2²); compare Tb with T1 T2 / (T1 − T2)."],
        [_q("In the in-phase mode the coupling spring", ["keeps its natural length", "is stretched the most", "breaks the symmetry"],
            "Both bobs move together, so the spring's ends never move apart."),
         _q("Beats appear when", ["both normal modes are excited together", "only the in-phase mode is excited", "the spring is removed"],
            "The two slightly different frequencies drift in and out of step.")],
        [DU, GENERIC, SIM],
        {"params": {"kc": 1.0}, "reading": "kappa", "textbook": "w7_coupled_kappa"})


# =============================================================================================== SPRINGS
def _spring(id, title, aim, params, knobs, theory, steps, questions, check, chapter=CH_OSC, sources=None):
    return _mk(id, "w7-oscillation-bench", title, G_OSC, chapter, aim, "w7_spring", params, knobs,
               [inst("x", "readout", "Displacement from rest", "x", k=1000, unit="mm", digits=1), _SW],
               theory, steps, questions, sources or [DU, GENERIC, SIM], check,
               safety="Do not overload the spring: keep within the loads given. Keep your face away from a stretched spring.")


def spring_static_dynamic() -> dict:
    return _spring(
        "w7-spring-static-dynamic", "Spring-mass system by the static and dynamic methods",
        "Load a helical spring, read its extension, then time its vertical oscillations, and find the spring constant, "
        "g and the mass of the spring.",
        {"k1": 22.0, "ms": 0.045, "m": 0.2, "x0": 0.02, "mode": 0.0, "geo": 0.0},
        [knob("k1", "Spring (k hidden)", "k1", 8, 60, 0.5, 22, "N/m", hidden=True),
         knob("ms", "Mass of the spring (hidden)", "ms", 0, 150, 1, 45, "g", 0.001, hidden=True),
         knob("m", "Load on the hanger", "m", 100, 300, 50, 200, "g", 0.001)],
        "Static method: a load m stretches the spring by x = m g / k, so x against m is a straight line of slope g / k. "
        "Dynamic method: the loaded spring oscillates with T = 2π √((m + ms/3) / k), because one third of the spring's "
        "own mass ms moves with the load. T² against m is a straight line of slope 4π² / k whose intercept on the "
        "m axis is −ms/3. The slope gives k; with k, the static slope gives g and the intercept gives ms.",
        ["Hang the spring with its hanger and note the pointer reading with no load.",
         "Add 100 g and read the extension. Then pull the load down 2 cm, release and time 20 oscillations.",
         "Repeat for 150, 200, 250 and 300 g.", "Plot x against m and T² against m.",
         "k = 4π² / (slope of T² against m); g = k × (slope of x against m); ms = 3 × (intercept ÷ slope)."],
        [_q("Why is ms/3 added to the load in the period?", ["Each part of the spring moves, the lower parts the most", "The spring is weighed three times", "Air drag"],
            "The kinetic energy of a uniform spring equals that of one third of its mass moving with the load."),
         _q("The slope of T² against m is", ["4π² / k", "k / 4π²", "g / k"], "T² = 4π² (m + ms/3) / k.")],
        {"params": {"k1": 22.0, "ms": 0.045, "m": 0.2}, "reading": "T", "textbook": "w7_spring_T"})


def springs_combo() -> dict:
    return _spring(
        "w7-springs-series-parallel", "Spring constant of two springs in series and in parallel",
        "Join two light springs end to end, or side by side, load the combination and find its effective spring "
        "constant from the period of oscillation and from the extension.",
        {"k1": 30.0, "k2": 45.0, "ms": 0.0, "m": 0.2, "x0": 0.015, "mode": 1.0, "geo": 0.0},
        [knob("m", "Load on the hanger", "m", 100, 300, 50, 200, "g", 0.001)],
        "In series both springs carry the same force and their extensions add: 1/k = 1/k1 + 1/k2, so the combination "
        "is softer than either. In parallel they share the force and stretch equally: k = k1 + k2, stiffer than "
        "either. The effective constant is found as for one spring: T² against m has the slope 4π² / k, and x "
        "against m has the slope g / k. The two springs here are light, so their own mass is neglected.",
        ["Find k1 and k2 of each spring alone (their values are on the tags).", "Join the springs and hang the hanger.",
         "For loads of 100 to 300 g read the extension, then time 20 oscillations.",
         "Plot T² against m: k = 4π² / slope.", "Compare with k1 k2 / (k1 + k2) in series or k1 + k2 in parallel."],
        [_q("Two springs in series are", ["softer than either spring", "stiffer than either", "as stiff as the stiffer one"],
            "The same force stretches both, so the total extension is larger."),
         _q("Two springs in parallel have k equal to", ["k1 + k2", "k1 k2 / (k1 + k2)", "the mean of k1 and k2"],
            "They stretch equally and their forces add.")],
        {"params": {"k1": 30.0, "k2": 45.0, "m": 0.2}, "reading": "k", "textbook": "w7_spring_k"})


def spring_rigidity() -> dict:
    return _spring(
        "w7-spring-rigidity", "Modulus of rigidity of the wire of a helical spring from its oscillations",
        "Time the vertical oscillations of a loaded steel spring, find its spring constant and from the size of the "
        "wire and the coil find the modulus of rigidity of the wire.",
        {"geo": 1.0, "eta": 7.93e10, "rw": 0.0006, "Rc": 0.010, "Nt": 60.0, "ms": 0.04, "m": 0.2, "x0": 0.015, "mode": 0.0},
        [knob("eta", "Spring wire (η hidden)", "eta", 20, 90, 0.01, 79.3, "GPa", 1e9, hidden=True),
         knob("m", "Load on the hanger", "m", 100, 300, 50, 200, "g", 0.001)],
        "When a flat helical spring is stretched its wire is twisted, not pulled. For N turns of mean radius R wound "
        "from wire of radius r the spring constant is k = η r⁴ / (4 N R³), where η is the modulus of rigidity of the "
        "wire. k comes from the oscillations: T² against the load m is a straight line of slope 4π² / k. "
        "Then η = 4 N R³ k / r⁴.",
        ["Count the turns N. Measure the outer diameter of the coil with vernier callipers and the wire with a screw gauge.",
         "Hang the spring, add 100 g, pull the load down and time 20 oscillations.", "Repeat for 150 to 300 g.",
         "Plot T² against m: k = 4π² / slope.", "η = 4 N R³ k / r⁴."],
        [_q("Stretching a helical spring mainly", ["twists its wire", "stretches its wire", "bends the hook"],
            "Each turn of the wire is twisted a little, which is why the rigidity modulus appears."),
         _q("Which measurement matters most for η?", ["The radius of the wire, since it enters as r⁴", "The number of turns", "The load"],
            "A 1 % error in r becomes a 4 % error in η.")],
        {"params": {"eta": 7.93e10, "m": 0.2}, "reading": "eta", "textbook": "w7_spring_eta"}, chapter=CH_MECH,
        sources=[{"title": "UGC LOCF Physics 2019, Mechanics Lab: motion of a spring, modulus of rigidity"},
                 {"title": "Shear modulus of spring steel (music wire) 79.3 GPa: Shigley's Mechanical Engineering Design, spring materials table",
                  "note": "from memory - verify"}, SIM])


def coupled_springs() -> dict:
    return _mk(
        "w7-coupled-spring-oscillators", "w7-oscillation-bench", "Coupled spring oscillators on an air track", G_OSC, CH_OSC,
        "Join two equal gliders on an air track with three springs, time the two normal modes and find the coupling "
        "coefficient; with damping magnets fitted, find the damping coefficient too.",
        "w7_coupled", {"kind": 1.0, "m": 0.2, "k": 4.0, "kc": 1.0, "A0": 0.04, "gam": 0.0, "mode": 0.0},
        [knob("kc", "Middle spring (hidden)", "kc", 0.2, 5, 0.05, 1.0, "N/m", hidden=True),
         knob("gam", "Damping magnets (hidden)", "gam", 0, 0.2, 0.001, 0.0, "1/s", hidden=True)],
        [inst("x1", "readout", "Glider A", "x1", k=1000, unit="mm", digits=1), _SW],
        "Two gliders of mass m are each tied to an end post by a spring k and to each other by a spring kc. Moving "
        "together they leave the middle spring unstretched: ω1² = k / m. Moving oppositely: ω2² = (k + 2 kc) / m. The "
        "coupling coefficient is κ = (ω2² − ω1²) / (ω2² + ω1²) = (T1² − T2²) / (T1² + T2²). Magnets on the gliders "
        "induce eddy currents in the track and add a force proportional to the velocity: each mode then decays as "
        "exp(−γ t), and the slope of ln(A0 / A) against t gives the damping coefficient γ.",
        ["Level the track and switch the blower on. Check that each glider alone has the same period.",
         "Displace both gliders the same way, release them together and time 20 oscillations: T1.",
         "Displace them in opposite ways, release and time 20 oscillations: T2.",
         "κ = (T1² − T2²) / (T1² + T2²).",
         "With the damping magnets fitted, read the amplitude of the in-phase mode every 5 oscillations and find γ."],
        [_q("In the in-phase mode the middle spring", ["is not stretched", "does all the work", "is stretched twice as much"],
            "Both gliders move together, so the middle spring keeps its length."),
         _q("The damping magnets act by", ["eddy currents in the aluminium track", "friction with the track", "making the gliders heavier"],
            "A moving magnet induces currents in the metal that oppose its motion.")],
        [{"title": "University of Delhi B.Sc. (Hons) Physics, DSE Applied Dynamics Lab: coupled oscillators"}, GENERIC, SIM],
        {"params": {"kc": 1.0, "k": 4.0}, "reading": "kappa", "textbook": "w7_coupled_kappa"},
        safety="Keep the blower hose clear and the track level. Do not drop the gliders: a dented glider drags.")


# =============================================================================================== ELASTICITY
def maxwell_needle() -> dict:
    return _mk(
        "w7-maxwell-needle", "w7-oscillation-bench", "Modulus of rigidity of a wire with Maxwell's needle", G_PM, CH_PM,
        "Time the torsional oscillations of Maxwell's needle with its solid cylinders outside and then inside, and "
        "find the modulus of rigidity of the suspension wire.",
        "w7_torsion", {"kind": 0.0, "eta": 8.22e10, "rw": 0.0005, "lw": 0.4, "Ln": 0.4, "ms": 0.216, "mh": 0.06,
                       "I0": 0.002, "pos": 0.0, "th0": 0.2},
        [knob("eta", "Wire (η hidden)", "eta", 20, 90, 0.01, 82.2, "GPa", 1e9, hidden=True)],
        [_ang(), _SW],
        "Maxwell's needle is a hollow tube of length L hung at its middle from the wire. It holds four cylinders, "
        "each L/4 long: two solid (mass ms) and two hollow (mass mh). Changing them over, from solids outside to "
        "hollows outside, changes the moment of inertia by (ms − mh) L² / 4 without changing the total mass. With "
        "T = 2π √(I / C) and C = π η r⁴ / (2 l) for a wire of length l and radius r, "
        "η = 2π l (ms − mh) L² / (r⁴ (T1² − T2²)).",
        ["Measure the wire: length l with a metre scale, diameter with a screw gauge at several places.",
         "Weigh a solid and a hollow cylinder and measure the length L of the tube.",
         "With the solid cylinders outside, twist the needle a little and time 10 oscillations: T1.",
         "Change the cylinders over (hollow outside) and time 10 oscillations: T2.",
         "η = 2π l (ms − mh) L² / (r⁴ (T1² − T2²))."],
        [_q("Why are the cylinders changed over instead of removed?", ["The load on the wire stays the same", "It is quicker", "To change the wire"],
            "The same total mass keeps the wire's tension and the needle's level unchanged."),
         _q("The radius of the wire must be measured most carefully because", ["it enters as the fourth power", "the wire is long", "it is made of steel"],
            "A 1 % error in r gives a 4 % error in η.")],
        [DU, IP, KL, SIM],
        {"params": {"eta": 8.22e10}, "reading": "eta", "textbook": "w7_tors_eta"},
        safety="Do not kink the suspension wire. Keep the twist small and steady the needle before timing.")


def searle_bars() -> dict:
    return _mk(
        "w7-searle-elastic-constants", "w7-oscillation-bench", "Elastic constants of a wire by Searle's two-bar method", G_PM, CH_PM,
        "Join two equal bars by a short wire, time their oscillations when the wire bends and when it twists, and find "
        "Young's modulus, the modulus of rigidity and Poisson's ratio of the wire.",
        "w7_torsion", {"kind": 1.0, "Y": 2.119e11, "eta": 8.22e10, "rw": 0.0005, "lw": 0.3, "Mb": 0.45, "Lbar": 0.3,
                       "wb": 0.012, "pos": 0.0, "th0": 0.12},
        [knob("Y", "Wire (Y hidden)", "Y", 50, 250, 0.01, 211.9, "GPa", 1e9, hidden=True),
         knob("eta", "Wire (η hidden)", "eta", 20, 90, 0.01, 82.2, "GPa", 1e9, hidden=True)],
        [_ang(), _SW],
        "Two equal bars hang by threads with the wire of length l and radius r joining their middles. Swinging in "
        "the horizontal plane, towards and away from each other, they bend the wire into an arc: "
        "T1 = 2π √(2 I l / (π Y r⁴)), so Y = 8π I l / (T1² r⁴). With one bar clamped and the other hanging from the "
        "wire and twisting it, T2 = 2π √(2 I l / (π η r⁴)), so η = 8π I l / (T2² r⁴). I = M (L² + b²) / 12 is the "
        "moment of inertia of a bar. Poisson's ratio follows without any dimensions: σ = Y / 2η − 1 = T2² / (2 T1²) − 1.",
        ["Weigh a bar and measure its length and breadth; measure the length and the diameter of the wire.",
         "Hang the two bars by their threads. Draw their ends together a little and release: time 20 oscillations, T1.",
         "Clamp one bar and let the other hang from the wire. Twist it a little and time 20 oscillations: T2.",
         "Y = 8π I l / (T1² r⁴) and η = 8π I l / (T2² r⁴).", "σ = T2² / (2 T1²) − 1."],
        [_q("Poisson's ratio comes from", ["the two periods alone", "the mass of the bars", "the length of the threads"],
            "σ = T2² / (2 T1²) − 1: every dimension cancels."),
         _q("In the first arrangement the wire is", ["bent into an arc", "twisted", "stretched"],
            "The bars turn opposite ways and bend the wire, which is why Young's modulus appears.")],
        [DU, IP, KL, SIM],
        {"params": {"Y": 2.119e11, "eta": 8.22e10}, "reading": "Y", "textbook": "w7_tors_Y"},
        safety="Keep the amplitude small so the wire is not bent permanently. Do not kink the wire while clamping it.")


BUILDERS = (simple_damping, bar_damping, bar_shm_limit, photogate, kater, coupled_pendulums, spring_static_dynamic,
            springs_combo, spring_rigidity, coupled_springs, maxwell_needle, searle_bars)


# =============================================================================================== HEAT
CODATA = {"title": "CODATA 2018: Stefan-Boltzmann constant 5.670374 × 10⁻⁸ W m⁻² K⁻⁴ (exact from the defined constants)"}
CRC_CU = {"title": "CRC Handbook of Chemistry and Physics: copper at 300 K, K = 401 W/(m K), density 8960 kg/m³, specific heat 385 J/(kg K)",
          "note": "the diffusivity used, 1.1625 × 10⁻⁴ m²/s, is K / (ρ c) from these three values"}
HEAT_SAFE = "Hot parts stay hot after the supply is off. Keep water away from the mains leads and switch off before changing a connection."


def _heat(id, title, aim, kernel, params, knobs, insts, theory, steps, questions, sources, check, safety=HEAT_SAFE):
    return lab(
        id=id, rig="w7-heat-bench", title=title, group=G_HEAT, level=LEVEL, topic=CH_HEAT, chapter=CH_HEAT, aim=aim,
        kernel=kernel, params=params, autorun=False, camera={"pos": [0.4, 0.5, 1.2], "look": [0, 0.1, -0.2]}, floor=-0.03,
        bodies=[board(1.4, 0.7),
                B("app", "box", name="Apparatus", info="The heated body of this experiment.", size=[0.3, 0.05, 0.05], pos=[0, 0.1, -0.2], color="copper"),
                B("box", "box", name="Supply and meters", info="Supply, meters or the data logger.", size=[0.2, 0.1, 0.12], pos=[0.45, 0.05, -0.2], color="#2b2f36")],
        knobs=knobs, instruments=insts, steps=steps, theory=theory, safety=safety,
        tour=[{"say": "The apparatus is on the bench with its supply, its meters and the record book."}],
        questions=questions, sources=sources, check=check)


def stefan() -> dict:
    return _heat(
        "w7-stefan-lamp", "Stefan's law and Stefan's constant with a tungsten lamp",
        "Run a vacuum tungsten lamp at several voltages, find the filament temperature from its resistance, show that "
        "the radiated power goes as the fourth power of T and find Stefan's constant.",
        "w7_stefan", {"V": 6.0},
        [knob("V", "Lamp voltage", "V", 2, 12, 0.5, 6, "V"),
         knob("sigma", "Stefan's constant (hidden)", "sigma", 4.0, 7.0, 0.000001, 5.670374, "×10⁻⁸ W/(m² K⁴)", 1e-8, hidden=True)],
        [inst("i", "readout", "Lamp current", "I", unit="A", digits=3), inst("tt", "readout", "Filament temperature", "T", unit="K", digits=0)],
        "In an evacuated lamp the filament loses heat only by radiation, so the electrical power equals the radiated "
        "power: V I = e σ A (T⁴ − T0⁴), with e the emissivity and A the surface area of the filament. The temperature "
        "comes from the filament's resistance: for tungsten R / R0 = (T / T0)^1.2 closely. A graph of log P against "
        "log T is a straight line whose slope is the exponent of T (4 by Stefan's law), and σ = P / (e A (T⁴ − T0⁴)).",
        ["Note the room temperature T0 and the cold resistance R0 of the lamp (measured with a very small current).",
         "Raise the lamp voltage in steps from 4 V to 12 V; at each step read V and I.",
         "Work out R = V / I, T = T0 (R / R0)^(1/1.2) and P = V I.",
         "Plot log P against log T: the slope is the exponent of T.", "σ = P / (e A (T⁴ − T0⁴))."],
        [_q("Why must the lamp be evacuated?", ["So the filament loses heat only by radiation", "To make it brighter", "To cool the glass"],
            "A gas would carry heat away by conduction and convection."),
         _q("If the absolute temperature of the filament doubles, the radiated power becomes", ["16 times", "twice", "4 times"],
            "P is proportional to T⁴.")],
        [CODATA, DU,
         {"title": "Tungsten lamp data used: R ∝ T^1.2 and total emissivity 0.35",
          "note": "from memory - verify: the T^1.2 resistance law is the usual lab approximation; tungsten's emissivity really rises with T (about 0.26 to 0.35 between 1800 and 3000 K). The filament area is a setting of this bench."}, SIM],
        {"params": {"V": 6.0}, "reading": "sigma", "textbook": "w7_stefan_sigma"})


def callendar_barnes() -> dict:
    return _heat(
        "w7-callendar-barnes", "Mechanical equivalent of heat by Callendar and Barnes' constant-flow method",
        "Pass a steady stream of water over a heater wire, read the steady rise in temperature for two rates of flow "
        "and find J, the mechanical equivalent of heat, with the heat loss eliminated.",
        "w7_cbarnes", {"V": 6.0, "mdot": 1.5, "mdot2": 0.9},
        [knob("J", "J (hidden)", "J", 3.5, 5.0, 0.0001, 4.1855, "J/cal", hidden=True),
         knob("hl", "Heat leak (hidden)", "hl", 0, 1, 0.01, 0.25, "W/K", hidden=True)],
        [inst("dt", "readout", "Rise of the water", "dT", unit="K", digits=2), inst("i", "readout", "Heater current", "I", unit="A", digits=2), _SW],
        "Water flows steadily through a narrow tube along a heater wire, inside a vacuum jacket. When the readings "
        "are steady, the electrical energy supplied in a time t heats the water that has flowed and supplies the "
        "small loss h: V I t = J (m s Δθ + h). A second run with a different flow, and the voltage changed until the "
        "rise Δθ is the same, has the same loss, so it cancels: J = (V1 I1 − V2 I2) t / ((m1 − m2) s Δθ). With s in "
        "cal/(g K), J comes out in joule per calorie.",
        ["Start the water from the constant-head tank and switch the heater on.",
         "Wait until both thermometers are steady. Read V, I and the rise Δθ, and collect the water for 60 s.",
         "Change the rate of flow. Adjust the voltage until Δθ is the same as before, and wait for the steady state.",
         "Again read V and I and collect the water for 60 s.", "J = (V1 I1 − V2 I2) t / ((m1 − m2) s Δθ)."],
        [_q("Why are two rates of flow used?", ["To eliminate the heat lost to the surroundings", "To save water", "To change the specific heat"],
            "With the same temperature rise the loss is the same in both runs and cancels on subtraction."),
         _q("A great advantage of the constant-flow method is that", ["the heat capacity of the apparatus does not enter", "it needs no thermometer", "it works without a heater"],
            "In the steady state no part of the apparatus is changing temperature.")],
        [{"title": "1 calorie (15 °C) = 4.1855 J: NIST Special Publication 811, Guide for the Use of the SI, conversion factors"}, DU, IP, SIM],
        {"params": {}, "reading": "J", "textbook": "w7_cbarnes_J"})


def angstrom() -> dict:
    return _heat(
        "w7-angstrom-bar", "Thermal conductivity of copper by Angstrom's method",
        "Heat one end of a long copper bar periodically, record the temperature waves at two points and find the "
        "thermal diffusivity and conductivity from their amplitudes and time lag.",
        "w7_angstrom", {"tau": 120.0},
        [knob("D", "Bar (diffusivity hidden)", "D", 0.1, 2.0, 0.0001, 1.1625, "cm²/s", 1e-4, hidden=True),
         knob("tau", "Heating period", "tau", 60, 240, 60, 120, "s")],
        [inst("t1", "readout", "Thermocouple 1", "T1", unit="°C", digits=2), inst("t2", "readout", "Thermocouple 2", "T2", unit="°C", digits=2), _SW],
        "When one end of a bar is heated and cooled with a period τ, a damped temperature wave runs along it: "
        "θ = A0 exp(−a x) sin(ω t − b x). Heat lost from the surface makes a and b unequal, but their product is "
        "always a b = ω / (2 D), where D = K / (ρ c) is the thermal diffusivity. Two thermocouples a distance Δx apart "
        "give a = ln(A1 / A2) / Δx from the amplitudes and b = ω Δt / Δx from the time lag of the peaks, so "
        "D = Δx² / (2 Δt ln(A1 / A2)) and K = D ρ c.",
        ["Measure the distance between the two thermocouple junctions.",
         "Set the heater to switch with a period of 120 s and let several periods pass until the record repeats.",
         "From the record read the amplitude of each temperature wave and the time by which the far peak lags.",
         "Repeat with periods of 180 s and 240 s.", "D = Δx² / (2 Δt ln(A1 / A2)) and K = D ρ c."],
        [_q("Why does the far thermocouple show a smaller swing?", ["The temperature wave is damped as it travels", "It is a weaker thermocouple", "The bar is thinner there"],
            "The amplitude falls as exp(−a x) along the bar."),
         _q("Angstrom's method does not need", ["the heat loss from the surface to be known", "a clock", "two thermocouples"],
            "The product a b = ω / 2D holds whatever the surface loss is.")],
        [CRC_CU, DU, SIM],
        {"params": {"tau": 120.0}, "reading": "D", "textbook": "w7_angstrom_D"})


def cooling_method() -> dict:
    return _heat(
        "w7-specific-heat-cooling", "Specific heat of a liquid by the method of cooling",
        "Let equal volumes of water and of a liquid cool in identical calorimeters in the same enclosure, time them "
        "over the same fall of temperature and find the specific heat of the liquid.",
        "w7_cool", {"cl": 2010.0, "rhol": 810.0},
        [knob("cl", "Liquid (specific heat hidden)", "cl", 800, 4200, 1, 2010, "J/(kg·K)", hidden=True)],
        [inst("t", "readout", "Thermometer", "T", unit="°C", lc=0.1, digits=1), _SW],
        "Two identical blackened calorimeters with the same exposed surface, in the same enclosure, lose heat at the "
        "same rate when they are at the same temperature (Newton's law of cooling). So the times they take to cool "
        "through the same range are in the ratio of their heat capacities: (m_l c_l + W) / (m_w c_w + W) = t_l / t_w, "
        "where W is the water equivalent (heat capacity) of a calorimeter with its stirrer. Hence "
        "c_l = ((m_w c_w + W) t_l / t_w − W) / m_l.",
        ["Weigh the two calorimeters empty, then with equal volumes of water and of the liquid.",
         "Fill both with their liquids at about 72 °C and put them in the enclosure with their lids on.",
         "Stir gently. For each, time the fall from 65 °C to 55 °C.", "Repeat for the fall from 60 °C to 50 °C.",
         "c_l = ((m_w c_w + W) t_l / t_w − W) / m_l."],
        [_q("Why must the two calorimeters be identical and equally filled?", ["So they lose heat at the same rate at the same temperature", "So they weigh the same", "So the liquids mix"],
            "The rate of loss depends on the surface and its temperature excess, not on what is inside."),
         _q("A liquid of lower heat capacity cools", ["faster than water", "slower than water", "at the same rate"],
            "The same rate of heat loss lowers its temperature more quickly.")],
        [IP, {"title": "Kerosene: specific heat 2010 J/(kg K), density 810 kg/m³ (Engineering ToolBox, liquids tables)", "note": "from memory - verify"},
         {"title": "Water 4186 J/(kg K), 998.2 kg/m³; copper 385 J/(kg K): CRC Handbook of Chemistry and Physics"}, SIM],
        {"params": {"cl": 2010.0, "rhol": 810.0}, "reading": "cl", "textbook": "w7_cool_cl"},
        safety="The liquids are hot: handle the calorimeters by their lids. Kerosene and turpentine are flammable: no flame on the bench; warm them in a water bath only.")


def cooling_daq() -> dict:
    return _heat(
        "w7-cooling-curve-daq", "Cooling of a hot object recorded with a thermocouple and data acquisition",
        "Record the temperature of a hot metal block with a thermocouple and a data logger as it cools in air, and "
        "find the cooling constant of Newton's law of cooling.",
        "cooling", {"T0": 90.0, "Ts": 28.0, "k": 0.003},
        [knob("k", "Block and air (k hidden)", "k", 0.0005, 0.02, 0.0001, 0.003, "1/s", hidden=True)],
        [inst("t", "readout", "Thermocouple", "T", unit="°C", lc=0.1, digits=1), _SW],
        "Newton's law of cooling: for a small excess of temperature the rate of cooling is proportional to the excess, "
        "dT/dt = −k (T − Ts). So T − Ts = (T0 − Ts) exp(−k t), and a graph of ln(T − Ts) against t is a straight line of "
        "slope −k. A thermocouple in the block feeds an amplifier and a data logger, which samples the temperature "
        "every 30 s with no reading error from a moving mercury thread.",
        ["Note the room temperature Ts with the thermocouple before heating.",
         "Heat the block in the hot bath to about 90 °C, set it on the insulating stand and start the logger.",
         "Let the logger record the temperature every 30 s for 10 minutes.",
         "Plot ln(T − Ts) against t.", "The slope of the line is −k."],
        [_q("A graph of ln(T − Ts) against t is", ["a straight line of slope −k", "a parabola", "a horizontal line"],
            "T − Ts falls exponentially with time."),
         _q("Why is a thermocouple with a logger better here than a mercury thermometer?", ["It responds quickly and records by itself", "It is heavier", "It needs no calibration"],
            "Its small junction follows the block closely and the readings are taken at exact intervals.")],
        [HNB, GENERIC, SIM],
        {"params": {"k": 0.003, "T0": 90.0, "Ts": 28.0}, "reading": "T60", "textbook": "cooling_T60"},
        safety="The block is hot enough to burn: move it with tongs and leave it on the insulating stand.")


# =============================================================================================== HARMONICS
def harmonics() -> dict:
    return lab(
        id="w7-harmonics-cro", rig="w7-harmonics-bench", title="Harmonics and their amplitudes in a complex wave on a CRO",
        group="Physics · Waves", level=LEVEL, topic=CH_OSC, chapter=CH_OSC,
        aim="Pass a square, triangular or clipped sine wave through a narrow tunable filter, read each harmonic on the "
            "CRO and compare the relative amplitudes with Fourier's theorem.",
        kernel="w7_fourier", params={"shape": 0.0, "A": 2.0, "f0": 1000.0, "clip": 0.5, "n": 3.0}, autorun=False,
        camera={"pos": [0.3, 0.5, 1.1], "look": [0, 0.1, -0.2]}, floor=-0.03,
        bodies=[board(1.2, 0.6),
                B("gen", "box", name="Function generator", info="Gives the complex wave at 1 kHz.", size=[0.25, 0.1, 0.2], pos=[-0.35, 0.05, -0.2], color="#2b2f36"),
                B("cro", "box", name="CRO", info="Shows the harmonic the filter passes.", size=[0.3, 0.2, 0.25], pos=[0.35, 0.1, -0.2], color="#d8d4c8")],
        knobs=[knob("n", "Filter tuned to harmonic", "n", 1, 9, 1, 3, "")],
        instruments=[inst("an", "readout", "Harmonic amplitude", "an", unit="V", digits=3)],
        steps=["Set the generator to 1 kHz and look at the wave itself on the CRO.",
               "Tune the filter to the fundamental (1 kHz) and read the peak-to-peak height of the sine wave it passes.",
               "Tune to 2, 3, 4 ... 9 kHz in turn and read each harmonic.",
               "Divide each amplitude by that of the fundamental.", "Compare with 1/n (square), 1/n² (triangle) or the Fourier integral."],
        theory="Fourier's theorem: any periodic wave is a sum of sine waves at the fundamental frequency and its "
               "whole-number multiples, the harmonics. A square wave has only odd harmonics, with amplitudes "
               "4A/(nπ), falling as 1/n. A triangular wave has only odd harmonics falling as 1/n², 8A/(n²π²). A sine "
               "wave clipped flat at part of its height gains odd harmonics that grow as the clipping deepens. A narrow "
               "band-pass filter tuned to n times the fundamental lets through only the n-th harmonic.",
        safety="Signal-level voltages only. Do not short the generator output, and keep the CRO earthed.",
        tour=[{"say": "A function generator, a tunable filter and a CRO. The filter picks out one harmonic at a time."}],
        questions=[_q("A symmetrical square wave contains", ["only odd harmonics", "only even harmonics", "all harmonics equally"],
                      "Its two half cycles are mirror images, which removes every even harmonic."),
                   _q("The third harmonic of a triangular wave is what fraction of its fundamental?", ["1/9", "1/3", "1/27"],
                      "The harmonics of a triangle fall as 1/n².")],
        sources=[{"title": "Gurugram University NEP physics practical list: Elements of Modern Physics lab, harmonics of a complex wave"},
                 {"title": "Fourier series of square, triangular and clipped sine waves: standard results (e.g. Arfken and Weber, Mathematical Methods for Physicists)"}, SIM],
        check={"params": {"shape": 0.0, "n": 3.0}, "reading": "ratio", "textbook": "w7_fourier_ratio"})


def capillary_temperature() -> dict:
    return lab(
        id="w7-capillary-temperature", rig="capillary-rise", title="Surface tension of water by capillary rise",
        group=G_PM, level=LEVEL, topic=CH_PM, chapter=CH_PM,
        aim="Measure the rise of water in fine capillary tubes with a travelling microscope and find its surface "
            "tension, at room temperature and at several other temperatures.",
        kernel="capillary", params={"T": 0.07275, "rho": 998.2, "r": 0.00025, "theta": 0.0}, autorun=False,
        camera={"pos": [0.12, 0.2, 0.42], "look": [-0.02, 0.08, -0.02]}, floor=-0.02,
        bodies=[board(0.5, 0.3),
                B("trough", "cylinder", name="Glass trough", info="Holds the water the capillary tube dips into.", r=0.055, h=0.04, open=True, pos=[0, 0.02, 0], color="glass", opacity=0.3),
                B("tube", "cylinder", name="Capillary tube", info="A fine glass tube of known bore.", r=0.003, h=0.16, pos=[0, 0.09, 0], color="glass", opacity=0.5)],
        knobs=[knob("tube", "Capillary tube (bore radius r)", "r", 0.15, 0.6, 0.05, 0.25, "mm", 0.001),
               knob("T", "Water (surface tension hidden)", "T", 0.02, 0.085, 0.00001, 0.07275, "N/m", hidden=True)],
        instruments=[inst("h", "readout", "Rise of the liquid h", "h_cm", unit="cm", lc=0.001, digits=3)],
        steps=["Clean the capillary tubes and hold one upright with its lower end in the water.",
               "Bring the pointer tip just to the water surface.",
               "Focus the travelling microscope on the bottom of the meniscus and read the scale.",
               "Lower the microscope to the pointer tip and read again: the difference is h.",
               "T = r ρ g (h + r/3) / 2. Repeat for other bores and for water at other temperatures."],
        theory="Water wets clean glass, so its surface in a narrow tube is curved and the pressure just under the "
               "meniscus is lower than atmospheric by 2T/r. The water rises until the weight of the column balances "
               "this: h = 2 T cos θ / (r ρ g), with θ nearly zero for clean glass. So T = r ρ g h / 2 (adding r/3 to h "
               "for the liquid in the meniscus). Surface tension falls steadily as the water is warmed.",
        safety="Capillary tubes break easily: hold them near the middle. Wipe up spilt water at once. Take care with hot water.",
        tour=[{"say": "A capillary tube dips into a trough of water; a travelling microscope reads the height of the meniscus."}],
        questions=[_q("In a narrower tube the water rises", ["higher", "less", "to the same height"], "h is inversely proportional to the bore radius."),
                   _q("When water is warmed its surface tension", ["falls", "rises", "does not change"], "The molecules are held less strongly as the temperature rises.")],
        sources=[IP, {"title": "Surface tension and density of water against temperature: CRC Handbook of Chemistry and Physics (IAPWS values)",
                      "note": "from memory - verify"}, SIM],
        check={"params": {"r": 0.00025}, "reading": "h", "textbook": "cap_h"})


BUILDERS = BUILDERS + (stefan, callendar_barnes, angstrom, cooling_method, cooling_daq, harmonics, capillary_temperature)


# =============================================================================================== OPTICAL LEVER
def optical_lever() -> dict:
    return lab(
        id="w7-youngs-optical-lever", rig="w7-optical-lever", title="Young's modulus of a wire by the optical lever method",
        group=G_PM, level=LEVEL, topic=CH_PM, chapter=CH_PM,
        aim="Load a long wire, magnify its tiny extension with an optical lever, a telescope and a scale, and find "
            "Young's modulus of the material of the wire.",
        kernel="searle", params={"Y": 2.0e11, "L": 1.0, "d": 0.000559, "m": 0.0}, autorun=False,
        camera={"pos": [0.3, 0.8, 1.6], "look": [0.2, 0.5, -0.4]}, floor=-0.03,
        bodies=[board(1.8, 0.7),
                B("wire", "cylinder", name="Experimental wire", info="A long thin wire clamped at the top and loaded at the bottom.", r=0.002, h=1.0, pos=[0.7, 0.7, -0.3], color="steel"),
                B("tel", "cylinder", name="Telescope and scale", info="Reads the scale reflected in the lever's mirror.", r=0.015, h=0.2, pos=[-0.3, 0.5, -0.3], rot=[0, 0, 1.5708], color="brass")],
        knobs=[knob("Y", "Wire material (Y hidden)", "Y", 50, 250, 0.1, 200, "GPa", 1e9, hidden=True),
               knob("m", "Load on the hanger", "m", 0, 3, 0.5, 0, "kg")],
        instruments=[inst("e", "readout", "Extension of the wire", "e_mm", unit="mm", digits=3)],
        steps=["Measure the length of the wire and, with a screw gauge, its diameter at several places.",
               "Rest the front leg of the optical lever on the wire's chuck and its hind legs on the fixed platform.",
               "Focus the telescope on the image of the scale in the mirror and note the reading with no load.",
               "Add 0.5 kg at a time up to 3 kg, reading the scale each time; then unload and read again.",
               "Extension e = s z / (2 D); Y = M g L / (π r² e)."],
        theory="A load M g stretches a wire of length L and radius r by e, and Young's modulus is "
               "Y = (M g / π r²) / (e / L). The extension is only a fraction of a millimetre. An optical lever rests one "
               "leg on the moving end and two on a fixed platform, a distance z behind: when the wire stretches by e the "
               "lever and its mirror tilt by e / z, and the image of a scale a distance D away, seen in the telescope, "
               "moves through s = 2 D e / z. So e = s z / (2 D), magnified about fifty times.",
        safety="Keep your feet clear of the hanging load. Do not exceed the stated load: the wire must stay within its elastic limit.",
        tour=[{"say": "A long wire carries a hanger. An optical lever on its lower clamp tilts a small mirror, read by a telescope and scale one metre away."}],
        questions=[_q("Why does the reflected ray turn through twice the angle of the mirror?", ["Both the angle of incidence and of reflection change", "The mirror is curved", "The scale is far away"],
                      "When a mirror turns through θ, the reflected ray turns through 2θ."),
                   _q("Making the scale distance D larger", ["increases the magnification", "stretches the wire more", "changes Y"],
                      "The scale shift is s = 2 D e / z, proportional to D.")],
        sources=[DU, IP, {"title": "CRC Handbook of Chemistry and Physics, elastic constants of metals (Young's modulus of steel about 200 GPa); BS 3737 standard wire gauge: SWG 24 = 0.559 mm", "note": "from memory - verify"}, SIM],
        check={"params": {"Y": 2.0e11, "L": 1.0, "d": 0.000559, "m": 2.0}, "reading": "e", "textbook": "searle_e"})


BUILDERS = BUILDERS + (optical_lever,)


# =============================================================================================== TROLLEY ON AN INCLINE
def trolley_incline() -> dict:
    return lab(
        id="w7-incline-trolley", rig="w7-trolley-incline", title="Sliding and rolling friction of a trolley on an inclined plane",
        group="Physics · Mechanics", level=LEVEL, topic=CH_MECH, chapter=CH_MECH,
        aim="Release a trolley from rest on an inclined plane, time it between two photo-gates at several angles, and "
            "find the coefficient of sliding friction (wheels locked) and of rolling friction (wheels free).",
        kernel="w7_trolley", params={"angle": 0.4363, "mus": 0.30, "mur": 0.012, "lock": 1.0, "g": 9.8, "d": 1.0},
        autorun=False, camera={"pos": [0.3, 0.7, 1.6], "look": [0.1, 0.2, -0.2]}, floor=-0.03,
        bodies=[board(1.6, 0.6),
                B("plank", "box", name="Inclined plane", info="A long plank hinged at its lower end; its upper end rests on a lab jack.", size=[1.3, 0.02, 0.18], pos=[0, 0.2, -0.2], rot=[0, 0, 0.3], color="wood"),
                B("trolley", "box", name="Trolley", info="A four-wheeled trolley whose wheels can be locked by a lever.", size=[0.12, 0.05, 0.08], pos=[0.3, 0.4, -0.2], rot=[0, 0, 0.3], color="steel")],
        knobs=[knob("mus", "Sliding friction (hidden)", "mus", 0.1, 0.6, 0.005, 0.30, "", hidden=True),
               knob("mur", "Rolling friction (hidden)", "mur", 0.002, 0.05, 0.0005, 0.012, "", hidden=True),
               knob("deg", "Angle of the plane", "angle", 1, 40, 0.5, 25, "°", DEG)],
        instruments=[inst("s", "readout", "Distance moved", "s", k=100, unit="cm", digits=1), _SW],
        steps=["Measure the length of the plane between the hinge and the support, and the gate distance d.",
               "Lock the wheels. Raise the upper end until the trolley slides; read the height h with the vernier height gauge.",
               "Release the trolley at the first gate and read the time t to the second gate. Repeat at four more heights.",
               "Free the wheels and repeat at small angles.",
               "For each run μ = tan θ − 2d / (g t² cos θ). Take the mean for each state of the wheels."],
        theory="On a plane at angle θ a trolley released from rest accelerates at a = g (sin θ − μ cos θ), where μ is the "
               "coefficient of friction acting while it moves. With its wheels locked the trolley slides and μ is the "
               "coefficient of sliding (kinetic) friction. With its wheels free they roll and the much smaller μ is the "
               "coefficient of rolling friction (rolling resistance, including the axle friction). Timing it over a "
               "distance d from rest gives a = 2d / t², so μ = tan θ − 2d / (g t² cos θ). The angle comes from the height "
               "h of the support: sin θ = h / l.",
        safety="Catch the trolley at the bottom: do not let it fall off the plane. Keep fingers clear of the hinge and the jack.",
        tour=[{"say": "A trolley sits at the top of an inclined plane between two photo-gates; a timer reads the time between them."}],
        questions=[_q("Rolling friction is much smaller than sliding friction because", ["the wheel surface does not rub along the plane", "the trolley is lighter", "the plane is steeper"],
                      "A rolling wheel only deforms and recovers at its contact; it does not slide over the surface."),
                   _q("If the trolley moves down at constant speed, then", ["μ = tan θ", "μ = sin θ", "μ = 0"],
                      "With a = 0, g sin θ = μ g cos θ.")],
        sources=[DU, {"title": "Generic trolley and plank", "note": "the sliding and rolling coefficients are settings of this bench (a typical locked trolley on wood, a typical lab trolley rolling), not values of a named material"},
                 {"title": "g = 9.8 m/s²", "note": "standard rounded value for the lab"}, SIM],
        check={"params": {"angle": 0.4363, "lock": 1.0, "mus": 0.30}, "reading": "mu", "textbook": "w7_trolley_mu"})


BUILDERS = BUILDERS + (trolley_incline,)


# =============================================================================================== 2-D COLLISIONS (VIRTUAL)
def collision_2d() -> dict:
    return lab(
        id="w7-collision-2d", rig="w7-air-table", title="Two-dimensional elastic and inelastic collisions (virtual air table)",
        group="Physics · Mechanics", level=LEVEL, topic=CH_MECH, chapter=CH_MECH,
        aim="Virtual lab (SIMULATED DATA): launch one puck at another resting on a frictionless air table, read both "
            "tracks from a strobe photograph and test the conservation of momentum (both components) and of kinetic "
            "energy, for an elastic and an inelastic collision.",
        kernel="w7_coll2d", params={"m1": 0.2, "m2": 0.3, "u": 0.5, "b": 0.03, "R": 0.04, "e": 1.0, "x0": -0.4},
        autorun=False, camera={"pos": [0, 1.0, 0.9], "look": [0, 0.1, -0.2]}, floor=-0.03,
        bodies=[board(1.2, 0.8),
                B("table", "box", name="Air table", info="A flat table on a cushion of air: the pucks glide without friction.", size=[1.0, 0.03, 0.7], pos=[0, 0.1, -0.2], color="glass"),
                B("puckA", "cylinder", name="Puck A", info="The launched puck.", r=0.04, h=0.02, pos=[-0.4, 0.13, -0.17], color="red"),
                B("puckB", "cylinder", name="Puck B", info="The target puck, at rest.", r=0.04, h=0.02, pos=[0.1, 0.13, -0.2], color="blue")],
        knobs=[knob("b", "Sideways offset of the launch b", "b", 0, 70, 1, 30, "mm", 0.001),
               knob("e", "Bumper rings (restitution, hidden)", "e", 0, 1, 0.01, 1.0, "", hidden=True)],
        instruments=[inst("x1", "readout", "Puck A, x", "x1", k=1000, unit="mm", digits=0), inst("x2", "readout", "Puck B, x", "x2", k=1000, unit="mm", digits=0)],
        steps=["Weigh both pucks. Put puck B at rest at the centre of the table.",
               "Set the launcher a sideways distance b from the line through B's centre and launch puck A.",
               "Take a strobe photograph (a flash every 0.05 s) and read both tracks on the printed grid.",
               "Fit straight lines to the dots to get every velocity component before and after.",
               "Compare the total momentum (x and y) and the kinetic energy before and after. Repeat with other offsets."],
        theory="During the impact the only force between the pucks acts along the line joining their centres. The total "
               "momentum is conserved in both directions: m1 u = m1 v1x + m2 v2x and 0 = m1 v1y + m2 v2y. Along the line "
               "of centres the separation speed is e times the approach speed (e = 1: elastic; e < 1: inelastic). The "
               "fraction of kinetic energy kept is 1 − (1 − e²) m2 / (m1 + m2) cos²φ, where φ is the angle between the "
               "line of centres and the first puck's velocity (sin φ = b / 2R).",
        safety="A virtual lab: there is nothing to injure. On a real air table keep the blower on whenever a puck moves.",
        tour=[{"say": "This is a simulated air table: two pucks, a launcher and a strobe camera above."}],
        questions=[_q("In every collision of the two pucks", ["the total momentum is conserved", "the kinetic energy is always conserved", "only the x-momentum is conserved"],
                      "No outside force acts along the table, so both components of the momentum are kept."),
                   _q("If puck A hits B head on (b = 0) with e = 1 and equal masses, then", ["A stops and B moves on with A's speed", "both stop", "they move off together"],
                      "Equal masses in an elastic head-on collision exchange their velocities.")],
        sources=[DU, {"title": "Oblique impact of smooth spheres (Newton's experimental law along the line of centres)",
                      "note": "standard result, e.g. any text on the mechanics of particles; masses, speed and restitution are settings of this virtual bench"}, SIM],
        check={"params": {"b": 0.03, "e": 1.0}, "reading": "ke", "textbook": "w7_coll2d_ke"})


BUILDERS = BUILDERS + (collision_2d,)
