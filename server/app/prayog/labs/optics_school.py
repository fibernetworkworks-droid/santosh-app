"""Prayogshala lab pack: SCHOOL OPTICS - the NCERT Class 6-10 light practicals and activities.

Seven set-ups, all on the school's own apparatus (a lamp and a screen, a pinhole camera, a drawing board with a
ray box and pins, a glass slab, a concave mirror, a convex lens, a beaker of water). Four of them run on this
area's own kernels (`packs/optics_school.py`: shadowbox / pinhole / planemirror / slabray); three run on the
shared optics kernels (mirror / lens / slab) with the school's own procedure.

Every lab carries its NCERT check (the kernel's own measurement against the textbook formula, within 1 %).
"""
from __future__ import annotations

import math

from ..catalog import B, col, inst, knob, lab

DEG = math.pi / 180
R2D = 180 / math.pi
SCH = {"title": "Science / Curiosity, NCERT Classes VI-VIII: Light, Shadows and Reflections; Light"}
S10 = {"title": "Science, NCERT Class X (Light - Reflection and Refraction) + Laboratory Manual Science Class X"}
SIM = {"title": "Hoola Prayogshala kernel", "note": "readings come from the simulation code; checked against the NCERT formula in Hoola's tests"}
GRP = "Physics · Optics"


# ========================================================================================= shadows and straight lines
def shadow_bench() -> dict:
    return lab(
        id="school-shadow-bench", title="Shadows: how the size of a shadow changes", group=GRP, level="Class VI-VII",
        topic="Light, Shadows and Reflections", chapter="Light: Shadows and Reflection",
        aim="Light travels in straight lines: measure the shadow of an object on a screen and work out the object's height.",
        kernel="shadowbox", params={"h": 0.06, "s": 0.004}, autorun=True,
        camera={"pos": [0.45, 0.35, 1.1], "look": [0.45, 0.02, 0]}, floor=-0.2,
        bodies=[
            B("bench", "box", name="Bench", size=[1.3, 0.02, 0.2], pos=[0.5, -0.02, 0], color="wood", cut=False),
            B("lampbox", "box", name="Lamp house", info="A small clear lamp in a metal house: it acts as the source of light.",
              size=[0.08, 0.1, 0.08], pos=[-0.05, 0.04, 0], color="#2b2f36"),
            B("bulb", "sphere", name="Lamp", r=0.012, pos=[0, 0.05, 0], color="white"),
            B("obj", "box", name="Object (a card standing on the bench)", info="Its height is what you have to find.",
              size=[0.05, 0.06, 0.004], pos=[0.3, 0.03, 0], color="black",
              bind={"x": "p.a", "sy": {"var": "p.h", "k": 16.667}, "y": {"var": "p.h", "k": 0.5}}),
            B("scr", "plane", name="Screen", info="A white screen; the shadow falls on it.", size=[0.3, 0.3],
              pos=[0.9, 0.1, 0], rot=[0, 1.5708, 0], color="white", opacity=0.9, bind={"x": "p.D"}),
            B("shade", "box", name="Shadow", info="The dark patch where no light reaches.", size=[0.004, 0.18, 0.05],
              pos=[0.895, 0.09, 0], color="#1a1a1a", opacity=0.75, illustrative=True,
              bind={"x": "p.D", "sy": {"var": "shadow", "k": 5.556}, "y": {"var": "shadow", "k": 0.5}}),
            B("ruler", "scale", name="Screen scale (cm)", length=0.3, spacing=0.01, major=10, labels=True, label_step=10,
              tick=0.012, font=0.016, pos=[0.9, 0.0, 0.055], rot=[0, 1.5708, 0]),
            B("pipe", "cylinder", name="Straight pipe", info="Look at the lamp through it: a straight pipe shows the lamp, a bent one does not.",
              r=0.009, h=0.3, pos=[0.45, 0.2, 0.12], rot=[0, 0, 1.5708], color="#5f646b"),
            B("rays", "rays", name="Rays of light", var="rays", color="ray"),
        ],
        knobs=[knob("a", "Lamp to object", "a", 10, 60, 1, 30, "cm", 0.01, hint="Bring the object closer to the lamp: the shadow grows."),
               knob("D", "Lamp to screen", "D", 40, 110, 1, 90, "cm", 0.01),
               knob("h", "Take another object (true height hidden)", "h", 2, 12, 0.1, 6, "cm", 0.01, hidden=True)],
        instruments=[inst("sh", "readout", "Height of the shadow on the screen", "shadow", k=100, unit="cm", lc=0.1, digits=1),
                     inst("mg", "readout", "How many times bigger (D ÷ a)", "mag", digits=2),
                     inst("pp", "readout", "Lamp seen through the pipe (1 = yes)", "see", digits=0)],
        table={"columns": [col("a", "a (lamp → object)", "knob:a", "cm", 0.01, digits=1),
                           col("D", "D (lamp → screen)", "knob:D", "cm", 0.01, digits=1),
                           col("sh", "Shadow height", "inst:sh", "cm", 0.01, digits=2)],
               "calc": "shadow_h0", "rows_min": 3, "truth": "p.h", "result_k": 100, "result_unit": "cm", "result_digits": 2,
               "hint": "For each position of the object: measure the shadow on the screen scale and record the reading."},
        steps=["Line up the lamp, the object and the screen along the bench.",
               "Look at the lamp through the straight pipe, then through the bent one: light travels in straight lines.",
               "Measure the height of the shadow with the screen scale.",
               "Move the object to 3 or 4 more distances and measure each shadow.",
               "The object's height = shadow × a ÷ D."],
        theory="Light travels in straight lines, so an opaque object cuts out a cone of light and leaves a shadow. "
               "The rays that just graze the top of the object give similar triangles, so shadow ÷ object = D ÷ a. "
               "A lamp with a filament of some size also gives a faint border, the penumbra.",
        safety="In a real lab the lamp gets hot: switch it off before moving it, and never look into it from close by.",
        questions=[{"q": "The object is moved closer to the lamp. The shadow then?", "options": ["Gets bigger", "Gets smaller", "Does not change"],
                    "answer": 0, "why": "a gets smaller, so D ÷ a gets larger."},
                   {"q": "Why does a shadow have a sharp edge?", "options": ["Light travels in straight lines", "Light bends around the object", "The screen is white"],
                    "answer": 0, "why": "Rectilinear propagation: the edge is where the grazing ray lands."}],
        sources=[SCH, SIM],
        check={"params": {"a": 0.3, "D": 0.9}, "reading": "shadow", "textbook": "shadow_h"},
    )


