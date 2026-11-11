"""Lab pack: Class 6-10 mechanics - Motion, Friction, Pressure, Gravitation and Floatation, Work and Energy.

The physics lives in `app/prayog/packs/mech_school.py` (with its JavaScript twin); the studio rigs live in
`app/static/prayog/exp/<rig>.js`. Several labs share one rig through the `rig` field:

    motion-track         - a grooved track with a printed metre scale, a motor car / a trolley, a stopwatch
                           -> motion-track, distance-time-graph
    friction-pull        - a block on a flat surface pulled by a spring balance, slotted weights on top
                           -> friction-pull, friction-lubricant
    archimedes-balance   - a spring balance on a stand, a graduated jar and a measuring cylinder
                           -> archimedes-balance, solid-density
    sucker-pressure      - rubber suction cups on a plate glass sheet, pulled by a spring balance

Every constant used here is named with its source on the lab (`sources`) and in the family files beside it.
"""
from __future__ import annotations

from ..catalog import B, knob, lab

NCERT8 = {"title": "Science, Textbook for Class VIII, NCERT", "note": "chapters Force and Pressure; Friction"}
NCERT9 = {"title": "Science, Textbook for Class IX, NCERT", "note": "chapters Motion; Force and Laws of Motion; Gravitation; Work and Energy"}
LABMAN9 = {"title": "Laboratory Manual, Science, Class IX, NCERT",
           "note": "experiments on Archimedes' principle and the density of a solid"}
SIM = {"title": "Hoola Prayogshala kernel",
       "note": "every reading comes from the simulation code; it is checked against the NCERT formula in Hoola's tests"}
FRICTION_TABLE = {"title": "Serway & Jewett, Physics for Scientists and Engineers - table of coefficients of friction",
                  "note": "wood on wood 0.25, glass on glass 0.94, steel on steel 0.74, aluminium on steel 0.61, "
                          "copper on steel 0.53, metal on metal (lubricated) 0.15"}
CRC = {"title": "CRC Handbook of Chemistry and Physics",
       "note": "densities of aluminium, iron, copper, brass, water, kerosene, glycerine and saturated brine"}
ISA = {"title": "ISO 2533:1975 Standard Atmosphere",
       "note": "air pressure 101.325 kPa at sea level, 89.876 kPa at 1000 m, 79.501 kPa at 2000 m, 70.121 kPa at 3000 m"}


# ======================================================================================= motion on a track
def _track_bodies(moving_name: str, moving_info: str, rise: float) -> list[dict]:
    return [
        B("bench", "box", name="Laboratory table", size=[1.3, 0.02, 0.4], pos=[0, -0.01, 0], color="wood", cut=False),
        B("prop", "box", name="Wooden block under one end", info="Raises the far end of the track for the accelerated run.",
          size=[0.08, max(0.004, rise), 0.09], pos=[-0.52, max(0.002, rise / 2), 0], color="#8c5a2b"),
        B("rail", "box", name="Grooved track", info="A straight wooden track 1.1 m long with a shallow groove, so the body runs in a straight line.",
          size=[1.1, 0.014, 0.1], pos=[0, 0.007 + rise / 2, 0], color="wood"),
        B("scalebar", "scale", name="Printed metre scale (cm)", info="Fixed along the track. Its zero is at the starting line.",
          length=1.0, spacing=0.01, major=10, labels=True, label_step=10, tick=0.012, font=0.016,
          pos=[-0.5, 0.015 + rise / 2, 0.055], rot=[-1.5708, 0, 1.5708]),
        B("start", "box", name="Starting line", size=[0.002, 0.004, 0.1], pos=[-0.5, 0.016 + rise / 2, 0], color="red"),
        B("buffer", "box", name="Buffer", info="A padded stop at the far end of the track.", size=[0.02, 0.05, 0.1],
          pos=[0.55, 0.04 + rise / 2, 0], color="black"),
        B("car", "box", name=moving_name, info=moving_info, size=[0.09, 0.045, 0.06],
          pos=[-0.455, 0.04 + rise / 2, 0], color="#1f4f8c", bind={"x": {"var": "car_x", "c": -0.455}}),
        B("wheelA", "cylinder", name="Wheel", r=0.016, h=0.008, pos=[-0.48, 0.022 + rise / 2, 0.034], rot=[1.5708, 0, 0], color="black"),
        B("wheelB", "cylinder", name="Wheel", r=0.016, h=0.008, pos=[-0.43, 0.022 + rise / 2, 0.034], rot=[1.5708, 0, 0], color="black"),
        B("watch", "box", name="Digital stopwatch", info="Least count 0.01 s. Started as the body crosses the zero mark.",
          size=[0.07, 0.015, 0.05], pos=[0.3, 0.008, 0.16], color="#2b2f36"),
    ]


