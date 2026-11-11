"""Prayogshala lab pack: the school set-ups of wave 7 (Class 6-10 activities, Class 11-12 Section A / B work).

Four rigs serve them all (`app/static/prayog/exp/`):
    sw7-motion-bench      ramps, runway, launcher, drop stand, staircase, damped pendulum
    sw7-measure-bench     water bottle with holes, cuboid on sand, upthrust and density, beam balance, callipers,
                          screw gauge, paper scale, lens combination
    sw7-heat-sound-bench  sound in solids, reflection of sound, black and white tins, calorimeter, wax, bimetal,
                          liquid level, rate of loss of heat
    sw7-electric-bench    copper plating, liquid conductivity tester, force on a conductor, multimeter, diode / LED
Physics: the `school_w7` kernel pack (the liquid specific heat rides the shipped `mixtures` kernel). Every lab has
its own check (the kernel's reading against the textbook formula). A constant that was NOT looked up in a table is
labelled "from memory - verify" or "illustrative" in the lab's sources. English only.
"""
from __future__ import annotations

from ..catalog import B, inst, lab

SIM = {"title": "Hoola Prayogshala kernel", "note": "readings come from the simulation code; checked against the textbook formula in Hoola's tests"}
N8 = {"title": "Science, Textbook for Class VIII, NCERT"}
N9 = {"title": "Science, Textbook for Class IX, NCERT"}
N7 = {"title": "Science, Textbook for Class VII, NCERT"}
N10 = {"title": "Science, Textbook for Class X, NCERT"}
L9 = {"title": "Laboratory Manual Science, Class IX, NCERT"}
L11 = {"title": "Laboratory Manual Physics Class XI, NCERT"}
L12 = {"title": "Laboratory Manual Physics Class XII, NCERT"}


def _src(title: str, note: str) -> dict:
    return {"title": title, "note": note}


def _mk(sid, rig, title, level, chapter, aim, kernel, params, var, theory, safety, steps, questions, sources, check):
    return lab(
        id="sw7-" + sid, rig=rig, title=title, group="Physics · " + chapter, level=level, topic=chapter, chapter=chapter,
        aim=aim, kernel=kernel, params=params, autorun=True,
        camera={"pos": [0.3, 0.6, 1.2], "look": [0, 0.05, 0]}, floor=-0.02,
        bodies=[B("board", "box", name="Bench", size=[1.2, 0.02, 0.5], pos=[0, -0.01, 0], color="wood", cut=False),
                B("app", "box", name="Apparatus", info="The realistic apparatus is drawn by the studio rig.",
                  size=[0.2, 0.1, 0.1], pos=[0, 0.05, 0], color="steel")],
        instruments=[inst("rd", "readout", "Reading", var, digits=4)],
        steps=steps, theory=theory, safety=safety,
        questions=[{"q": q, "options": o, "answer": 0, "why": w} for q, o, w in questions],
        sources=sources + [SIM], check=check)


RM, RB, RH, RE = "sw7-motion-bench", "sw7-measure-bench", "sw7-heat-sound-bench", "sw7-electric-bench"
ILL = "illustrative value, not a property of a named material"
MEM = "from memory - verify"


# =================================================================================================== MOTION
def rolling_surfaces():
    return _mk("rolling-surfaces", RM, "How far a ball rolls on different surfaces", "Class VIII", "Friction",
               "Let a ball roll down the same ramp on to a bare table, newspaper, cloth and sand; measure how far it goes on each and find the rolling resistance.",
               "sw7_rollout", {"surf": 2.0}, "d",
               "The ball reaches the foot of the ramp with the same energy every time, m g h. On the flat surface a resisting force c m g slows it, and it stops after a distance d where m g h = c m g d, so c = h / d. A rougher or softer surface has a larger c and stops the ball sooner.",
               "Release the ball from the mark without pushing it, and keep the ramp at the same height for every surface.",
               ["Set the ramp and note the height h of the release mark.", "Lay the surface on the runway and release the ball from the mark.",
                "Measure how far the ball rolls before it stops.", "Repeat for the bare table, newspaper, cloth and sand, and work out c = h / d."],
               [("On which surface does the ball stop soonest?", ["Sand", "Bare table", "Newspaper"], "Sand gives way under the ball, so the resisting force is the largest."),
                ("Why is the ball always released from the same mark?", ["So that it starts with the same energy", "So that it rolls straight", "To save time"], "Only then is the distance a fair comparison of the surfaces.")],
               [N8, _src("Rolling-resistance coefficients of the four surfaces", ILL + "; chosen so the ball stops on the bench")],
               {"params": {}, "reading": "d", "textbook": "sw7_rollout_d"})


def rolling_vs_sliding():
    return _mk("rolling-vs-sliding", RM, "Rolling friction is smaller than sliding friction", "Class VIII", "Friction",
               "Pull a book along the table with a spring balance, first sliding and then on pencils used as rollers, and compare the two forces.",
               "sw7_pull", {"mode": 0.0}, "F",
               "A book pulled at a steady speed needs a force equal to the friction on it. Sliding friction is F = μ W, with W the weight. On rollers the surfaces do not rub; they only press and roll, so the force needed is many times smaller. That is why wheels and ball bearings are used.",
               "Pull the balance level with the table and at a steady speed; read it only while the book is moving.",
               ["Weigh the book with the spring balance.", "Pull it along the table at a steady speed and read the balance.",
                "Put three pencils under the book and pull again.", "Compare the forces and work out μ = F / W for sliding."],
               [("Rolling friction compared with sliding friction is", ["Much smaller", "Much larger", "The same"], "Rolling replaces rubbing, so far less force is needed."),
                ("Which uses this fact?", ["Ball bearings in a fan", "Brake pads", "The grooves of a tyre"], "Bearings replace sliding by rolling.")],
               [N8, _src("Friction coefficients of the book on the table and on pencils", ILL)],
               {"params": {}, "reading": "F", "textbook": "sw7_pull_F"})