# ========================================================================================= pinhole camera
def pinhole_camera() -> dict:
    return lab(
        id="school-pinhole-camera", title="Pinhole camera: the image of a lit object", group=GRP, level="Class VI-VII",
        topic="Light, Shadows and Reflections", chapter="Light: Shadows and Reflection",
        aim="Make a pinhole camera and measure the inverted image: image ÷ object = v ÷ u.",
        kernel="pinhole", params={"h": 0.09}, autorun=True,
        camera={"pos": [0.3, 0.25, 0.8], "look": [0.1, 0.0, 0]}, floor=-0.2,
        bodies=[
            B("bench", "box", name="Bench", size=[1.2, 0.02, 0.2], pos=[0.3, -0.02, 0], color="wood", cut=False),
            B("boxb", "box", name="Pinhole camera", info="A card box with a pinhole in front and tracing paper at the back.",
              size=[0.16, 0.12, 0.12], pos=[0.08, 0.06, 0], color="#8a5a32", opacity=0.55,
              bind={"sx": {"var": "p.v", "k": 6.667}, "x": {"var": "p.v", "k": 0.5}}),
            B("hole", "cylinder", name="Pinhole", info="A tiny hole made with a pin: only a narrow pencil of light gets in.",
              r=0.002, h=0.004, pos=[0, 0.06, 0], rot=[0, 0, 1.5708], color="black"),
            B("tp", "plane", name="Tracing paper screen", size=[0.12, 0.12], pos=[0.15, 0.06, 0], rot=[0, 1.5708, 0],
              color="white", opacity=0.75, bind={"x": "p.v"}),
            B("objc", "arrow", name="Lit object (a candle)", info="Its height is what you have to find.", dir=[0, 1, 0],
              len=0.09, head=0.016, pos=[-0.6, 0.0, 0], color="red", bind={"x": {"var": "p.u", "k": -1}, "len": "p.h"}),
            B("img", "arrow", name="Image on the screen", info="Upside down, because the rays cross at the hole.",
              dir=[0, -1, 0], len=0.02, head=0.008, pos=[0.15, 0.06, 0], color="blue",
              bind={"x": "p.v", "len": "img_h"}),
            B("ruler", "scale", name="Screen scale (cm)", length=0.1, spacing=0.01, major=5, labels=True, label_step=5,
              tick=0.01, font=0.014, pos=[0.15, 0.0, 0.062], rot=[0, 1.5708, 0]),
            B("rays", "rays", name="Rays of light", var="rays", color="ray"),
        ],
        knobs=[knob("u", "Object to pinhole", "u", 30, 120, 1, 60, "cm", 0.01),
               knob("v", "Length of the box (pinhole to screen)", "v", 5, 30, 0.5, 15, "cm", 0.01),
               knob("h", "Take another object (true height hidden)", "h", 4, 20, 0.5, 9, "cm", 0.01, hidden=True)],
        instruments=[inst("hi", "readout", "Height of the image", "img_h", k=100, unit="cm", lc=0.01, digits=2),
                     inst("bl", "readout", "Blur circle of the hole", "blur", k=1000, unit="mm", digits=2),
                     inst("mg", "readout", "Magnification (v ÷ u)", "mag", digits=3)],
        table={"columns": [col("u", "u (object → hole)", "knob:u", "cm", 0.01, digits=1),
                           col("v", "v (hole → screen)", "knob:v", "cm", 0.01, digits=1),
                           col("hi", "Image height", "inst:hi", "cm", 0.01, digits=2)],
               "calc": "pinhole_h0", "rows_min": 3, "truth": "p.h", "result_k": 100, "result_unit": "cm", "result_digits": 2},
        steps=["Point the pinhole at the lit object and look at the tracing paper: the image is upside down.",
               "Measure the height of the image on the screen scale.", "Change u and v and measure again.",
               "Object height = image × u ÷ v."],
        theory="Only the rays that pass through the pinhole reach the screen, and each one goes straight on, so the top "
               "of the object lands at the bottom of the screen: the image is inverted and image ÷ object = v ÷ u. "
               "A bigger hole lets in more light but spreads every point into a small circle, so the picture is brighter and blurred.",
        questions=[{"q": "Why is the image of a pinhole camera upside down?", "options": ["The rays cross at the hole", "The paper is thin", "Light bends at the hole"],
                    "answer": 0, "why": "Straight rays from the top of the object go on to the bottom of the screen."},
                   {"q": "The box is made longer (v larger). The image then?", "options": ["Gets bigger and dimmer", "Gets smaller", "Does not change"],
                    "answer": 0, "why": "Image height = h v ÷ u, and the same light is spread over a larger area."}],
        sources=[SCH, SIM],
        check={"params": {"u": 0.6, "v": 0.15}, "reading": "img_h", "textbook": "pinhole_h"},
    )