def motion_track() -> dict:
    """NCERT Class VII / IX: speed of a body in uniform motion, from a measured distance and time."""
    return lab(
        id="motion-track", title="Uniform motion: speed from distance and time",
        group="Physics · Mechanics", level="Class VII-IX", topic="Motion", chapter="Motion",
        aim="Time a body moving with a steady speed over measured distances and find its speed.",
        kernel="track", params={"u": 0.25, "acc": 0.0, "len": 1.0, "mark": 0.8},
        camera={"pos": [0.0, 0.5, 1.1], "look": [0, 0.05, 0]}, floor=-0.02,
        bodies=_track_bodies("Motor-driven car", "A battery car that runs at a steady speed. Its speed is what you measure.", 0.0),
        knobs=[knob("u", "Car (steady speed hidden)", "u", 0.08, 0.6, 0.005, 0.25, "m/s", hidden=True),
               knob("mark", "Mark timed to", "mark", 0.1, 1.0, 0.1, 0.8, "m")],
        steps=["Lay the track flat and fix the metre scale along it, zero at the starting line.",
               "Switch the car on and let it reach its steady speed before the zero mark.",
               "Start the stopwatch as the car's front crosses the zero mark and stop it at the 20 cm mark.",
               "Repeat for 40, 60 and 80 cm.",
               "Plot distance against time: the graph is a straight line through the origin and its slope is the speed."],
        theory="A body in uniform motion covers equal distances in equal intervals of time. Its speed is "
               "v = distance / time, so a graph of distance against time is a straight line whose slope is the speed.",
        safety="Keep the track clear and catch the car at the buffer; do not let it fall off the table.",
        questions=[{"q": "In uniform motion, what does the distance-time graph look like?",
                    "options": ["A straight line through the origin", "A curve bending upwards", "A horizontal line"],
                    "answer": 0, "why": "Equal distances in equal times give a constant slope, and at t = 0 the distance is 0."},
                   {"q": "The slope of a distance-time graph gives", "options": ["speed", "acceleration", "distance"],
                    "answer": 0, "why": "Slope = change in distance / change in time = speed."}],
        sources=[NCERT9, SIM],
        check={"params": {"mark": 0.8}, "reading": "t_mark", "textbook": "track_t"},
    )


def distance_time_graph() -> dict:
    """NCERT Class IX: the distance-time graph of a uniformly accelerated trolley."""
    return lab(
        id="distance-time-graph", title="Distance-time graph of an accelerating trolley",
        group="Physics · Mechanics", level="Class IX", topic="Motion", chapter="Motion", rig="motion-track",
        aim="Time a trolley released down a gently sloping track and find its acceleration from the graph.",
        kernel="track", params={"u": 0.0, "acc": 0.25, "len": 1.0, "mark": 0.8},
        camera={"pos": [0.0, 0.5, 1.1], "look": [0, 0.05, 0]}, floor=-0.02,
        bodies=_track_bodies("Trolley", "A free-running trolley. Released from rest, it speeds up steadily down the slope.", 0.028),
        knobs=[knob("acc", "Slope (acceleration hidden)", "acc", 0.05, 1.2, 0.01, 0.25, "m/s²", hidden=True),
               knob("mark", "Mark timed to", "mark", 0.1, 1.0, 0.1, 0.8, "m")],
        steps=["Raise the far end of the track on the wooden block, so the trolley runs down a gentle slope.",
               "Hold the trolley at the zero mark and release it from rest as you start the stopwatch.",
               "Stop the stopwatch when the trolley's front reaches the 20 cm mark.",
               "Repeat for 40, 60 and 80 cm.",
               "Plot distance against time (a curve) and against time squared (a straight line); the slope of the second graph is a/2."],
        theory="A body released from rest with a steady acceleration a covers s = ½ a t². The distance-time graph is "
               "therefore a curve, but a graph of distance against the square of the time is a straight line through "
               "the origin whose slope is a/2.",
        safety="Release the trolley gently, without a push, and let the buffer stop it.",
        questions=[{"q": "For a trolley released from rest, distance is proportional to",
                    "options": ["the square of the time", "the time", "the square root of the time"], "answer": 0,
                    "why": "s = ½ a t² when the starting speed is zero."},
                   {"q": "Why plot distance against t² and not t?",
                    "options": ["Because then the graph is a straight line and its slope gives a",
                                "Because t is hard to measure", "Because the units match"], "answer": 0,
                    "why": "A straight line is easy to draw and its slope is a/2."}],
        sources=[NCERT9, SIM],
        check={"params": {"mark": 0.8}, "reading": "t_mark", "textbook": "track_t"},
    )