def trolley_block():
    return _mk("trolley-block", RM, "A moving trolley pushes a block: kinetic energy", "Class IX", "Work and Energy",
               "Release a trolley from different heights, time it through a light gate, and see how far it pushes a wooden block: faster means much more work done.",
               "sw7_trolley", {}, "KE",
               "A trolley of mass M moving at speed v has kinetic energy ½ M v². Released from a height h on a smooth ramp it gains M g h, so ½ M v² = M g h. It then does work pushing the block against friction; the distance the block moves grows as v², not as v.",
               "Keep hands clear of the runway and catch the trolley after the block has stopped.",
               ["Note the release height h on the ramp.", "Release the trolley; the light gate shows its speed at the foot.",
                "Measure how far the block is pushed.", "Repeat from two more heights and compare ½ M v² with M g h."],
               [("If the speed of the trolley doubles, its kinetic energy becomes", ["Four times", "Twice", "Half"], "Kinetic energy goes as the square of the speed."),
                ("Where does the trolley's kinetic energy go?", ["Into work against friction on the block", "It disappears", "Into the light gate"], "The block is pushed against friction until all the energy is used.")],
               [N9, _src("Friction coefficient of the block on the runway", ILL)],
               {"params": {}, "reading": "KE", "textbook": "sw7_trolley_KE"})


def incline_roller():
    return _mk("incline-roller", RM, "Force along an inclined plane on a roller, against sin θ", "Class XI", "Work, Energy and Power",
               "Hold a roller at rest on an inclined plane with weights in a pan over a pulley; plot the force against sin θ and find the weight of the roller.",
               "sw7_roller", {}, "F",
               "The weight W of the roller has a part W sin θ down the plane. A string over a pulley carries a pan; the roller just stays at rest when the pan and its weights pull with F = W sin θ. A graph of F against sin θ is a straight line through the origin whose slope is W.",
               "Add the weights gently and keep the string parallel to the plane.",
               ["Set the plane to an angle and read it on the protractor.", "Add weights to the pan until the roller just stays at rest.",
                "Record the force F for each angle.", "Plot F against sin θ; the slope is the weight of the roller."],
               [("The force needed to hold the roller grows with the angle as", ["sin θ", "cos θ", "It stays the same"], "Only the part W sin θ of the weight acts down the plane."),
                ("At θ = 90° the force needed would be", ["The whole weight W", "Zero", "Half of W"], "sin 90° = 1.")],
               [L11],
               {"params": {}, "reading": "W", "textbook": "sw7_roller_W"})


def double_incline():
    return _mk("double-incline", RM, "Conservation of energy on a double inclined plane", "Class XI", "Work, Energy and Power",
               "Release a steel ball on one incline and measure the height it reaches on the facing incline; see how nearly the energy is conserved.",
               "sw7_dincline", {}, "h2",
               "A ball released at height h1 turns potential energy into kinetic energy and back again as it climbs the second incline. If no energy were lost it would reach the same height. A little is lost to rolling friction along both tracks, so h2 is slightly less than h1: h2 = h1 (1 − c cot θ1) / (1 + c cot θ2).",
               "Release the ball without a push and stop it after its first climb.",
               ["Read the release height h1 on the scale.", "Release the ball and mark the highest point it reaches on the other incline.",
                "Read that height h2.", "Repeat from two more heights and work out h2 / h1."],
               [("With no friction the ball would rise to", ["The same height h1", "A greater height", "Half the height"], "Mechanical energy would be conserved."),
                ("h2 is a little less than h1 because", ["Some energy is lost to rolling friction", "Gravity is weaker on that side", "The ball loses mass"], "The lost energy warms the ball and the track.")],
               [L11, _src("Rolling-loss coefficient of the ball on the track", ILL)],
               {"params": {}, "reading": "h2", "textbook": "sw7_dincline_h2"})


def projectile():
    return _mk("projectile-range", RM, "Range of a projectile against the angle of projection", "Class XI", "Motion in a Plane",
               "Fire a ball from a spring launcher at several angles, measure the range each time, and find the angle that gives the greatest range.",
               "sw7_proj", {}, "R",
               "A projectile launched at speed v0 and angle θ lands at the same level at a range R = v0² sin 2θ / g. The range is greatest when sin 2θ = 1, at θ = 45°, and two angles that add up to 90° give the same range.",
               "Wear eye protection and never look into the launcher. Fire only when the landing strip is clear.",
               ["Set the launcher to an angle on its protractor.", "Fire the ball and mark where it lands on the carbon paper.",
                "Measure the range on the tape.", "Repeat for 15°, 30°, 45°, 60° and 75° and find the angle of greatest range."],
               [("The range is greatest at", ["45°", "30°", "60°"], "sin 2θ is largest at θ = 45°."),
                ("Which pair of angles gives the same range?", ["30° and 60°", "30° and 45°", "45° and 75°"], "Angles that add up to 90° have the same sin 2θ.")],
               [L11],
               {"params": {}, "reading": "ang_max", "textbook": "sw7_proj_ang"})


def free_fall():
    return _mk("free-fall-paper", RM, "A stone and a sheet of paper falling from the same height", "Class IX", "Gravitation and Floatation",
               "Drop a stone, a flat sheet of paper and the same sheet crumpled into a ball from one height; time each and find g from the stone.",
               "sw7_fall", {"body": 0.0, "h": 1.0}, "tf",
               "Every body falls with the same acceleration g when air does not matter: h = ½ g t². Air resistance grows with the area facing the air. A flat sheet has a large area for its small weight and soon reaches a low terminal speed; crumpled into a ball the same paper falls almost as fast as the stone.",
               "Drop the bodies; do not throw them. Keep feet clear of the landing pad.",
               ["Measure the height of the release clamp above the pad.", "Drop the stone and read the timer.",
                "Drop the flat sheet, then the crumpled ball, from the same height.", "Work out g = 2h / t² from the stone and compare the three times."],
               [("The crumpled paper falls faster than the flat sheet because", ["Air resists it less", "It is heavier", "Gravity pulls it more"], "The mass is the same; only the area facing the air has changed."),
                ("In a vacuum the sheet and the stone would", ["Land together", "The stone first", "The sheet first"], "With no air every body has the same acceleration g.")],
               [N9, _src("A4 sheet of 80 g/m² paper: 210 mm × 297 mm, 4.99 g", "ISO 216 size and the paper's printed grammage"),
                _src("Drag coefficients: flat plate facing the flow 1.28, sphere 0.47; air 1.2 kg/m³", MEM)],
               {"params": {"body": 0.0}, "reading": "tf", "textbook": "sw7_fall_t"})