# ========================================================================================= plane mirror
def plane_mirror() -> dict:
    return lab(
        id="school-plane-mirror", title="Plane mirror: the law of reflection and the image", group=GRP,
        level="Class VII-VIII", topic="Light", chapter="Light: Shadows and Reflection",
        aim="Send a narrow beam onto a plane mirror and measure i and r; find where the image is, and count the images in two inclined mirrors.",
        kernel="planemirror", params={"sep": 0.02}, autorun=True,
        camera={"pos": [0.0, 0.3, 0.42], "look": [0.0, 0.0, 0]}, floor=-0.1,
        bodies=[
            B("paper", "box", name="Drawing board with a sheet of paper", size=[0.5, 0.004, 0.36], pos=[0, -0.004, 0],
              color="white", cut=False),
            B("mirror", "box", name="Plane mirror", info="A strip mirror standing on its edge, its silvered face along the ruled line.",
              size=[0.16, 0.05, 0.004], pos=[0, 0.025, 0], color="#c8d4e0"),
            B("raybox", "box", name="Ray box", info="A torch with a comb in front: it gives one narrow beam of light.",
              size=[0.07, 0.05, 0.05], pos=[-0.11, 0.025, 0.11], color="#2b2f36"),
            B("prot", "torus", name="Protractor", info="Read the angle of incidence and the angle of reflection on it.",
              r=0.06, tube=0.001, arc=3.1416, pos=[0, 0.002, 0], rot=[-1.5708, 0, 0], color="ink"),
            B("normal", "box", name="The normal", size=[0.001, 0.001, 0.09], pos=[0, 0.002, 0.045], color="black"),
            B("pin1", "cylinder", name="Object pin", info="An optical pin standing in front of the mirror.", r=0.0015,
              h=0.05, pos=[0, 0.025, 0.09], color="steel", bind={"z": "p.d"}),
            B("pin2", "cylinder", name="Image", info="Where the image appears: as far behind the mirror as the pin is in front.",
              r=0.0015, h=0.05, pos=[0, 0.025, -0.09], color="red", opacity=0.5, illustrative=True,
              bind={"z": {"var": "img", "k": -1}}),
            B("mir2", "box", name="Second mirror", info="Stand it against the first at an angle and count the images.",
              size=[0.16, 0.05, 0.004], pos=[0.06, 0.025, -0.06], rot=[0, 1.0472, 0], color="#c8d4e0",
              bind={"ry": "p.theta"}),
            B("rays", "rays", name="The beam", var="rays", color="ray", virtual="ink"),
        ],
        knobs=[knob("i", "Angle of incidence i", "i", 10, 80, 1, 30, "°", DEG),
               knob("d", "Pin in front of the mirror", "d", 4, 14, 0.5, 9, "cm", 0.01),
               knob("theta", "Angle between the two mirrors", "theta", 30, 120, 1, 60, "°", DEG,
                    hint="Use an angle that divides 360: 36, 45, 60, 72, 90 or 120 degrees.")],
        instruments=[inst("r", "readout", "Angle of reflection r (protractor)", "r", k=R2D, unit="°", lc=0.5, digits=1),
                     inst("iv", "readout", "Image behind the mirror", "img", k=100, unit="cm", lc=0.1, digits=1),
                     inst("ni", "readout", "Number of images in the two mirrors", "N", digits=0)],
        table={"columns": [col("ai", "i", "knob:i", "°", DEG, digits=1), col("ar", "r", "inst:r", "°", DEG, digits=1)],
               "calc": "mirror_law_r", "rows_min": 4, "result_digits": 3,
               "hint": "For each angle of incidence read the reflected beam on the protractor and record it."},
        steps=["Draw the mirror line and the normal on the paper; stand the mirror on the line.",
               "Set the ray box so that the beam strikes the pole at i = 30°; read r on the protractor.",
               "Repeat for i = 40°, 50°, 60° and 70°: r equals i every time.",
               "Put a pin in front of the mirror and locate the image: it is as far behind as the pin is in front.",
               "Stand the second mirror at 60° and count the images: N = 360 ÷ θ − 1."],
        theory="The incident ray, the reflected ray and the normal at the point of incidence lie in one plane, and the "
               "angle of reflection equals the angle of incidence. The reflected rays from a point object diverge, so "
               "they only appear to come from a point as far behind the mirror as the object is in front: the image is "
               "virtual, erect, the same size, and left and right are interchanged. Two mirrors at θ give 360 ÷ θ − 1 images.",
        questions=[{"q": "A ray falls along the normal (i = 0). The angle of reflection is?", "options": ["0°", "90°", "180°"],
                    "answer": 0, "why": "r = i, so the ray comes straight back."},
                   {"q": "The image in a plane mirror is?", "options": ["Virtual, erect, the same size", "Real and inverted", "Real and smaller"],
                    "answer": 0, "why": "The reflected rays only appear to meet behind the mirror."},
                   {"q": "Two mirrors at 60° give how many images?", "options": ["5", "3", "6"], "answer": 0,
                    "why": "360 ÷ 60 − 1 = 5."}],
        sources=[SCH, SIM],
        check={"params": {"i": 0.5236}, "reading": "r", "textbook": "planemirror_r"},
    )