# ======================================================================================= friction: pull a block
def _pull_bodies(surface: str, surface_info: str, surface_colour: str) -> list[dict]:
    return [
        B("bench", "box", name="Laboratory table", size=[1.0, 0.02, 0.45], pos=[0, -0.01, 0], color="wood", cut=False),
        B("sheet", "box", name=surface, info=surface_info, size=[0.6, 0.004, 0.22], pos=[-0.05, 0.002, 0], color=surface_colour),
        B("block", "box", name="Wooden block with a hook", info="Mass 500 g, weighed on a balance. Slotted weights go on top of it.",
          size=[0.1, 0.06, 0.08], pos=[-0.27, 0.034, 0], color="#b98a58", bind={"x": {"var": "s", "c": -0.27}}),
        B("hook", "torus", name="Hook", r=0.005, tube=0.0014, pos=[-0.215, 0.034, 0], rot=[0, 1.5708, 0], color="brass"),
        B("weights", "cylinder", name="Slotted weights", info="Flat slotted weights that sit on the block and increase the normal reaction.",
          r=0.028, h=0.014, pos=[-0.27, 0.071, 0], color="iron" if False else "steel"),
        B("balance", "box", name="Spring balance (0-10 N)", info="Least count 0.05 N. Read the largest value just before the block moves.",
          size=[0.2, 0.035, 0.035], pos=[-0.06, 0.034, 0], color="#2b2f36"),
        B("bscale", "scale", name="Spring balance scale (N)", length=0.16, spacing=0.008, major=5, labels=True,
          label_step=5, tick=0.008, font=0.012, pos=[-0.14, 0.053, 0.0], rot=[0, 0, -1.5708]),
        B("thread", "rope", name="Thread", info="Keep it horizontal and in line with the block, so the whole pull goes along the surface.",
          a="hook", b={"body": "balance", "off": [-0.1, 0, 0]}, r=0.0012, color="ink"),
        B("ring", "torus", name="Pull ring", r=0.012, tube=0.0025, pos=[0.055, 0.034, 0], rot=[0, 1.5708, 0], color="chrome" if False else "steel"),
        B("box2", "box", name="Weight box", info="500 g, 1 kg and 2 kg slotted weights.", size=[0.18, 0.05, 0.12],
          pos=[0.33, 0.025, 0.1], color="#7a4e2c"),
    ]