def ball_sand():
    return _mk("ball-in-sand", RM, "A heavy ball dropped into wet sand: potential energy", "Class IX", "Work and Energy",
               "Drop a ball into a tray of wet sand from different heights, and then a heavier ball; measure the depth of the dent each time.",
               "sw7_crater", {}, "d",
               "A ball of mass m held at height h has potential energy m g h. When it lands, the sand stops it by doing work against it: F d = m g (h + d), where d is the depth of the dent and F the resisting force of the sand. A greater height or a heavier ball means more energy and a deeper dent.",
               "Drop the ball from rest and keep fingers out of the tray.",
               ["Level the wet sand in the tray.", "Hold the ball at the height marked on the stand and let go.",
                "Measure the depth of the dent with the depth gauge.", "Repeat from other heights and with the heavier ball."],
               [("Dropped from twice the height, the ball has", ["Twice the potential energy", "The same potential energy", "Four times the potential energy"], "Potential energy m g h is proportional to the height."),
                ("A heavier ball from the same height makes", ["A deeper dent", "A shallower dent", "The same dent"], "It carries more energy.")],
               [N9, _src("Resisting force of the wet sand (taken as constant)", ILL)],
               {"params": {}, "reading": "F_meas", "textbook": "sw7_crater_F"})


def stairs_power():
    return _mk("stairs-power", RM, "Power of a person running up a staircase", "Class IX", "Work and Energy",
               "Weigh the runner, measure the height of the staircase, time the climb and work out the power. The runner here is SIMULATED.",
               "sw7_stairs", {}, "tclimb",
               "Climbing a staircase of height H, a person of mass m does work m g H against gravity. Power is the rate of doing work: P = m g H / t. SIMULATED DATA: the figure on the model staircase climbs with a fixed, hidden power; in a real class each student times a real climb.",
               "On a real staircase hold the rail, run one at a time and do not skip steps.",
               ["Read the runner's mass on the weighing machine.", "Measure the height of one step and count the steps.",
                "Time the climb with the stopwatch.", "Work out the work done, m g H, and the power, m g H / t."],
               [("Climbing the same stairs in half the time needs", ["Twice the power", "Half the power", "The same power"], "Power is work divided by time."),
                ("The unit of power is the", ["Watt", "Joule", "Newton"], "1 W = 1 J/s.")],
               [N9, _src("Runner's mass, step height and power", ILL + "; a simulated runner")],
               {"params": {}, "reading": "P_meas", "textbook": "sw7_stairs_P"})


def pendulum_decay():
    return _mk("pendulum-dissipation", RM, "Dissipation of energy of a simple pendulum", "Class XI", "Oscillations",
               "Let a pendulum swing freely and read its amplitude after every ten swings; plot amplitude against time and find the decay constant.",
               "sw7_pend_decay", {}, "theta",
               "Air resistance takes a little energy from the pendulum on every swing, so its amplitude falls. For light damping the amplitude decays exponentially, A = A0 e^(−γt), so ln A against t is a straight line of slope −γ. The energy, which goes as A², decays twice as fast.",
               "Release the bob without a push and let it swing in one plane.",
               ["Pull the bob to 15° on the protractor and release it.", "Read the amplitude after every ten swings, with the time.",
                "Plot the amplitude against time.", "Work out γ = ln(A0 / A) / t."],
               [("The amplitude of a real pendulum falls because", ["Air resistance takes away energy", "Gravity gets weaker", "The string grows longer"], "Work done against the air is not returned."),
                ("If the amplitude halves, the energy becomes", ["One quarter", "One half", "Unchanged"], "Energy goes as the square of the amplitude.")],
               [L11, _src("Damping constant of the bob in air", ILL)],
               {"params": {}, "reading": "gamma", "textbook": "sw7_pend_gamma"})


# =================================================================================================== MEASURING
def pressure_holes():
    return _mk("liquid-pressure-holes", RB, "Liquid pressure: water from holes in a bottle", "Class VIII", "Pressure",
               "Open holes at three heights in a tall bottle of water, and then holes all round at one height; measure how far each jet lands and find its speed.",
               "sw7_jet", {"hole": 0.0}, "x",
               "The pressure in a liquid grows with depth: P = ρ g d. Water leaves a hole at depth d with speed v = √(2 g d), so a deeper hole gives a faster jet. Holes at the same depth give equal jets in every direction, because the pressure at one depth is the same on all sides.",
               "Keep the tray under the jets and mop up spills at once.",
               ["Fill the bottle to the mark and note the water level.", "Open one hole and measure where the jet lands in the tray.",
                "Repeat for the holes at the other two heights.", "Open the ring of holes at one height and compare the jets."],
               [("The fastest jet comes from the hole that is", ["Deepest below the surface", "Nearest the surface", "In the middle"], "Pressure, and so the speed, grows with depth."),
                ("Holes at the same depth all round the bottle give jets that are", ["Equal", "Stronger at the front", "Stronger at the back"], "At one depth a liquid presses equally in all directions.")],
               [N8, _src("Density of water 998 kg/m³ at 20 °C", "CRC Handbook of Chemistry and Physics")],
               {"params": {}, "reading": "v_meas", "textbook": "sw7_jet_v"})