# ========================================================================================= glass slab
def glass_slab_ray() -> dict:
    return lab(
        id="school-glass-slab-ray", title="Glass slab: the path of a ray and its lateral shift", group=GRP,
        level="Class X", topic="Light - Reflection and Refraction", chapter="Light: Reflection and Refraction (Class 10)",
        aim="Trace a ray through a rectangular slab with pins: measure i, r and the lateral displacement, and find n.",
        kernel="slabray", params={"t": 0.05, "n": 1.5168}, autorun=True,
        camera={"pos": [0.0, 0.26, 0.34], "look": [0.0, 0.0, 0]}, floor=-0.1,
        bodies=[
            B("paper", "box", name="Drawing board with a sheet of paper", size=[0.42, 0.004, 0.3], pos=[0, -0.004, 0],
              color="white", cut=False),
            B("slab", "box", name="Rectangular glass slab", info="Its two long faces are flat and parallel.",
              size=[0.1, 0.018, 0.05], pos=[0, 0.009, 0], color="glass", opacity=0.35,
              bind={"sz": {"var": "p.t", "k": 20}}),
            B("normal1", "box", name="The normal at the first face", size=[0.001, 0.001, 0.07], pos=[0, 0.002, 0.06],
              color="black"),
            B("normal2", "box", size=[0.001, 0.001, 0.07], pos=[0, 0.002, -0.06], color="black"),
            B("prot", "torus", name="Protractor", info="Measure i, r and e on it.", r=0.055, tube=0.001, arc=3.1416,
              pos=[0, 0.002, 0.025], rot=[-1.5708, 0, 0], color="ink"),
            B("pinA", "cylinder", name="Pin P1", info="The two pins in front fix the incident ray.", r=0.0012, h=0.04,
              pos=[-0.05, 0.02, 0.085], color="steel"),
            B("pinB", "cylinder", name="Pin P2", r=0.0012, h=0.04, pos=[-0.028, 0.02, 0.048], color="steel"),
            B("pinC", "cylinder", name="Pin P3", info="The two pins behind are fixed in line with the images of the first two.",
              r=0.0012, h=0.04, pos=[0.03, 0.02, -0.05], color="red"),
            B("pinD", "cylinder", name="Pin P4", r=0.0012, h=0.04, pos=[0.052, 0.02, -0.087], color="red"),
            B("rays", "rays", name="The ray", var="rays", color="ray", virtual="ink"),
        ],
        knobs=[knob("i", "Angle of incidence i", "i", 20, 70, 1, 30, "°", DEG),
               knob("t", "Thickness of the slab", "t", 2, 8, 0.1, 5, "cm", 0.01),
               knob("n", "Take another slab (n hidden)", "n", 1.3, 1.8, 0.0001, 1.5168, hidden=True)],
        instruments=[inst("r", "readout", "Angle of refraction r", "r", k=R2D, unit="°", lc=0.5, digits=1),
                     inst("e", "readout", "Angle of emergence e", "e", k=R2D, unit="°", lc=0.5, digits=1),
                     inst("sx", "readout", "Lateral displacement", "shift", k=1000, unit="mm", lc=0.1, digits=1)],
        table={"columns": [col("ai", "i", "knob:i", "°", DEG, digits=1), col("ar", "r", "inst:r", "°", DEG, digits=1)],
               "calc": "slabray_n", "rows_min": 4, "truth": "p.n", "result_digits": 3,
               "hint": "For each angle of incidence read the angle of refraction and record both."},
        steps=["Draw the outline of the slab and the normal at the first face.",
               "Fix pins P1 and P2 on the incident ray at i = 30°.",
               "Look from the other side and fix P3 and P4 in line with the images of P1 and P2.",
               "Join the points: measure r, e and the perpendicular distance between the incident and emergent rays.",
               "Repeat for i = 40°, 50° and 60°; n = sin i ÷ sin r."],
        theory="At the first face the ray bends towards the normal (air to glass, n = sin i ÷ sin r) and at the second "
               "face it bends away by the same amount, so the emergent ray is parallel to the incident ray: e = i. "
               "The ray is only shifted sideways, by t sin(i − r) ÷ cos r.",
        safety="Glass slabs chip easily: hold one by its edges and keep it away from the edge of the table.",
        questions=[{"q": "The emergent ray from a rectangular slab is?", "options": ["Parallel to the incident ray", "Along the normal", "Bent towards the normal"],
                    "answer": 0, "why": "The two faces are parallel, so the two bendings cancel."},
                   {"q": "A thicker slab, same angle of incidence. The lateral shift?", "options": ["Increases", "Decreases", "Stays the same"],
                    "answer": 0, "why": "The shift is proportional to the thickness t."}],
        sources=[S10, SIM],
        check={"params": {"i": 0.5236}, "reading": "r", "textbook": "slabray_r"},
    )