def _friction_lab(lab_id: str, title: str, aim: str, mu: float, surface: str, surface_info: str, colour: str,
                  theory_tail: str, rig: str | None, chapter: str, extra: list[dict]) -> dict:
    d = lab(
        id=lab_id, title=title, group="Physics · Mechanics", level="Class VIII-IX", topic="Friction",
        chapter=chapter, aim=aim,
        kernel="pullblock", params={"mu": mu, "m": 0.5, "load": 0.0, "g": 9.8, "len": 0.3},
        camera={"pos": [0.1, 0.4, 0.8], "look": [-0.1, 0.04, 0]}, floor=-0.02,
        bodies=_pull_bodies(surface, surface_info, colour),
        knobs=[knob("mu", "Surfaces (coefficient of friction hidden)", "mu", 0.05, 1.2, 0.01, mu, hidden=True),
               knob("load", "Weights on the block", "load", 0.0, 8.0, 0.1, 0.0, "kg")],
        steps=["Lay the surface flat on the table and put the block on it, hook towards the balance.",
               "Hook the spring balance to the block and keep the thread horizontal.",
               "Pull very slowly and steadily and read the largest value on the balance just as the block begins to move.",
               "Put slotted weights on the block and take the reading again for three more loads.",
               "Plot the limiting friction against the normal reaction: the slope is the coefficient of friction μ."],
        theory="A block at rest on a surface does not move until the pull exceeds the limiting friction. Limiting "
               "friction is proportional to the normal reaction: f = μ N, where N = (mass of block + load) × g and μ "
               "is the coefficient of friction between the two surfaces. " + theory_tail,
        safety="Pull slowly: a jerk gives a reading that is too high. Keep the surface clean and the thread horizontal.",
        questions=[{"q": "Why must the thread be kept horizontal?",
                    "options": ["Otherwise part of the pull lifts the block and changes N",
                                "Otherwise the balance breaks", "It does not matter"], "answer": 0,
                    "why": "A slanting pull has a vertical part, which changes the normal reaction and so the friction."},
                   {"q": "Doubling the weights on the block makes the limiting friction",
                    "options": ["about twice as large", "the same", "half as large"], "answer": 0,
                    "why": "f = μ N, and N grows with the total weight pressing the surfaces together."}],
        sources=[NCERT8, FRICTION_TABLE, SIM] + extra,
        check={"params": {"load": 1.5}, "reading": "P_min", "textbook": "friction_Pmin"},
    )
    if rig:
        d["rig"] = rig
    return d


def friction_pull() -> dict:
    """NCERT Class VIII: the force of friction on different surfaces, with a spring balance."""
    return _friction_lab(
        "friction-pull", "Force of friction on different surfaces",
        "Find the least force that moves a block along a surface, and from it the coefficient of friction.",
        0.25, "Wooden surface", "A planed wooden board. The block and the board are both wood.", "wood",
        "The rougher the pair of surfaces, the larger μ.", None, "Friction", [])


def friction_lubricant() -> dict:
    """NCERT Class VIII: oil between two surfaces reduces friction."""
    return _friction_lab(
        "friction-lubricant", "Oil reduces friction between two metal surfaces",
        "Measure the friction between two dry metal surfaces, then with oil between them, and compare.",
        0.74, "Steel plate (dry)", "A ground steel plate. The block is faced with steel, so it is steel on steel.", "steel",
        "A lubricant keeps a thin layer of oil between the two surfaces, so they no longer rub directly and μ falls.",
        "friction-pull", "Friction", [])