def cuboid_sand():
    return _mk("pressure-cuboid-sand", RB, "Pressure of an iron cuboid on sand on its three faces", "Class IX", "Pressure",
               "Rest an iron cuboid on sand on its largest, middle and smallest faces; weigh it, measure each face and work out the pressure.",
               "sw7_cuboid", {"face": 2.0}, "P",
               "Pressure is the force on unit area: P = W / A. The weight of the cuboid is the same whichever way it rests, but the area under it changes, so the smallest face presses hardest and sinks deepest into the sand.",
               "Lower the cuboid gently; do not drop it. Level the sand before each trial.",
               ["Weigh the cuboid with the spring balance.", "Measure the two sides of the face it will rest on.",
                "Place it on the levelled sand and measure the depth of the dent.", "Repeat for the other two faces and work out P = W / A."],
               [("The cuboid sinks deepest when it rests on its", ["Smallest face", "Largest face", "Middle face"], "The same weight on a smaller area gives a larger pressure."),
                ("The SI unit of pressure is the", ["Pascal", "Newton", "Joule"], "1 Pa = 1 N/m².")],
               [L9, _src("Density of iron 7874 kg/m³", "CRC Handbook of Chemistry and Physics"),
                _src("Depth of the dent per unit pressure in sand", ILL)],
               {"params": {}, "reading": "P", "textbook": "sw7_cuboid_P"})


def bottle_upthrust():
    return _mk("bottle-upthrust", RB, "Upthrust on an empty bottle pushed into water", "Class IX", "Gravitation and Floatation",
               "Push a sealed empty bottle into water with a force gauge, a quarter at a time, and compare the upthrust with the weight of water displaced.",
               "sw7_upthrust", {}, "F",
               "Water pushes up on anything put into it. The upthrust equals the weight of the water displaced (Archimedes' principle): U = ρ g V. To hold the bottle under, the push F and the bottle's small weight together must balance the upthrust, so U = F + W.",
               "Push straight down and slowly so that water does not splash over.",
               ["Weigh the empty bottle.", "Push it a quarter under with the force gauge and read the push.",
                "Read the volume of water that has run out of the overflow can.", "Repeat for half, three quarters and the whole bottle."],
               [("The upthrust on a body equals", ["The weight of liquid it displaces", "Its own weight", "Its volume"], "This is Archimedes' principle."),
                ("Pushing more of the bottle under water makes the upthrust", ["Larger", "Smaller", "Unchanged"], "More water is displaced.")],
               [N9, _src("Density of water 998 kg/m³ at 20 °C", "CRC Handbook of Chemistry and Physics")],
               {"params": {}, "reading": "U_meas", "textbook": "sw7_upthrust_U"})


def cork_nail():
    return _mk("cork-nail", RB, "Why a cork floats and an iron nail sinks", "Class IX", "Gravitation and Floatation",
               "Find the mass and the volume of a cork and of iron nails, work out each density and compare it with the density of water.",
               "sw7_density", {"body": 0.0}, "rho_meas",
               "A body floats in a liquid if its density is less than the liquid's and sinks if it is more. Density = mass / volume. Cork is far less dense than water, so only a part of it needs to be under water to displace its own weight; iron is nearly eight times denser than water and sinks.",
               "Lower the nails into the cylinder on a thread so that the glass does not crack.",
               ["Find the mass of the cork on the balance.", "Push it just under water in the measuring cylinder with a pin and read the rise.",
                "Do the same with the iron nails.", "Work out each density and compare with water."],
               [("A body floats on water when its density is", ["Less than that of water", "More than that of water", "Exactly 1 g"], "Then it displaces its own weight before it is fully under."),
                ("An iron ship floats because", ["Its average density, with the air inside, is less than water", "Iron is lighter at sea", "Salt holds it up"], "The hull encloses a large volume of air.")],
               [N9, _src("Density of iron 7874 kg/m³, water 998 kg/m³", "CRC Handbook of Chemistry and Physics"),
                _src("Density of cork 240 kg/m³", MEM)],
               {"params": {"body": 0.0}, "reading": "rho_meas", "textbook": "sw7_density_rho"})


def beam_balance():
    return _mk("beam-balance", RB, "Beam balance: mass of two different bodies", "Class XI", "Laws of Motion",
               "Weigh two bodies on a physical balance by trying the weights from the box, largest first, until the pointer rests at the centre.",
               "sw7_balance", {"body": 0.0}, "div",
               "A beam balance compares the unknown mass in one pan with standard weights in the other. With equal arms the beam is level when the two masses are equal, wherever the balance is used. Weights are tried from the largest down: one that makes its pan sink is taken off, one that does not is kept.",
               "Arrest the beam before adding or removing a weight, and handle the weights with forceps only.",
               ["Level the balance and check that the pointer rests at zero.", "Put the body in the left pan.",
                "Try the weights in the right pan, largest first.", "Add up the weights that stayed; repeat for the second body."],
               [("A beam balance measures", ["Mass", "Weight", "Volume"], "It compares the body with standard masses, so g cancels out."),
                ("Weights are handled with forceps because", ["Fingers leave grease that changes their mass", "They are hot", "They are magnetic"], "Even a film of grease is a few milligrams.")],
               [L11, _src("The two bodies", "unknown bodies; their masses are the hidden unknowns")],
               {"params": {"body": 0.0}, "reading": "m_read", "textbook": "sw7_balance_m"})


def vernier_vessel():
    return _mk("vernier-inside-depth", RB, "Vernier callipers: internal diameter, depth and volume", "Class XI", "Units and Measurements",
               "Use the inside jaws and the depth strip of vernier callipers to measure a beaker and a calorimeter, and work out each internal volume.",
               "sw7_vessel", {"vessel": 0.0}, "D",
               "The upper jaws of the callipers measure an inside diameter and the strip at the end measures a depth, each to the least count of 0.01 cm. For a cylindrical vessel the internal volume is V = π D² h / 4.",
               "Do not force the jaws against the glass; hold the callipers square to the rim.",
               ["Find the least count and check the zero error.", "Open the inside jaws across the mouth and read the diameter.",
                "Stand the end of the main scale on the rim and run the depth strip to the bottom.", "Work out V = π D² h / 4; repeat for the calorimeter."],
               [("Which part measures the depth of a vessel?", ["The strip at the end of the main scale", "The lower jaws", "The upper jaws"], "The strip slides out as the vernier moves."),
                ("With 10 vernier divisions equal to 9 mm, the least count is", ["0.1 mm", "1 mm", "0.01 mm"], "1 mm − 0.9 mm = 0.1 mm.")],
               [L11, _src("The beaker and the calorimeter", "unknown vessels; their sizes are the hidden unknowns")],
               {"params": {}, "reading": "V", "textbook": "sw7_vessel_V"})