# ========================================================================================= concave mirror, class 10
def mirror_images() -> dict:
    return lab(
        id="school-concave-mirror-images", title="Concave mirror: where the image is for each position", group=GRP,
        level="Class X", topic="Light - Reflection and Refraction", chapter="Light: Reflection and Refraction (Class 10)",
        aim="Find f from a distant object, then put the object beyond C, just beyond C, between C and F and inside F.",
        kernel="mirror", params={"h": 0.02}, autorun=True,
        camera={"pos": [0.35, 0.2, 0.9], "look": [0.3, 0.0, 0]}, floor=-0.15,
        bodies=[
            B("bench", "box", name="Bench", size=[1.2, 0.02, 0.18], pos=[0.45, -0.02, 0], color="wood", cut=False),
            B("mir", "dish", name="Concave mirror (R = 30 cm)", info="So f = R ÷ 2 = 15 cm.", R=0.3, r=0.05,
              pos=[0, 0.08, 0], color="#c8d4e0"),
            B("stand", "cylinder", name="Mirror holder", r=0.004, h=0.08, pos=[0, 0.04, 0], color="steel"),
            B("obj", "arrow", name="Object (a short lit candle)", dir=[0, 1, 0], len=0.02, head=0.008, pos=[0.45, 0.08, 0],
              color="red", bind={"x": "p.u", "len": "p.h"}),
            B("img", "arrow", name="Image", info="Real and inverted when it falls on the screen.", dir=[0, 1, 0],
              len=0.02, head=0.008, pos=[0.3, 0.08, 0], color="blue", bind={"x": "img_x", "len": "img_h"}),
            B("scr", "plane", name="Screen", size=[0.12, 0.12], pos=[0.3, 0.08, 0], rot=[0, 1.5708, 0], color="white",
              opacity=0.85, bind={"x": "p.scr"}),
            B("ruler", "scale", name="Bench scale (cm)", length=1.0, spacing=0.01, major=10, labels=True, label_step=10,
              tick=0.01, font=0.016, pos=[0, 0.0, 0.09], rot=[-1.5708, 0, 0]),
            B("rays", "rays", name="Rays", var="rays", color="ray"),
        ],
        knobs=[knob("u", "Object distance u", "u", 10, 90, 0.5, 45, "cm", 0.01),
               knob("scr", "Screen distance", "scr", 5, 100, 0.5, 22.5, "cm", 0.01),
               knob("conv", "Turn the mirror round (0 = concave, 1 = convex)", "convex", 0, 1, 1, 0,
                    hint="The two sides of a shining spoon: the inner side is concave, the outer side convex.")],
        instruments=[inst("sh", "meter", "Sharpness of the image on the screen", "sharp", range=[0, 1], digits=2),
                     inst("v", "readout", "Image distance v", "img_x", k=100, unit="cm", digits=1),
                     inst("re", "readout", "Real image (1 = yes)", "real", digits=0)],
        table={"columns": [col("u", "u", "knob:u", "cm", 0.01, digits=1),
                           col("v", "v (sharp screen)", "knob:scr", "cm", 0.01, digits=1)],
               "calc": "mirror_f", "rows_min": 3, "result_k": 100, "result_unit": "cm", "result_digits": 1},
        steps=["Hold the mirror facing a distant window and catch the image on the screen: that distance is f.",
               "Put the candle beyond C (u > 30 cm) and slide the screen until the image is sharp.",
               "Repeat just beyond C and between C and F: note where the image is and how big it is.",
               "Bring the candle inside F (10 cm): no image forms on the screen, it is virtual and erect.",
               "f = uv ÷ (u + v) for each pair; take the mean."],
        theory="For a concave mirror 1 ÷ v + 1 ÷ u = 1 ÷ f (both distances taken positive from the pole for a real "
               "image), and f = R ÷ 2. Beyond C the image is between F and C, inverted and smaller; at C it is at C "
               "and the same size; between C and F it is beyond C and larger; inside F it is virtual, erect and larger. "
               "Rays from a very distant object arrive parallel, so they meet at the focus and the image distance is f.",
        questions=[{"q": "The object is at the centre of curvature. The image is?", "options": ["At C, inverted, same size", "At F", "Virtual"],
                    "answer": 0, "why": "u = 2f gives v = 2f."},
                   {"q": "The image of a distant object by a concave mirror forms?", "options": ["At the focus", "At the pole", "At the centre of curvature"],
                    "answer": 0, "why": "Parallel rays converge to F."},
                   {"q": "The outer (convex) side of a spoon always gives?", "options": ["A small erect image", "An inverted image", "No image"],
                    "answer": 0, "why": "A convex mirror always gives a virtual, erect, diminished image."}],
        sources=[S10, SIM],
        check={"params": {"u": 0.45}, "reading": "v", "textbook": "mirror_v"},
    )