# ======================================================================================= upthrust, density
def _buoy_bodies(solid: str, solid_info: str, liquid: str, liquid_colour: str, cylinder: bool) -> list[dict]:
    out = [
        B("bench", "box", name="Laboratory table", size=[0.9, 0.02, 0.45], pos=[0, -0.01, 0], color="wood", cut=False),
        B("base", "box", name="Stand base", size=[0.2, 0.022, 0.15], pos=[-0.26, 0.011, -0.02], color="#2b3138"),
        B("rod", "cylinder", name="Stand rod", r=0.008, h=0.6, pos=[-0.31, 0.32, -0.02], color="steel"),
        B("arm", "box", size=[0.14, 0.012, 0.012], pos=[-0.24, 0.5, -0.02], color="steel"),
        B("balance", "box", name="Spring balance (0-5 N)", info="Least count 0.02 N. It hangs from the stand and carries the solid.",
          size=[0.045, 0.2, 0.035], pos=[-0.17, 0.38, -0.02], color="#2b2f36"),
        B("bscale", "scale", name="Spring balance scale (N)", length=0.16, spacing=0.008, major=5, labels=True,
          label_step=5, tick=0.008, font=0.012, pos=[-0.148, 0.3, -0.002]),
        B("hook", "torus", name="Hook", r=0.005, tube=0.0014, pos=[-0.17, 0.277, -0.02], color="brass"),
        B("jar", "cylinder", name="Glass jar", info="Holds the liquid. The solid is lowered into it.", r=0.05, h=0.16,
          open=True, pos=[-0.17, 0.08, -0.02], color="glass", opacity=0.25),
        B("liq", "cylinder", name=liquid, info="The liquid the solid is immersed in.", r=0.047, h=0.12,
          pos=[-0.17, 0.062, -0.02], color=liquid_colour),
        B("solid", "cylinder", name=solid, info=solid_info, r=0.02, h=0.095, pos=[-0.17, 0.2, -0.02], color="steel"),
        B("thread", "rope", name="Thread", a="hook", b={"body": "solid", "off": [0, 0.048, 0]}, r=0.0009, color="ink"),
    ]
    if cylinder:
        out += [
            B("mcyl", "cylinder", name="Measuring cylinder (250 mL)", info="Bore 40.1 mm. Its scale is read to 1 mL.",
              r=0.0201, h=0.26, open=True, pos=[0.14, 0.13, -0.02], color="glass", opacity=0.25),
            B("mwater", "cylinder", name="Water in the cylinder", r=0.0195, h=0.1, pos=[0.14, 0.05, -0.02], color="water",
              bind={"sy": {"var": "level", "k": 1.0, "c": 1.0, "min": 0.5, "max": 3.0}}),
            B("mscale", "scale", name="Cylinder scale (mL)", length=0.2, spacing=0.0016, major=5, labels=True,
              label_step=25, tick=0.006, font=0.01, pos=[0.16, 0.02, 0.0]),
            B("beaker", "cylinder", name="Beaker", info="Water to set the starting level in the cylinder.", r=0.035,
              h=0.07, open=True, pos=[0.3, 0.035, 0.1], color="glass", opacity=0.3),
        ]
    else:
        out += [B("ruler", "scale", name="Metre scale (cm)", length=0.3, spacing=0.001, major=10, labels=True,
                  label_step=10, tick=0.008, font=0.012, pos=[0.12, 0.004, 0.08], rot=[-1.5708, 0, 1.5708])]
    return out


def archimedes_balance() -> dict:
    """NCERT Class IX laboratory manual: the loss in weight of an immersed solid is the weight of liquid it displaces."""
    return lab(
        id="archimedes-balance", title="Archimedes' principle: loss in weight on immersion",
        group="Physics · Mechanics", level="Class IX", topic="Gravitation and Floatation",
        chapter="Gravitation and Floatation",
        aim="Lower a solid into a liquid step by step and show that its loss in weight equals the weight of the liquid it displaces.",
        kernel="buoy", params={"rho_s": 2700.0, "rho_l": 998.0, "V": 1.2e-4, "g": 9.8, "frac": 0.0, "Acyl": 1.264e-3},
        camera={"pos": [0.0, 0.45, 0.65], "look": [-0.15, 0.18, -0.02]}, floor=-0.02,
        bodies=_buoy_bodies("Aluminium cylinder", "40.0 mm across and 95.5 mm long, so its volume is 120 cm³ (measured with callipers).",
                            "Water", "water", False),
        knobs=[knob("rho_l", "Liquid (density hidden)", "rho_l", 700.0, 1400.0, 1.0, 998.0, "kg/m³", hidden=True),
               knob("frac", "Fraction of the solid under the surface", "frac", 0.0, 1.0, 0.05, 0.0)],
        steps=["Hang the solid from the spring balance and read its weight in air.",
               "Lower it until one quarter of its length is under the liquid and read the balance again.",
               "Repeat at one half, three quarters and fully immersed, without letting the solid touch the jar.",
               "Work out the upthrust for each reading: U = weight in air − reading.",
               "Plot the upthrust against the volume of liquid displaced; the loss in weight when fully immersed is the weight of the liquid displaced."],
        theory="A body immersed in a liquid is pushed up by an upthrust equal to the weight of the liquid it "
               "displaces (Archimedes' principle): U = ρ g V, where V is the volume of the body under the surface. "
               "The spring balance therefore reads less than the true weight, and the loss in weight is exactly U.",
        safety="Do not let the solid touch the bottom or the sides of the jar, and keep the balance hanging freely.",
        questions=[{"q": "The loss in weight of a fully immersed solid equals",
                    "options": ["the weight of the liquid it displaces", "its own weight", "the weight of the jar"],
                    "answer": 0, "why": "That is Archimedes' principle."},
                   {"q": "If the same solid is immersed in a denser liquid, the loss in weight",
                    "options": ["increases", "stays the same", "decreases"], "answer": 0,
                    "why": "U = ρ g V, so a larger ρ gives a larger upthrust for the same volume."}],
        sources=[LABMAN9, NCERT9, CRC, SIM],
        check={"params": {"frac": 1.0}, "reading": "loss", "textbook": "arch_loss"},
    )