def screw_sheet():
    return _mk("screw-gauge-sheet", RB, "Screw gauge: thickness of a sheet, volume of a lamina", "Class XI", "Units and Measurements",
               "Measure the thickness of a metal sheet and of an irregular lamina with a screw gauge, find the lamina's area on graph paper and work out its volume.",
               "sw7_sheet", {"body": 1.0}, "th",
               "A screw gauge reads to 0.01 mm: reading = main scale + circular scale × least count. An irregular lamina has no formula for its area, so its outline is traced on graph paper and the squares inside are counted. Volume = area × thickness.",
               "Turn the ratchet, not the thimble, so that every reading is taken at the same pressure.",
               ["Find the least count and the zero error of the screw gauge.", "Measure the thickness of the metal sheet.",
                "Measure the thickness of the lamina and trace it on graph paper.", "Count the squares for the area and work out the volume."],
               [("The ratchet of a screw gauge is used to", ["Apply the same light pressure every time", "Lock the screw", "Read the zero error"], "It slips once the faces touch."),
                ("The area of an irregular lamina is found by", ["Counting squares on graph paper", "Length × breadth", "Weighing it"], "There is no formula for an irregular outline.")],
               [L11, _src("The sheet and the lamina", "unknown samples; thickness and area are the hidden unknowns")],
               {"params": {}, "reading": "V", "textbook": "sw7_sheet_V"})


def paper_scale():
    return _mk("paper-scale", RB, "Make a paper scale of a given least count", "Class XI", "Units and Measurements",
               "Mark a paper strip in steps of 0.5 cm and another in steps of 0.2 cm, measure the same pencil with both and see what the least count does.",
               "sw7_pscale", {"lc": 0.002}, "reading",
               "The least count of a scale is its smallest division. A length is read to the nearest division, so a scale with a least count of 0.2 cm can be wrong by up to 0.1 cm and one of 0.5 cm by up to 0.25 cm. A finer scale gives a reading closer to the true length.",
               "Keep the eye straight above the mark being read to avoid parallax.",
               ["Rule a paper strip and mark it every 0.5 cm.", "Lay the pencil along it from zero and read its length.",
                "Make a second strip marked every 0.2 cm and read again.", "Compare the two readings."],
               [("The least count of a scale is", ["Its smallest division", "Its total length", "Its first mark"], "It is the smallest length the scale can read directly."),
                ("A reading on a scale of least count 0.2 cm can be wrong by up to", ["0.1 cm", "0.2 cm", "1 cm"], "The length is read to the nearest division.")],
               [L11, _src("The pencil", "an unknown length; it is the hidden unknown")],
               {"params": {}, "reading": "reading", "textbook": "sw7_pscale_L", "tol": 0.02})


def lens_combination():
    return _mk("lens-combination", RB, "A lens combination of a specified focal length", "Class XII", "Ray Optics and Optical Instruments",
               "From a set of convex lenses choose two that together give a focal length of 12 cm, then check the combination on an optical bench.",
               "sw7_lenscomb", {}, "v",
               "Two thin lenses in contact act as one lens whose power is the sum of the two powers: 1/F = 1/f1 + 1/f2. The focal length of the pair is checked by forming a sharp image of a lit object on a screen: F = u v / (u + v).",
               "Hold the lenses by the rim and keep them in contact in one holder.",
               ["Work out which two lenses of the set give the focal length asked for.", "Mount the two in contact in the lens holder.",
                "Place the object, move the screen until the image is sharp and read u and v.", "Work out F = u v / (u + v) for three object distances."],
               [("Two convex lenses of 20 cm and 30 cm in contact have a focal length of", ["12 cm", "50 cm", "25 cm"], "1/F = 1/20 + 1/30 = 1/12."),
                ("The power of a combination of thin lenses in contact is the", ["Sum of the powers", "Product of the powers", "Difference of the powers"], "P = P1 + P2.")],
               [L12, _src("The lens set", "marked focal lengths 10, 15, 20, 30 and 50 cm")],
               {"params": {}, "reading": "F_meas", "textbook": "sw7_lens_F"})


# =================================================================================================== HEAT AND SOUND
def sound_solids():
    return _mk("sound-through-solids", RH, "Sound travels through solids", "Class VIII", "Sound",
               "Tap one end of a wooden metre scale and of a string telephone; time the sound between two contact microphones and compare its speed with air.",
               "sw7_solidsound", {"medium": 0.0, "d1": 2.0}, "dt",
               "Sound needs a medium, and it travels faster in solids than in air because the particles of a solid are bound closely and stiffly. In a rod or a stretched string the speed is v = √(Y / ρ), with Y the Young's modulus and ρ the density. That is why a tap is heard clearly with the ear on the table, and why a string telephone works.",
               "Tap lightly; do not shout into a string telephone held at someone's ear.",
               ["Fix the two contact microphones a measured distance apart.", "Tap the end and read the time between the two signals.",
                "Work out the speed, distance / time.", "Repeat for the string telephone and for air."],
               [("Sound travels fastest in", ["Solids", "Liquids", "Gases"], "The particles of a solid pass the disturbance on most quickly."),
                ("A string telephone works only when the string is", ["Stretched tight", "Slack", "Wet"], "A slack string cannot pass the vibration along.")],
               [N8, _src("Wood along the grain: Young's modulus 11 GPa, density 650 kg/m³; nylon line: 3.0 GPa, 1150 kg/m³", MEM),
                _src("Speed of sound in air 331.3 √(1 + t / 273.15) m/s", "standard formula")],
               {"params": {}, "reading": "v_meas", "textbook": "sw7_sound_v"})