# ========================================================================================= convex lens, class 10
def lens_images() -> dict:
    return lab(
        id="school-convex-lens-images", title="Convex lens: the image for each position of the object", group=GRP,
        level="Class X", topic="Light - Reflection and Refraction", chapter="Light: Reflection and Refraction (Class 10)",
        aim="Find f from a distant object, then place the object beyond 2F, at 2F, between F and 2F and inside F.",
        kernel="lens", params={"h": 0.02}, autorun=True,
        camera={"pos": [0.0, 0.22, 1.0], "look": [0.0, 0.0, 0]}, floor=-0.15,
        bodies=[
            B("bench", "box", name="Bench", size=[1.5, 0.02, 0.18], pos=[0, -0.02, 0], color="wood", cut=False),
            B("lens", "lens", name="Convex lens (f ≈ 20 cm)", info="Glass n = 1.5, both surfaces R = 20 cm.", r=0.025,
              thick=0.008, pos=[0, 0.1, 0], color="glass", opacity=0.45),
            B("holder", "cylinder", name="Lens holder", r=0.004, h=0.075, pos=[0, 0.037, 0], color="steel"),
            B("obj", "arrow", name="Object (a short lit candle)", dir=[0, 1, 0], len=0.02, head=0.008, pos=[-0.4, 0.1, 0],
              color="red", bind={"x": {"var": "p.u", "k": -1}, "len": "p.h"}),
            B("img", "arrow", name="Image", dir=[0, 1, 0], len=0.02, head=0.008, pos=[0.4, 0.1, 0], color="blue",
              bind={"x": "img_x", "len": "img_h"}),
            B("scr", "plane", name="Screen", size=[0.12, 0.12], pos=[0.4, 0.1, 0], rot=[0, 1.5708, 0], color="white",
              opacity=0.85, bind={"x": "p.scr"}),
            B("ruler", "scale", name="Bench scale (cm)", length=1.4, spacing=0.01, major=10, labels=True, label_step=10,
              tick=0.01, font=0.016, pos=[-0.7, 0.0, 0.09], rot=[-1.5708, 0, 0]),
            B("rays", "rays", name="Rays", var="rays", color="ray"),
        ],
        knobs=[knob("u", "Object distance u", "u", 12, 90, 0.5, 40, "cm", 0.01),
               knob("scr", "Screen distance", "scr", 5, 100, 0.5, 40, "cm", 0.01)],
        instruments=[inst("sh", "meter", "Sharpness of the image on the screen", "sharp", range=[0, 1], digits=2),
                     inst("v", "readout", "Image distance v", "img_x", k=100, unit="cm", digits=1),
                     inst("re", "readout", "Real image (1 = yes)", "real", digits=0)],
        table={"columns": [col("u", "u", "knob:u", "cm", 0.01, digits=1),
                           col("v", "v (sharp screen)", "knob:scr", "cm", 0.01, digits=1)],
               "calc": "lens_f", "rows_min": 3, "result_k": 100, "result_unit": "cm", "result_digits": 1},
        steps=["Catch the image of a distant window on the screen: that distance is f (about 20 cm).",
               "Put the candle beyond 2F (u > 40 cm) and slide the screen until the image is sharp.",
               "Repeat at 2F (40 cm) and between F and 2F (30 cm).",
               "Bring the candle inside F (15 cm): no image on the screen, it is virtual, erect and larger.",
               "f = uv ÷ (u + v); take the mean."],
        theory="For a thin convex lens 1 ÷ v + 1 ÷ u = 1 ÷ f with u and v measured from the lens (real image, both "
               "positive). Beyond 2F the image is between F and 2F, inverted and smaller; at 2F it is at 2F and the "
               "same size; between F and 2F it is beyond 2F and larger; at F no image forms; inside F the image is "
               "virtual, erect and larger. Parallel rays from a distant object meet at F, so that image distance is f.",
        questions=[{"q": "The object is at 2F of a convex lens. The image is?", "options": ["At 2F, inverted, same size", "At F", "Virtual"],
                    "answer": 0, "why": "u = 2f gives v = 2f."},
                   {"q": "No image can be caught on the screen when the object is?", "options": ["Inside F", "At 2F", "Beyond 2F"],
                    "answer": 0, "why": "The emerging rays diverge: the image is virtual."}],
        sources=[S10, SIM],
        check={"params": {"u": 0.4}, "reading": "v", "textbook": "lens_v"},
    )