def solid_density() -> dict:
    """NCERT Class IX laboratory manual: density of a solid denser than water, by spring balance and measuring cylinder."""
    return lab(
        id="solid-density", title="Density of a solid with a balance and a measuring cylinder",
        group="Physics · Mechanics", level="Class IX", topic="Gravitation and Floatation",
        chapter="Gravitation and Floatation", rig="archimedes-balance",
        aim="Find the mass of a solid on a spring balance and its volume by displacement, and work out its density.",
        kernel="buoy", params={"rho_s": 2700.0, "rho_l": 998.0, "V": 4.82e-5, "g": 9.8, "frac": 0.0, "Acyl": 1.264e-3},
        camera={"pos": [0.0, 0.45, 0.65], "look": [-0.1, 0.16, -0.02]}, floor=-0.02,
        bodies=_buoy_bodies("Metal cylinder", "The solid whose density you are finding. It sinks in water.",
                            "Water", "water", True),
        knobs=[knob("rho_s", "Solid (density hidden)", "rho_s", 200.0, 12000.0, 10.0, 2700.0, "kg/m³", hidden=True),
               knob("frac", "Fraction of the solid under the surface", "frac", 0.0, 1.0, 0.05, 0.0)],
        steps=["Hang the solid from the spring balance and read its weight W; its mass is m = W / g.",
               "Pour water into the measuring cylinder and read the level V₁.",
               "Lower the solid in until it is fully under water and read the new level V₂.",
               "The volume of the solid is V₂ − V₁. Repeat with two more starting levels.",
               "Density = mass ÷ volume. Compare it with the density of water, 1000 kg/m³."],
        theory="The mass of a solid comes from its weight, m = W / g. A solid that sinks pushes aside exactly its own "
               "volume of water, so the rise of the water level in a measuring cylinder gives its volume. Density is "
               "then ρ = m / V. A solid denser than water sinks; one less dense floats.",
        safety="Lower the solid in on its thread so no water splashes out, and read the level with your eye at the "
               "bottom of the meniscus.",
        questions=[{"q": "Why does the water level rise when the solid goes in?",
                    "options": ["The solid pushes aside its own volume of water", "Water expands", "The solid dissolves"],
                    "answer": 0, "why": "A fully immersed solid displaces a volume of water equal to its own volume."},
                   {"q": "1 g/cm³ is the same as", "options": ["1000 kg/m³", "100 kg/m³", "10 kg/m³"], "answer": 0,
                    "why": "1 g/cm³ = 1000 kg / 1 m³."}],
        sources=[LABMAN9, CRC, SIM],
        check={"params": {"frac": 1.0}, "reading": "rho", "textbook": "solid_rho"},
    )