def sound_reflection():
    return _mk("reflection-of-sound", RH, "Laws of reflection of sound with two tubes", "Class IX", "Sound",
               "Send the ticking of a clock down one tube towards a wall and turn a second tube until the sound is loudest; compare the two angles.",
               "sw7_echo", {}, "loud",
               "Sound is reflected like light: the angle of reflection equals the angle of incidence, and the incident sound, the reflected sound and the normal lie in one plane. The listening tube hears the loudest sound when it points along the reflected direction.",
               "Keep the room quiet and the tubes level on the board.",
               ["Set the first tube at an angle to the normal and note it.", "Turn the listening tube slowly and watch the sound-level meter.",
                "Read the angle at which the sound is loudest.", "Repeat for two more angles of incidence."],
               [("The loudest sound is heard when the angle of reflection is", ["Equal to the angle of incidence", "Twice the angle of incidence", "Zero"], "This is the law of reflection."),
                ("A screen is kept between the two tubes so that", ["Sound does not reach the ear directly", "The tubes stay cool", "The wall stays clean"], "Only the reflected sound should be heard.")],
               [L9, _src("Width of the reflected beam", ILL + "; the position of the peak is the law being tested")],
               {"params": {}, "reading": "r_peak", "textbook": "sw7_echo_r"})


def black_white_tins():
    return _mk("black-white-tins", RH, "Absorption of heat by black and white tins in sunlight", "Class VII", "Heat",
               "Stand a black tin and a white tin of water in the sun, read the thermometers after the same time and compare how much heat each absorbed.",
               "sw7_tins", {"tin": 0.0}, "T",
               "Heat from the sun arrives by radiation. A dull black surface absorbs most of the radiation that falls on it; a white surface reflects most of it. With the same water in both tins, the rise in temperature after the same time is in the ratio of the fractions absorbed.",
               "Do not look at the sun; handle the warm tins by the rim.",
               ["Pour equal amounts of water into the two tins and note the temperature.", "Stand both in the sun (the lamp) side by side.",
                "Read both thermometers after 20 minutes and after 40 minutes.", "Compare the two rises in temperature."],
               [("Which tin warms more in the sun?", ["The black tin", "The white tin", "Both the same"], "Black absorbs most of the radiation; white reflects most of it."),
                ("Light-coloured clothes are preferred in summer because they", ["Reflect most of the sun's heat", "Absorb more heat", "Are thinner"], "They absorb less radiation.")],
               [N7, _src("Solar absorptance: flat black paint 0.95, white paint 0.25", MEM),
                _src("Sunlight 800 W/m², loss coefficient of the tin", ILL)],
               {"params": {}, "reading": "ratio", "textbook": "sw7_tins_ratio", "tol": 0.05})


def liquid_sp_heat():
    return _mk("specific-heat-liquid", RH, "Specific heat capacity of a liquid by the method of mixtures", "Class XI", "Thermal Properties of Matter",
               "Drop a hot brass bob into kerosene in a calorimeter, read the final temperature and work out the specific heat capacity of the kerosene.",
               "mixtures", {"m1": 0.1, "c1": 380.0, "T1": 100.0, "m2": 0.12, "c2": 2010.0, "T2": 28.0, "mc": 0.05, "cc": 385.0}, "Tw",
               "Heat lost by the hot solid equals heat gained by the liquid and the calorimeter: m1 c1 (T1 − T) = (m2 c2 + mc cc)(T − T2). With the solid's specific heat known, the liquid's is c2 = [m1 c1 (T1 − T) − mc cc (T − T2)] / [m2 (T − T2)].",
               "Kerosene catches fire: no flame near the calorimeter. Lift the hot bob by its thread only.",
               ["Weigh the calorimeter empty and with kerosene.", "Heat the brass bob in boiling water and note its temperature.",
                "Transfer it quickly to the kerosene, stir and read the highest temperature.", "Work out the specific heat capacity of the kerosene."],
               [("The bob is transferred quickly so that", ["It loses little heat to the air", "The kerosene does not spill", "The thermometer is not broken"], "Heat lost on the way is not counted in the equation."),
                ("Kerosene warms more than the same mass of water would because its specific heat is", ["Smaller", "Larger", "Zero"], "Less heat is needed for each degree.")],
               [L11, _src("Specific heat: kerosene 2010, brass 380, copper 385 J/(kg K)", MEM)],
               {"params": {}, "reading": "Tf", "textbook": "mix_Tf"})


def wax_cooling():
    return _mk("wax-cooling-curve", RH, "Cooling curve of molten wax and its melting point", "Class XI", "Thermal Properties of Matter",
               "Let molten paraffin wax cool in a test tube, read the thermometer every half minute and find the melting point from the flat part of the curve.",
               "sw7_waxcool", {}, "reading",
               "A hot liquid cools steadily until it starts to freeze. While it changes state it gives out latent heat, so its temperature stays the same although it is still losing heat. The flat part of the cooling curve is at the melting point. Once all of it is solid it cools again.",
               "Molten wax burns skin: hold the tube in a clamp and keep it upright.",
               ["Melt the wax in a water bath and note the temperature.", "Clamp the tube in air and start the stopwatch.",
                "Read the thermometer every 30 s until the wax is solid and cooling again.", "Plot temperature against time; the flat part gives the melting point."],
               [("During the flat part of the curve the wax is", ["Changing from liquid to solid", "Not losing any heat", "Getting hotter"], "Latent heat is given out at a steady temperature."),
                ("The heat given out at constant temperature is called", ["Latent heat", "Specific heat", "Radiant heat"], "It is the heat of the change of state.")],
               [L11, _src("Paraffin wax: melting point 57 °C (commercial waxes 46 to 68 °C), latent heat 200 kJ/kg, specific heat 2.5 kJ/(kg K)", MEM)],
               {"params": {}, "reading": "Tm_meas", "textbook": "sw7_wax_Tm"})