# ========================================================================================= refraction in water
def water_refraction() -> dict:
    return lab(
        id="school-water-refraction", title="A coin in water looks raised and a pencil looks bent", group=GRP,
        level="Class X", topic="Light - Reflection and Refraction", chapter="Light: Reflection and Refraction (Class 10)",
        aim="Look straight down at a coin under water: measure the real and the apparent depth and find n of water.",
        kernel="slab", params={"t": 0.08, "n": 1.333}, autorun=True,
        camera={"pos": [0.16, 0.12, 0.3], "look": [0.0, -0.02, 0]}, floor=-0.14,
        bodies=[
            B("tank", "box", name="Glass trough", info="A rectangular glass trough with water in it.", size=[0.18, 0.1, 0.1],
              pos=[0, -0.05, 0], color="glass", opacity=0.2),
            B("water", "box", name="Water", size=[0.17, 0.08, 0.095], pos=[0, 0, 0], color="water", opacity=0.35,
              bind={"sy": {"var": "p.t", "k": 12.5}, "y": {"var": "p.t", "k": -0.5}}),
            B("coin", "cylinder", name="Coin at the bottom", info="This is the mark you look down at.", r=0.011,
              h=0.002, pos=[0, -0.08, 0], color="brass", bind={"y": {"var": "p.t", "k": -1}}),
            B("ghost", "cylinder", name="Where the coin appears", info="Seen from straight above, it looks raised.",
              r=0.011, h=0.002, pos=[0, -0.06, 0], color="red", opacity=0.5, illustrative=True,
              bind={"y": {"var": "app", "k": -1}}),
            B("pencil", "cylinder", name="Pencil", info="Standing in the water, it looks bent at the surface.", r=0.004,
              h=0.14, pos=[0.055, 0.0, 0.03], rot=[0.35, 0, 0], color="#e8b024"),
            B("micro", "cylinder", name="Travelling microscope", info="Focus on the coin, then on the surface: the difference is the apparent depth.",
              r=0.012, h=0.07, pos=[0, 0.09, 0], color="#2b2f36"),
            B("rays", "rays", name="Rays", var="rays", color="ray"),
        ],
        knobs=[knob("t", "Depth of the water", "t", 4, 12, 0.1, 8, "cm", 0.01),
               knob("n", "Liquid (water 1.33, oil 1.47, glycerine 1.47)", "n", 1.33, 1.5, 0.001, 1.333, hidden=True)],
        instruments=[inst("ap", "readout", "Apparent depth (microscope)", "app", k=100, unit="cm", lc=0.01, digits=2),
                     inst("ri", "readout", "How much the coin rose", "shift", k=100, unit="cm", lc=0.01, digits=2)],
        table={"columns": [col("t", "Real depth", "knob:t", "cm", 0.01, digits=2),
                           col("a", "Apparent depth", "inst:ap", "cm", 0.01, digits=2)],
               "calc": "slab_n", "rows_min": 2, "truth": "p.n", "result_digits": 3},
        steps=["Fill the trough to 8 cm and drop the coin in.", "Focus the microscope on the coin and read the apparent depth.",
               "Change the depth of the water and read again.", "n = real depth ÷ apparent depth."],
        theory="A ray from the coin bends away from the normal as it leaves the water, so to an eye straight above it "
               "seems to come from a point higher up: apparent depth = real depth ÷ n. The same bending at the surface "
               "makes a pencil standing in water look broken.",
        questions=[{"q": "A pond 2 m deep, seen from above, appears?", "options": ["About 1.5 m deep", "About 2.7 m deep", "Exactly 2 m deep"],
                    "answer": 0, "why": "2 ÷ 1.33 = 1.5 m."},
                   {"q": "Why does a pencil in a glass of water look bent?", "options": ["Light refracts at the surface", "The glass is curved", "Water absorbs light"],
                    "answer": 0, "why": "Rays from the part under water change direction when they leave it."}],
        sources=[S10, SIM],
        check={"params": {}, "reading": "app", "textbook": "slab_app"},
    )


BUILDERS = (shadow_bench, pinhole_camera, plane_mirror, glass_slab_ray, mirror_images, lens_images, water_refraction)