# ======================================================================================= atmospheric pressure
def sucker_pressure() -> dict:
    """NCERT Class VIII: atmospheric pressure measured with rubber suction cups of known area."""
    return lab(
        id="sucker-pressure", title="Atmospheric pressure with a rubber sucker",
        group="Physics · Mechanics", level="Class VIII", topic="Pressure", chapter="Pressure",
        aim="Pull rubber suction cups of different sizes off a glass sheet and work out the pressure of the air.",
        kernel="sucker", params={"Patm": 101325.0, "Pin": 0.0, "d": 0.01, "P": 0.0, "g": 9.8},
        camera={"pos": [0.0, 0.42, 0.6], "look": [0, 0.06, 0]}, floor=-0.02,
        bodies=[
            B("bench", "box", name="Laboratory table", size=[0.9, 0.02, 0.45], pos=[0, -0.01, 0], color="wood", cut=False),
            B("glass", "box", name="Plate glass sheet", info="Thick, clean and perfectly smooth, so no air leaks in under the sucker.",
              size=[0.3, 0.008, 0.22], pos=[-0.05, 0.004, 0], color="glass", opacity=0.3),
            B("sucker", "cone", name="Rubber sucker", info="Pressed down to drive the air out. The air outside then holds it against the glass.",
              r=0.008, h=0.012, pos=[-0.05, 0.014, 0], color="black"),
            B("stem", "cylinder", name="Sucker stem", r=0.0025, h=0.02, pos=[-0.05, 0.027, 0], color="black"),
            B("ring", "torus", name="Pull ring", r=0.008, tube=0.0018, pos=[-0.05, 0.04, 0], color="steel"),
            B("balance", "box", name="Spring balance (0-20 N)", info="Least count 0.1 N. Pulled straight up, it reads the force that takes the sucker off.",
              size=[0.04, 0.18, 0.03], pos=[-0.05, 0.14, 0], color="#2b2f36"),
            B("bscale", "scale", name="Spring balance scale (N)", length=0.14, spacing=0.007, major=5, labels=True,
              label_step=5, tick=0.007, font=0.011, pos=[-0.028, 0.07, 0.016]),
            B("thread", "rope", name="Thread", a="ring", b={"body": "balance", "off": [0, -0.09, 0]}, r=0.001, color="ink"),
            B("tray", "box", name="Tray of suckers", info="Four rubber suckers, 8, 10, 12 and 14 mm across.",
              size=[0.16, 0.02, 0.1], pos=[0.26, 0.01, 0.08], color="#7a4e2c"),
            B("vern", "box", name="Vernier callipers", info="Least count 0.02 mm. Used to measure each sucker's diameter.",
              size=[0.18, 0.012, 0.035], pos=[0.2, 0.006, -0.12], color="chrome" if False else "steel"),
        ],
        knobs=[knob("Patm", "Place (air pressure hidden)", "Patm", 60000.0, 105000.0, 100.0, 101325.0, "Pa", hidden=True),
               knob("d", "Sucker diameter", "d", 0.006, 0.02, 0.001, 0.01, "m")],
        steps=["Clean the glass sheet and the face of the sucker so no air can leak in.",
               "Press the sucker down hard to drive the air out from under it.",
               "Measure the sucker's diameter with the vernier callipers and work out its area A = π d² / 4.",
               "Hook the spring balance to the ring, pull straight up slowly and read the force at which the sucker comes off.",
               "Repeat with the other three suckers, then plot the force against the area: the slope is the pressure of the air."],
        theory="When a sucker is pressed on a smooth plate the air under it is driven out, so the pressure inside "
               "falls almost to zero while the atmosphere still presses on the outside. The plate then holds the "
               "sucker with a force F = (P_atm − P_in) × A, where A is the area of the sucker's face. Measuring F "
               "for suckers of different area and plotting F against A gives the pressure of the air as the slope.",
        safety="Pull straight up, slowly. A sideways or jerky pull peels the sucker off too early.",
        questions=[{"q": "Why is it hard to pull a sucker off a smooth plate?",
                    "options": ["The air outside presses it against the plate", "Glue holds it", "The glass is magnetic"],
                    "answer": 0, "why": "The air under the sucker was driven out, so only the outside air presses."},
                   {"q": "A sucker of twice the diameter needs a pull that is",
                    "options": ["about four times as large", "twice as large", "the same"], "answer": 0,
                    "why": "F = P × π d² / 4, and the area grows as the square of the diameter."},
                   {"q": "Why does a sucker not stick to a rough wall?",
                    "options": ["Air leaks in under it through the roughness", "The wall is too heavy",
                                "Rubber does not touch brick"], "answer": 0,
                    "why": "Air creeping in raises the pressure inside, so there is no pressure difference left."}],
        sources=[NCERT8, ISA, SIM],
        check={"params": {"d": 0.012}, "reading": "F_off", "textbook": "sucker_F"},
    )