def bimetallic():
    return _mk("bimetallic-strip", RH, "Effect of heating on a bimetallic strip", "Class XI", "Thermal Properties of Matter",
               "Heat a brass and iron bimetallic strip clamped at one end, measure how far its tip bends at each temperature and find the difference of the two expansivities.",
               "sw7_bimetal", {}, "defl",
               "Brass expands more than iron for the same rise in temperature. Riveted together they cannot slide, so the strip bends with the brass on the outside. For two layers of equal thickness the curvature is 3 Δα ΔT / (2 t), and the tip of a strip of length L moves by δ = 3 Δα ΔT L² / (4 t). Equal stiffness of the two metals is assumed.",
               "The strip and the heater stay hot: do not touch them until they have cooled.",
               ["Clamp the strip and note the tip's position on the scale at room temperature.", "Heat the strip and read its temperature.",
                "Read how far the tip has moved.", "Repeat at two more temperatures and work out Δα."],
               [("On heating, the strip bends so that the brass is on the", ["Outside of the curve", "Inside of the curve", "It stays straight"], "Brass expands more, so it takes the longer outer path."),
                ("A bimetallic strip is used in", ["A thermostat", "A voltmeter", "A lens"], "Its bending opens and closes a switch.")],
               [L11, _src("Linear expansivity: brass 19 × 10⁻⁶ /K, iron 11.8 × 10⁻⁶ /K", "CRC Handbook of Chemistry and Physics, quoted " + MEM)],
               {"params": {}, "reading": "da_meas", "textbook": "sw7_bimetal_da"})


def liquid_level():
    return _mk("liquid-level-heating", RH, "Change in the level of a liquid on heating", "Class XI", "Thermal Properties of Matter",
               "Warm a flask of glycerine fitted with a narrow tube, read the rise of the level at each temperature and find the apparent expansivity of the liquid.",
               "sw7_level", {}, "dh",
               "Liquids expand more than solids. When the flask is warmed the glass expands first and the level dips for a moment; then the liquid warms and rises up the tube. The rise is Δh = V0 (γ − γg) ΔT / a, where a is the bore area and γ − γg is the apparent expansivity of the liquid in glass.",
               "Warm the flask in a water bath, never over a bare flame.",
               ["Note the level in the tube at room temperature.", "Warm the water bath by 5 °C and wait for the level to settle.",
                "Read the rise of the level on the scale.", "Repeat up to 20 °C above room temperature and work out the apparent expansivity."],
               [("The level first dips slightly because", ["The flask expands before the liquid warms", "The liquid contracts", "Liquid evaporates"], "The glass is heated first."),
                ("The expansion seen in the tube is called apparent because", ["The vessel has expanded too", "It is not real", "The scale is wrong"], "The real expansion is larger by the expansion of the glass.")],
               [L11, _src("Cubical expansivity: glycerine 4.9 × 10⁻⁴ /K, soda glass 2.55 × 10⁻⁵ /K", MEM)],
               {"params": {}, "reading": "gapp_meas", "textbook": "sw7_level_gapp"})


def heat_loss():
    return _mk("rate-of-heat-loss", RH, "Factors affecting the rate of loss of heat of a liquid", "Class XI", "Thermal Properties of Matter",
               "Time hot water cooling by 5 °C, then change one thing at a time: the exposed area, the surface, the temperature difference and the mass.",
               "sw7_loss", {}, "tdrop",
               "A hot liquid loses heat at a rate proportional to its exposed area, to the nature of its surface and to its excess temperature over the room (Newton's law of cooling). For the same loss of heat a larger mass cools more slowly. The cooling constant is k = h A / (m c), and the time to cool from T1 to T2 is ln[(T1 − Ts)/(T2 − Ts)] / k.",
               "Hot water scalds: use the tongs and keep the calorimeters on their stands.",
               ["Fill the calorimeter with hot water and time a fall of 5 °C.", "Repeat with a wider vessel, then a polished one.",
                "Repeat starting from a lower temperature, then with twice the water.", "Compare the times and work out the cooling constant."],
               [("Tea cools faster in a saucer than in a cup because", ["The exposed area is larger", "The saucer is colder", "There is more tea"], "The rate of loss of heat grows with the exposed area."),
                ("A liquid cools fastest when its temperature is", ["Far above the room's", "Just above the room's", "Equal to the room's"], "The rate is proportional to the excess temperature.")],
               [L11, _src("Specific heat of water 4186 J/(kg K)", "CRC Handbook of Chemistry and Physics"),
                _src("Heat-loss coefficient and the polished-surface factor", ILL)],
               {"params": {}, "reading": "k_meas", "textbook": "sw7_loss_k"})


# =================================================================================================== ELECTRIC
def electroplating():
    return _mk("electroplating-copper", RE, "Electroplating with copper sulphate and copper plates", "Class VIII", "Electricity",
               "Pass a steady current through copper sulphate solution between two copper plates, weigh the cathode before and after and find the mass deposited per coulomb.",
               "sw7_plating", {}, "dm",
               "A current through copper sulphate solution carries copper from the plate joined to the positive terminal to the plate joined to the negative terminal. The mass deposited is proportional to the charge passed: m = Z I t (Faraday's first law). For copper, Z = M / (2 F), because each Cu²⁺ ion carries two charges.",
               "Copper sulphate is harmful: wear gloves and goggles and wash your hands afterwards.",
               ["Clean, dry and weigh the cathode plate.", "Pass a steady current for the time shown, keeping it constant with the rheostat.",
                "Rinse, dry and weigh the cathode again.", "Work out Z = m / (I t); repeat for another time and current."],
               [("Copper is deposited on the plate joined to the", ["Negative terminal", "Positive terminal", "Both plates"], "Copper ions are positive and move to the cathode."),
                ("Doubling the time at the same current deposits", ["Twice the mass", "The same mass", "Half the mass"], "The mass is proportional to the charge passed.")],
               [N8, _src("Faraday constant 96485.33212 C/mol", "CODATA 2018 (exact since the 2019 SI)"),
                _src("Molar mass of copper 63.546 g/mol", "IUPAC standard atomic weights")],
               {"params": {}, "reading": "Z_meas", "textbook": "sw7_plating_Z"})