# ======================================================================================= Newton's third law
def third_law() -> dict:
    """NCERT Class IX laboratory manual: two spring balances hooked together read the same force."""
    return lab(
        id="third-law-balances", title="Third law of motion with two spring balances",
        group="Physics · Mechanics", level="Class IX", topic="Force and Laws of Motion",
        chapter="Force and Laws of Motion",
        aim="Hook two spring balances together, pull one of them and show that both read the same force.",
        kernel="twospring", params={"X": 0.02, "k1": 200.0, "k2": 300.0},
        camera={"pos": [0.2, 0.4, 0.6], "look": [-0.12, 0.1, -0.06]}, floor=-0.02,
        bodies=[
            B("bench", "box", name="Laboratory table", size=[1.0, 0.02, 0.45], pos=[0, -0.01, 0], color="wood", cut=False),
            B("base", "box", name="Clamp stand base", size=[0.2, 0.022, 0.16], pos=[-0.46, 0.011, -0.06], color="#2b3138"),
            B("post", "cylinder", name="Clamp stand rod", r=0.008, h=0.26, pos=[-0.5, 0.13, -0.06], color="steel"),
            B("fix", "torus", name="Fixed hook", info="A rigid support. Balance A is hooked to it, so it cannot move.",
              r=0.008, tube=0.002, pos=[-0.47, 0.1, -0.06], color="steel"),
            B("balA", "box", name="Spring balance A (0-5 N)", info="Least count 0.05 N. Hooked to the fixed support.",
              size=[0.19, 0.032, 0.03], pos=[-0.355, 0.1, -0.06], color="#2b2f36"),
            B("scaleA", "scale", name="Scale of balance A (N)", length=0.17, spacing=0.0085, major=5, labels=True,
              label_step=5, tick=0.008, font=0.012, pos=[-0.44, 0.117, -0.045], rot=[0, 0, -1.5708]),
            B("balB", "box", name="Spring balance B (0-10 N)", info="Least count 0.1 N. The hand pulls its ring.",
              size=[0.19, 0.032, 0.03], pos=[-0.125, 0.1, -0.06], color="#2b2f36"),
            B("scaleB", "scale", name="Scale of balance B (N)", length=0.17, spacing=0.0085, major=5, labels=True,
              label_step=5, tick=0.008, font=0.012, pos=[-0.21, 0.117, -0.045], rot=[0, 0, -1.5708]),
            B("join", "torus", name="Joining hook", info="Balance B's hook is put through balance A's ring.",
              r=0.009, tube=0.0025, pos=[-0.24, 0.1, -0.06], color="steel"),
            B("ring", "torus", name="Pull ring", info="The hand pulls here, horizontally.", r=0.013, tube=0.003,
              pos=[-0.015, 0.1, -0.06], color="steel"),
        ],
        knobs=[knob("X", "How hard the hand pulls", "X", 0.002, 0.04, 0.001, 0.02, "m"),
               knob("k1", "Stiffness of balance A", "k1", 100.0, 400.0, 10.0, 200.0, "N/m", hidden=True),
               knob("k2", "Stiffness of balance B", "k2", 100.0, 400.0, 10.0, 300.0, "N/m", hidden=True)],
        steps=["Hook balance A to the fixed support on the clamp stand.",
               "Put balance B's hook through balance A's ring, so the two hang in a line.",
               "Pull balance B's ring steadily and horizontally, and hold it still.",
               "Read both balances at the same moment and write both readings down.",
               "Repeat for three more pulls, then plot B's reading against A's reading."],
        theory="When the hand pulls balance B, balance B pulls balance A and balance A pulls balance B back with an "
               "equal and opposite force. The two balances therefore always show the same reading, however hard the "
               "pull. This is Newton's third law: to every action there is an equal and opposite reaction. A graph of "
               "B's reading against A's reading is a straight line through the origin with slope 1.",
        safety="Pull steadily and never beyond the full scale of either balance, or the spring is damaged.",
        questions=[{"q": "Which balance shows the larger reading?",
                    "options": ["Both show the same", "The one the hand pulls", "The one on the support"],
                    "answer": 0, "why": "Action and reaction are equal in size, so the two readings are the same."},
                   {"q": "If the hand pulls twice as hard, the two readings",
                    "options": ["both double and stay equal", "stay the same", "become different"], "answer": 0,
                    "why": "The tension is the same all along, whatever its size."}],
        sources=[LABMAN9, NCERT9, SIM],
        check={"params": {"X": 0.02}, "reading": "B", "textbook": "third_law_T"},
    )


BUILDERS = (motion_track, distance_time_graph, friction_pull, friction_lubricant,
            archimedes_balance, solid_density, sucker_pressure, third_law)