def liquid_conductivity():
    return _mk("liquid-conductivity", RE, "Which liquids conduct electricity: the LED tester", "Class VIII", "Electricity",
               "Dip an LED tester with a milliammeter into tap water, distilled water, lemon juice, vinegar and salt solution; see which make the LED glow.",
               "sw7_liquid", {"liq": 0.0}, "I",
               "A liquid conducts when it holds ions that can move. Distilled water has almost none and is a poor conductor; salts and acids dissolved in water give ions, so tap water, lemon juice, vinegar and salt solution conduct. The current through the tester is I = (V − Vf) / (Rs + R), where R is the resistance of the liquid between the plates.",
               "Use only the cells of the tester, never the mains. Rinse the plates between liquids.",
               ["Check the tester by touching its two plates together.", "Dip the plates into a liquid and see whether the LED glows.",
                "Read the milliammeter.", "Rinse the plates and repeat for every liquid."],
               [("Distilled water is a poor conductor because it has", ["Almost no ions", "No water", "Too many ions"], "Current in a liquid is carried by ions."),
                ("Adding a pinch of salt to distilled water makes it", ["A good conductor", "A poorer conductor", "No different"], "Salt dissolves into ions.")],
               [N8, _src("Conductivity: tap water 0.05, distilled water 0.0001, lemon juice 0.4, vinegar 0.3, 1 % salt solution 1.7 S/m", MEM + "; natural liquids vary widely"),
                _src("Red LED forward voltage 1.8 V", "typical datasheet value, " + MEM)],
               {"params": {}, "reading": "s_meas", "textbook": "sw7_liquid_s"})


def force_conductor():
    return _mk("force-on-conductor", RE, "Force on a current-carrying rod in a magnetic field", "Class X", "Magnetic Effects of Current",
               "Hang an aluminium rod between the poles of a horseshoe magnet, pass a current and measure its swing; reverse the current and the magnet.",
               "sw7_swing", {}, "ang",
               "A conductor carrying a current I across a magnetic field B feels a force F = B I L at right angles to both (Fleming's left-hand rule). The hanging rod swings aside until tan θ = B I L / (m g). Reversing the current or the field reverses the force; reversing both leaves it as it was.",
               "Switch the current on only for the reading: the rod and the wires get warm.",
               ["Hang the rod level between the poles.", "Close the key and read the angle of the swing.",
                "Reverse the current, then the magnet, and note the direction each time.", "Work out B = m g tan θ / (I L)."],
               [("Reversing the current makes the rod swing", ["The opposite way", "The same way", "Not at all"], "The force reverses with the current."),
                ("The rule that gives the direction of the force is", ["Fleming's left-hand rule", "Fleming's right-hand rule", "The right-hand thumb rule"], "Forefinger field, middle finger current, thumb force.")],
               [N10, _src("Field between the poles of the horseshoe magnet", "an unknown magnet; its field is the hidden unknown")],
               {"params": {}, "reading": "B_meas", "textbook": "sw7_swing_B"})


def multimeter():
    return _mk("multimeter", RE, "Using a multimeter: resistance, voltage, current, continuity", "Class XII", "Current Electricity",
               "Use a digital multimeter to measure a resistor, a battery, the output of a transformer and a current, and to check a wire for continuity.",
               "sw7_dmm", {"mode": 0.0}, "reading",
               "A multimeter is an ohmmeter, a voltmeter and an ammeter in one case. The dial chooses the quantity and the range. It is joined across a component for voltage and resistance, and in series for current. On the continuity setting it beeps when the resistance between the probes is very small.",
               "Never measure resistance in a live circuit, and never join the meter across a supply on a current range.",
               ["Turn the dial to Ω and measure the resistor on its own.", "Turn to DC volts and measure the battery; turn to AC volts for the transformer.",
                "Turn to mA, join the meter in series with the battery and the resistor, and read the current.", "Turn to continuity and test the wire."],
               [("To measure a current the multimeter is joined", ["In series", "In parallel", "Across the battery"], "The whole current must pass through the meter."),
                ("Resistance must be measured with the circuit", ["Switched off", "Switched on", "At full current"], "The meter uses its own small battery.")],
               [L12, _src("The resistor, battery and transformer", "unknown components; the resistance is the hidden unknown")],
               {"params": {"mode": 0.0}, "reading": "reading", "textbook": "sw7_dmm_R"})


def diode_led():
    return _mk("diode-led-multimeter", RE, "One-way flow of current in a diode and an LED", "Class XII", "Semiconductor Electronics",
               "Test a diode and an LED with the diode setting of a multimeter, both ways round; read the forward voltage and see that the reverse way shows no current.",
               "sw7_dtest", {"dev": 0.0, "dir": 1.0}, "reading",
               "A p-n junction lets current pass one way only. Forward biased (red probe on the anode) the meter passes about 1 mA and shows the forward voltage: about 0.6 V for a silicon diode and about 1.8 V for a red LED, which also glows faintly. Reverse biased it shows OL: no current flows. A component that conducts both ways, or neither way, is faulty.",
               "Hold the component by its body; do not bend the leads at the case.",
               ["Turn the multimeter to the diode setting.", "Touch the red probe to the anode and the black to the cathode; read the display.",
                "Reverse the probes and read again.", "Repeat for the LED."],
               [("A good diode on the diode test shows", ["A voltage one way and OL the other way", "OL both ways", "Zero both ways"], "It conducts in one direction only."),
                ("The forward voltage of a red LED compared with a silicon diode is", ["Larger", "Smaller", "The same"], "Its band gap is larger, which is why it gives out light.")],
               [L12, _src("Shockley parameters of the diode (n 1.8, Is 3 nA) and the LED (n 2, Is 2 × 10⁻¹⁸ A)", ILL + "; chosen to give typical datasheet forward voltages at 1 mA")],
               {"params": {"dev": 0.0, "dir": 1.0}, "reading": "reading", "textbook": "sw7_dtest_Vf"})


BUILDERS = (rolling_surfaces, rolling_vs_sliding, trolley_block, incline_roller, double_incline, projectile, free_fall,
            ball_sand, stairs_power, pendulum_decay,
            pressure_holes, cuboid_sand, bottle_upthrust, cork_nail, beam_balance, vernier_vessel, screw_sheet, paper_scale,
            lens_combination,
            sound_solids, sound_reflection, black_white_tins, liquid_sp_heat, wax_cooling, bimetallic, liquid_level, heat_loss,
            electroplating, liquid_conductivity, force_conductor, multimeter, diode_led)
