"""Lab pack `engine_ug`: twelve set-ups built on the three engines of `packs/engine_ug.py`.

  two-element ray tracer      convex-mirror-using-lens, concave-lens-using-convex (rig `convex-mirror-using-lens`),
                              liquid-lens-plane-mirror, liquid-concave-mirror (rig `liquid-lens-plane-mirror`)
  the same apparatus, shared  slab-lateral-deviation (rig `school-glass-slab-ray`, kernel slabray) and
                              image-nature-candle-screen (rig `school-convex-lens-images`, kernel lens)
  AC phasor engine            inductor-impedance (rig `inductor-impedance`), ac-mains-frequency-sonometer
                              (rig `ac-mains-frequency-sonometer`)
  clocked logic kernel        flip-flops-nand, jk-master-slave, counter-4bit, shift-register (rig `flip-flops-nand`)

Every lab carries its check: the kernel's own reading against the textbook formula, within 1 %.
"""
from __future__ import annotations

import copy
import math
from typing import Any

from ..catalog import B, S12, SIM, col, inst, knob, lab

DEG = math.pi / 180
CH_OPT = "Ray Optics and Optical Instruments"
CH_AC = "Alternating Current"
CH_DIG = "Digital electronics, microprocessors and microcontrollers"
LAB12 = {"title": "NCERT Laboratory Manual Physics Class XII (Section B: Optics; Section A: Electricity)"}
CBSE = {"title": "CBSE Senior Secondary Curriculum 2025-26, Physics (Classes XI-XII), practical syllabus"}
SCHOTT = {"title": "SCHOTT optical glass data sheet N-BK7: nd = 1.5168 (587.6 nm); refractiveindex.info"}
DU = {"title": "B.Sc. (Honours) Physics, Learning Outcomes based Curriculum Framework, University of Delhi: "
               "C-VII Digital Systems laboratory list"}
MANO = {"title": "M. Morris Mano, Digital Design (flip-flops, counters and registers from NAND gates)"}
TTL = {"title": "Texas Instruments SN5400/SN7400 quadruple 2-input positive-NAND gate datasheet (SDLS025)",
       "note": "5 V supply, V_IH 2 V, V_IL 0.8 V; SN7410 triple 3-input NAND, SN7476 dual J-K, SN7474 dual D-type"}
GRP_O = "Physics · Optics"
GRP_E = "Physics · Electricity"
GRP_D = "Physics · Electronics"


def _bench(x0: float = -0.1, x1: float = 0.8) -> list[dict]:
    return [B("bench", "box", name="Optical bench", info="An iron bed with a scale in centimetres.",
              size=[x1 - x0, 0.02, 0.06], pos=[(x0 + x1) / 2, -0.04, 0], color="#2b2f36", cut=False)]


# ===================================================================================== two-element ray tracer
def convex_mirror_using_lens() -> dict:
    return lab(
        id="convex-mirror-using-lens", rig="convex-mirror-using-lens",
        title="Convex mirror: its focal length using a convex lens", group=GRP_O, level="Class XII",
        topic=CH_OPT, chapter=CH_OPT,
        aim="Find the focal length of a convex mirror with the help of a convex lens: slide the mirror in the lens's "
            "converging beam until a pin and its own image coincide.",
        kernel="eng_lensmirror", params={"h": 0.003}, autorun=True,
        camera={"pos": [0.2, 0.25, 0.9], "look": [0.2, 0.0, 0]}, floor=-0.1,
        bodies=[*_bench(),
                B("lens", "lens", name="Convex lens", info="Glass, n = 1.5168, both faces R = 15 cm.", r=0.025,
                  thick=0.008, pos=[0, 0.0, 0], color="glass", opacity=0.45),
                B("pin", "arrow", name="Pin (the object)", dir=[0, 1, 0], len=0.03, head=0.008, pos=[0, 0, 0],
                  color="red", bind={"x": {"var": "p.u", "k": -1}}),
                B("mir", "dish", name="Convex mirror", info="Its radius of curvature is what you find.", R=0.2, r=0.03,
                  convex=1, pos=[0, 0, 0], rot=[0, 1.5708, 0], color="steel", bind={"x": "p.a"}),
                B("rays", "rays", name="Rays", var="rays", color="ray")],
        knobs=[knob("u", "Pin to lens, u", "u", 22, 40, 0.5, 30, "cm", 0.01),
               knob("scr", "Screen position (mirror removed)", "scr", 10, 45, 0.5, 28, "cm", 0.01),
               knob("a", "Mirror to lens", "a", 3, 30, 0.1, 8, "cm", 0.01),
               knob("mir", "Mirror in the beam (1) or removed (0)", "mir", 0, 1, 1, 0),
               knob("Rm", "Take another mirror (R hidden)", "Rm", 12, 24, 0.1, 20, "cm", 0.01, hidden=True)],
        instruments=[inst("sh", "meter", "Sharpness of the image on the screen", "sharp", range=[0, 1], digits=2),
                     inst("vl", "readout", "Image by the lens alone, v", "v_lens", k=100, unit="cm", lc=0.1, digits=1),
                     inst("gap", "readout", "Gap between the pin and its image", "coin", k=1000, unit="mm", lc=0.1,
                          digits=1)],
        table={"columns": [col("v", "v (lens alone)", "inst:vl", "cm", 0.01, digits=1),
                           col("a", "Mirror position a", "knob:a", "cm", 0.01, digits=1)],
               "calc": "eng_lm_f", "rows_min": 3, "result_k": 100, "result_unit": "cm", "result_digits": 1},
        steps=["Remove the mirror. Put the pin on the bench and slide the screen until its image is sharp: this gives v.",
               "Put the convex mirror between the lens and that image, with its pole on the axis.",
               "Slide the mirror until the pin and its own image are side by side with no parallax.",
               "The rays then meet the mirror along its radius: its centre of curvature is where the lens image was.",
               "R = v minus the mirror position a, and f = R / 2. Repeat for three pin distances."],
        theory="A convex lens makes a real image I of the pin. A convex mirror placed in the converging beam, before "
               "I, reflects the rays. When the beam is aimed at the mirror's centre of curvature C, every ray meets "
               "the mirror along a radius and returns along its own path: the pin and its image coincide. That puts C "
               "at I, so R = v - a (a is the mirror's distance from the lens) and f = R/2. A convex mirror alone "
               "cannot form a real image of a real object, which is why the lens is needed.",
        safety="Keep the bench clear of loose paper; the pin and the mirror edge are sharp.",
        tour=[{"say": "A convex lens, a pin on the left and a convex mirror on the right."},
              {"set": {"mir": 1, "a": 8.4}, "say": "With the mirror at the right distance the beam returns on itself."}],
        questions=[{"q": "At the position where the pin and its image coincide, the rays strike the mirror",
                    "options": ["along the radius, normally", "at 45 degrees", "parallel to the axis"], "answer": 0,
                    "why": "Only rays along a radius retrace their path, so the image falls on the object."},
                   {"q": "Why can a convex mirror not be used alone to find its focal length?",
                    "options": ["Its image of a real object is always virtual", "It has no focus",
                                "It is too small"], "answer": 0,
                    "why": "A real object always gives a virtual, diminished image behind a convex mirror."}],
        sources=[LAB12, SCHOTT, SIM],
        check={"params": {}, "reading": "f_est", "textbook": "eng_lensmirror_f"},
    )


def concave_lens_using_convex() -> dict:
    return lab(
        id="concave-lens-using-convex", rig="convex-mirror-using-lens",
        title="Concave lens: its focal length using a convex lens", group=GRP_O, level="Class XII",
        topic=CH_OPT, chapter=CH_OPT,
        aim="Find the focal length of a concave lens by placing it in the converging beam of a convex lens: the "
            "real image of the first lens is a virtual object for the second.",
        kernel="eng_twolens", params={"h": 0.003}, autorun=True,
        camera={"pos": [0.25, 0.25, 0.95], "look": [0.25, 0.0, 0]}, floor=-0.1,
        bodies=[*_bench(-0.1, 0.9),
                B("lens", "lens", name="Convex lens", info="Glass, n = 1.5168, both faces R = 15 cm.", r=0.025,
                  thick=0.008, pos=[0, 0.0, 0], color="glass", opacity=0.45),
                B("pin", "arrow", name="Pin (the object)", dir=[0, 1, 0], len=0.03, head=0.008, pos=[0, 0, 0],
                  color="red", bind={"x": {"var": "p.u", "k": -1}}),
                B("l2", "lens", name="Concave lens", info="Glass, both faces R = 30 cm; its focal length is hidden.",
                  r=0.025, thick=0.008, pos=[0, 0.0, 0], color="glass", opacity=0.45, bind={"x": "p.a"}),
                B("scr", "plane", name="Screen", size=[0.1, 0.1], pos=[0, 0, 0], rot=[0, 1.5708, 0], color="white",
                  opacity=0.8, bind={"x": "p.scr"}),
                B("rays", "rays", name="Rays", var="rays", color="ray")],
        knobs=[knob("u", "Pin to convex lens, u", "u", 22, 40, 0.5, 30, "cm", 0.01),
               knob("a", "Concave lens to convex lens", "a", 6, 24, 0.1, 13, "cm", 0.01),
               knob("scr", "Screen position", "scr", 10, 90, 0.1, 45, "cm", 0.01),
               knob("mir", "Concave lens in the beam (1) or removed (0)", "mir", 0, 1, 1, 0),
               knob("R2", "Take another concave lens (R hidden)", "R2", 20, 45, 0.5, 30, "cm", 0.01, hidden=True)],
        instruments=[inst("sh", "meter", "Sharpness of the image on the screen", "sharp", range=[0, 1], digits=2),
                     inst("v1", "readout", "Image by the convex lens alone, v1", "v1", k=100, unit="cm", lc=0.1,
                          digits=1),
                     inst("xi", "readout", "Final image position", "img_x", k=100, unit="cm", lc=0.1, digits=1)],
        table={"columns": [col("v1", "v1 (convex lens alone)", "inst:v1", "cm", 0.01, digits=1),
                           col("a", "Concave lens position a", "knob:a", "cm", 0.01, digits=1),
                           col("xi", "Final image position", "inst:xi", "cm", 0.01, digits=1)],
               "calc": "eng_tl_f", "rows_min": 3, "result_k": 100, "result_unit": "cm", "result_digits": 1},
        steps=["With the concave lens removed, find the sharp image I of the pin on the screen: its distance is v1.",
               "Put the concave lens between the convex lens and I, a distance a from the convex lens.",
               "The screen now needs to go further out. Slide it until the new image is sharp.",
               "For the concave lens u2 = v1 - a (a virtual object, on the far side) and v2 = new image - a.",
               "f2 = u2 v2 / (u2 - v2) comes out negative. Repeat for three positions a."],
        theory="The convex lens would form its image at I, a distance v1 away. The concave lens, placed before I, "
               "intercepts the converging rays; for it, I is a virtual object at u2 = v1 - a on the far side. It makes "
               "a real image at v2, further out than I. The lens formula 1/v2 - 1/u2 = 1/f2, with both distances "
               "taken positive on the side the light is going to, gives a negative f2: the lens is diverging. "
               "This works only if u2 is less than |f2|.",
        safety="Handle the lenses by their edges and keep them on the bench rails, not on the table edge.",
        tour=[{"say": "A convex lens makes an image; a concave lens in front of it pushes the image further away."},
              {"set": {"mir": 1}, "say": "With the concave lens in, the screen must move out to find the sharp image."}],
        questions=[{"q": "The concave lens must be placed",
                    "options": ["between the convex lens and its image", "beyond the image", "in front of the pin"],
                    "answer": 0, "why": "Only then does it receive the converging beam, making a virtual object."},
                   {"q": "With the concave lens in, the image on the screen is",
                    "options": ["further from the lens than before", "nearer than before", "the same"], "answer": 0,
                    "why": "A diverging lens reduces the convergence, so the rays meet later."}],
        sources=[LAB12, SCHOTT, SIM],
        check={"params": {}, "reading": "f2", "textbook": "eng_twolens_f2"},
    )


def _liquid_bodies(mirror: bool) -> list[dict]:
    out = [B("base", "box", name="Bench", size=[0.4, 0.02, 0.3], pos=[0, -0.01, 0], color="wood", cut=False),
           B("pin", "cylinder", name="Pin on a stand", r=0.0015, h=0.04, pos=[0, 0.2, 0], color="steel",
             bind={"y": {"var": "p.H", "k": 1}})]
    if mirror:
        out += [B("mir", "dish", name="Concave mirror, face up", R=0.3, r=0.05, convex=0, pos=[0, 0.0, 0],
                  rot=[-1.5708, 0, 0], color="steel"),
                B("liq", "cylinder", name="Liquid in the mirror", r=0.05, h=0.004, pos=[0, 0.004, 0], color="water",
                  opacity=0.5)]
    else:
        out += [B("pm", "box", name="Plane mirror", size=[0.12, 0.004, 0.12], pos=[0, 0.002, 0], color="steel"),
                B("lens", "lens", name="Convex lens on the mirror", r=0.03, thick=0.006, pos=[0, 0.012, 0],
                  rot=[0, 0, 1.5708], color="glass", opacity=0.45)]
    out.append(B("rays", "rays", name="Rays", var="rays", color="ray"))
    return out


def liquid_lens_plane_mirror() -> dict:
    return lab(
        id="liquid-lens-plane-mirror", rig="liquid-lens-plane-mirror",
        title="Refractive index of a liquid using a convex lens and a plane mirror", group=GRP_O, level="Class XII",
        topic=CH_OPT, chapter=CH_OPT,
        aim="Find the refractive index of a liquid: a drop of it between a convex lens and a plane mirror makes a "
            "plano-concave liquid lens, and the pin heights with and without it give its focal length.",
        kernel="eng_liquid", params={"mode": 0.0, "H": 0.15}, autorun=True,
        camera={"pos": [0.0, 0.3, 0.6], "look": [0.0, 0.1, 0]}, floor=-0.1,
        bodies=_liquid_bodies(False),
        knobs=[knob("H", "Pin height above the lens, H", "H", 8, 40, 0.1, 15, "cm", 0.01),
               knob("liq", "Liquid between lens and mirror (1) or dry (0)", "liq", 0, 1, 1, 0),
               knob("nl", "Take another liquid (n hidden)", "nl", 1.3, 1.5, 0.001, 1.333, hidden=True)],
        instruments=[inst("gap", "readout", "Gap between the pin and its image", "coin", k=1000, unit="mm", lc=0.1,
                          digits=1)],
        table={"columns": [col("Hd", "H without the liquid", "manual", "cm", 0.01, digits=2),
                           col("Hl", "H with the liquid", "manual", "cm", 0.01, digits=2)],
               "calc": "eng_liq_n", "rows_min": 2, "truth": "p.nl", "result_digits": 3},
        steps=["Lay the convex lens on the plane mirror, pin above on a stand.",
               "Move the pin up and down until it and its image coincide with no parallax: H1 is the focal length f1.",
               "Put a few drops of the liquid between the lens and the mirror and repeat: H2 is the focal length F "
               "of the lens with the liquid lens.",
               "1/F = 1/f1 + 1/f2 gives the focal length f2 of the liquid lens, which is concave.",
               "With R from f1 = R / (2(n_g - 1)), n of the liquid = 1 + R / |f2|. Repeat twice."],
        theory="The drops fill the wedge between the curved lower face of the lens and the flat mirror: a "
               "plano-concave liquid lens, f2 = -R / (n - 1). The pin image coincides with the pin when the rays leave "
               "the lens parallel and strike the plane mirror normally, so the pin is at the focal length F of the "
               "lens and the liquid lens in contact: 1/F = 1/f1 + 1/f2. With the lens glass index n_g known and "
               "f1 = R / (2(n_g - 1)), the liquid's index follows from n = 1 + 2(n_g - 1)(1 - f1/F).",
        safety="Wipe the liquid off the mirror and lens afterwards. Use water, a salt solution or clear oil only.",
        tour=[{"say": "A convex lens lying on a plane mirror, with a pin above."},
              {"set": {"liq": 1, "H": 21.5}, "say": "With liquid under the lens the pin must be held higher."}],
        questions=[{"q": "The liquid lens formed between the lens and the mirror is",
                    "options": ["plano-concave (diverging)", "plano-convex (converging)", "a flat plate"], "answer": 0,
                    "why": "It is thick at the edges and thin at the centre, so it diverges."},
                   {"q": "With the liquid, the pin has to be held",
                    "options": ["higher than before", "lower than before", "at the same height"], "answer": 0,
                    "why": "The diverging liquid lens makes the combination weaker: F is longer than f1."}],
        sources=[LAB12, CBSE, SCHOTT, SIM],
        check={"params": {}, "reading": "nl", "textbook": "eng_liquid_nl"},
    )


def liquid_concave_mirror() -> dict:
    return lab(
        id="liquid-concave-mirror", rig="liquid-lens-plane-mirror",
        title="Refractive index of a liquid using a concave mirror", group=GRP_O, level="Class XII",
        topic=CH_OPT, chapter=CH_OPT,
        aim="Find the refractive index of a liquid poured into a concave mirror: the pin must be held lower once "
            "the liquid is in, and the ratio of the two heights is the index.",
        kernel="eng_liquid", params={"mode": 1.0, "R": 0.30, "H": 0.30}, autorun=True,
        camera={"pos": [0.0, 0.3, 0.6], "look": [0.0, 0.1, 0]}, floor=-0.1,
        bodies=_liquid_bodies(True),
        knobs=[knob("H", "Pin height above the rim plane, H", "H", 12, 36, 0.1, 30, "cm", 0.01),
               knob("liq", "Liquid in the mirror (1) or dry (0)", "liq", 0, 1, 1, 0),
               knob("nl", "Take another liquid (n hidden)", "nl", 1.3, 1.5, 0.001, 1.333, hidden=True)],
        instruments=[inst("gap", "readout", "Gap between the pin and its image", "coin", k=1000, unit="mm", lc=0.1,
                          digits=1)],
        table={"columns": [col("Hd", "H without the liquid", "manual", "cm", 0.01, digits=2),
                           col("Hl", "H with the liquid", "manual", "cm", 0.01, digits=2)],
               "calc": "eng_liq_n", "rows_min": 2, "truth": "p.nl", "result_digits": 3},
        steps=["Lay the concave mirror face up with a pin above it on a stand.",
               "Move the pin until it and its image coincide with no parallax: the pin is at the centre of "
               "curvature, a height x1 = R.",
               "Pour a little liquid into the mirror, so that its flat top covers the pole, and find the new "
               "height x2 of the coincidence.",
               "n = x1 / x2. Repeat twice and take the mean."],
        theory="With no liquid the pin and its image coincide when the pin is at the centre of curvature, x1 = R. "
               "With liquid in, the flat top surface refracts the light: for the rays to strike the mirror along its "
               "radius they must seem to come from the centre of curvature, and an object x2 above the liquid appears "
               "n x2 below its surface. So n x2 = R and n = x1 / x2. Both heights are read from the same level.",
        safety="Use water or a clear oil. Wipe the mirror dry afterwards; its silvering is easily scratched.",
        tour=[{"say": "A concave mirror lies face up with a pin above it."},
              {"set": {"liq": 1, "H": 22.5}, "say": "With water in the mirror the coincidence comes at a lower pin height."}],
        questions=[{"q": "After the liquid is poured in, the pin has to be held",
                    "options": ["lower", "higher", "at the same height"], "answer": 0,
                    "why": "The liquid makes the pin look deeper, so it must be brought nearer the surface."},
                   {"q": "Why must both heights be measured from the same reference?",
                    "options": ["The ratio x1 / x2 would be wrong otherwise", "To save time", "The scale is short"],
                    "answer": 0, "why": "n = x1 / x2 holds only if both heights are taken from the same level."}],
        sources=[CBSE, LAB12, SIM],
        check={"params": {}, "reading": "nl", "textbook": "eng_liquid_nl"},
    )


# ===================================================================================== the apparatus already built
def slab_lateral_deviation() -> dict:
    from .optics_school import glass_slab_ray
    d = copy.deepcopy(glass_slab_ray())
    d.update(id="slab-lateral-deviation", rig="school-glass-slab-ray", level="Class XII", topic=CH_OPT, chapter=CH_OPT,
             title="Glass slab: refraction and lateral deviation of an oblique beam",
             aim="Trace an oblique ray through a rectangular glass slab with pins, show that the emergent ray is "
                 "parallel to the incident ray, and measure the lateral displacement for different angles of incidence.")
    d["theory"] = ("A ray entering a glass slab bends towards the normal (n = sin i / sin r); leaving by the parallel "
                   "face it bends away by the same amount, so the emergent ray is parallel to the incident ray: e = i. "
                   "It is shifted sideways by the lateral displacement t sin(i - r) / cos r, which grows with the "
                   "thickness t and with the angle of incidence.")
    d["sources"] = [LAB12, SIM]
    d["check"] = {"params": {"i": 0.7854}, "reading": "shift", "textbook": "slabray_shift"}
    return d


def image_nature_candle_screen() -> dict:
    from .optics_school import mirror_images
    d = copy.deepcopy(mirror_images())
    d.update(id="image-nature-candle-screen", rig="school-convex-lens-images", level="Class XII", topic=CH_OPT,
             chapter=CH_OPT, title="Convex lens: nature and size of the image of a candle at different distances",
             aim="Place a lit candle at different distances from a convex lens, catch the image on a screen where it "
                 "forms, and note whether it is real or virtual, erect or inverted, larger or smaller.")
    d["sources"] = [LAB12, SIM]
    return d


# ===================================================================================== AC engine
def inductor_impedance() -> dict:
    return lab(
        id="inductor-impedance", rig="inductor-impedance",
        title="Resistance and impedance of an inductor, with and without an iron core", group=GRP_E,
        level="Class XII", topic=CH_AC, chapter=CH_AC,
        aim="Find the resistance of a coil with direct current and its impedance with alternating current, with "
            "and without an iron core, and so the inductance in each case.",
        kernel="eng_acphasor", params={"topo": 2.0, "V": 8.4853, "f": 50.0, "r": 12.0, "L": 0.15, "kfe": 6.0},
        autorun=True, camera={"pos": [0.0, 0.5, 0.8], "look": [0.0, 0.05, 0]}, floor=-0.1,
        bodies=[B("base", "box", name="Bench", size=[0.9, 0.02, 0.5], pos=[0, -0.01, 0], color="wood", cut=False),
                B("coil", "cylinder", name="Coil", info="A coil of many turns of enamelled copper wire.", r=0.05,
                  h=0.08, pos=[0, 0.05, 0], color="copper"),
                B("core", "box", name="Iron core", size=[0.03, 0.12, 0.03], pos=[0.0, 0.07, 0], color="#6b7079"),
                B("tr", "box", name="Step-down transformer", info="Mains in, 6 volt rms out.", size=[0.14, 0.1, 0.1],
                  pos=[-0.3, 0.05, 0], color="#2b2f36")],
        knobs=[knob("V", "Source (amplitude, volts)", "V", 3, 11, 0.1, 8.4853, "V"),
               knob("core", "Iron core in the coil (1) or out (0)", "core", 0, 1, 1, 0),
               knob("L", "Take another coil (L hidden)", "L", 0.05, 0.4, 0.001, 0.15, "H", hidden=True)],
        instruments=[inst("Z", "readout", "Impedance |Z|", "Zmag", unit="ohm", lc=0.1, digits=1),
                     inst("I", "readout", "Current amplitude", "I", k=1000, unit="mA", lc=0.1, digits=1),
                     inst("ph", "readout", "Phase angle of the voltage ahead of the current", "phi", k=1 / DEG,
                          unit="°", lc=0.1, digits=1)],
        table={"columns": [col("V", "V (ac)", "knob:V", "V", 0.7071, digits=2),
                           col("I", "I (ac)", "inst:I", "mA", 0.001 * 0.7071, digits=2),
                           col("r", "R (dc)", "manual", "ohm", 1.0, digits=1)],
               "calc": "eng_coil_L", "rows_min": 2, "truth": "p.L", "result_unit": "H", "result_digits": 3},
        steps=["With a battery and a milliammeter, find the DC resistance R of the coil: R = V / I.",
               "Connect the coil to the 6 V secondary of the step-down transformer through an AC ammeter, with an "
               "AC voltmeter across it.",
               "Read V and I: the impedance Z = V / I.",
               "Push the iron core into the coil and read V and I again: Z rises.",
               "L = sqrt(Z squared - R squared) / (2 pi f), with f = 50 Hz, with and without the core."],
        theory="A coil has resistance R and inductance L in series. A steady current sees only R. An alternating "
               "current also meets the reactance X = 2 pi f L, and the two add at right angles: Z = sqrt(R squared + "
               "X squared). The voltage leads the current by tan(phi) = X / R. An iron core concentrates the magnetic "
               "field so L, and so Z, rises several times.",
        safety="Use only the low-voltage (about 6 V) secondary of a step-down transformer, never the mains directly, "
               "and keep the coil's connections insulated. Switch off before changing the circuit.",
        tour=[{"say": "A coil, and a step-down transformer giving a safe 6 volt supply."},
              {"set": {"core": 1}, "say": "With the iron core in, the current drops: the impedance has risen."}],
        questions=[{"q": "The iron core is pushed into the coil. The current from the AC source",
                    "options": ["falls", "rises", "stays the same"], "answer": 0,
                    "why": "The inductance, and so the reactance and the impedance, rise."},
                   {"q": "The same coil on a battery draws a much larger current than on AC of the same voltage because",
                    "options": ["only its resistance limits a steady current", "AC is weaker", "the battery is bigger"],
                    "answer": 0, "why": "A steady current has no reactance."}],
        sources=[CBSE, LAB12, SIM],
        check={"params": {}, "reading": "L_est", "textbook": "eng_coil_L"},
    )


def ac_mains_frequency_sonometer() -> dict:
    return lab(
        id="ac-mains-frequency-sonometer", rig="ac-mains-frequency-sonometer",
        title="Frequency of the AC mains with a sonometer", group=GRP_E, level="Class XII", topic=CH_AC,
        chapter=CH_AC,
        aim="Find the frequency of the AC mains: a sonometer wire carrying a small alternating current between the "
            "poles of a magnet is made to resonate by sliding the bridge.",
        kernel="eng_acsono", params={"mu": 0.00147, "M": 0.5, "l": 0.5}, autorun=True,
        camera={"pos": [0.0, 0.4, 0.8], "look": [0.0, 0.03, 0]}, floor=-0.1,
        bodies=[B("box", "box", name="Sonometer box", size=[1.0, 0.08, 0.1], pos=[0, 0.0, 0], color="wood"),
                B("wire", "box", name="Copper wire", size=[0.9, 0.001, 0.001], pos=[0, 0.085, 0], color="copper"),
                B("mag", "box", name="Horse-shoe magnet", info="Its poles straddle the wire at the middle.",
                  size=[0.05, 0.06, 0.03], pos=[0, 0.12, 0], color="#a02828"),
                B("tr", "box", name="Step-down transformer", size=[0.12, 0.08, 0.08], pos=[-0.3, 0.04, -0.2],
                  color="#2b2f36")],
        knobs=[knob("l", "Length of wire between the bridges, l", "l", 20, 90, 0.1, 50, "cm", 0.01),
               knob("M", "Load on the hanger, M", "M", 0.2, 1.0, 0.05, 0.5, "kg"),
               knob("Rh", "Rheostat", "Rh", 2, 20, 0.5, 5, "ohm"),
               knob("fm", "Take the mains of another grid (f hidden)", "fm", 45, 65, 0.01, 49.93, "Hz", hidden=True)],
        instruments=[inst("amp", "readout", "Amplitude of the wire at the middle", "amp", k=1000, unit="mm", lc=0.01,
                          digits=2),
                     inst("I", "readout", "Current in the wire", "I", unit="A", lc=0.01, digits=2)],
        table={"columns": [col("l", "Resonant length l", "knob:l", "cm", 0.01, digits=1),
                           col("M", "Load M", "knob:M", "kg", 1.0, digits=2)],
               "calc": "eng_sono_f", "rows_min": 3, "truth": "p.fm", "result_unit": "Hz", "result_digits": 1},
        steps=["Stretch the wire with a known load and set the horse-shoe magnet at the middle of the wire.",
               "Join the wire to the 6 V secondary of a step-down transformer through a rheostat.",
               "Slide one bridge to make the wire shorter or longer until it vibrates with the largest amplitude.",
               "Record l and the load M; the wire's linear density mu is printed on its reel.",
               "f = (1 / 2l) sqrt(M g / mu). Repeat with two other loads."],
        theory="The current in the wire alternates at the mains frequency, so the force B I w from the magnet "
               "alternates too, and pushes the wire up and down f times a second. The wire is a stretched string with "
               "natural frequency f1 = (1 / 2l) sqrt(T / mu), T = M g. It responds most when f1 equals the mains "
               "frequency, so at the resonant length f = (1 / 2l) sqrt(T / mu). The wire must be non-magnetic, "
               "or the pull would come twice every cycle.",
        safety="Use only the low-voltage (about 6 V) secondary of a step-down transformer and keep the rheostat in "
               "circuit to limit the current: a short length of copper wire gets hot. Never connect the wire to the "
               "mains. Keep the load away from your feet.",
        tour=[{"say": "A copper wire between two bridges, with a horse-shoe magnet at its middle."},
              {"set": {"l": 57.8}, "say": "At this length the wire jumps highest: it is in resonance with the mains."}],
        questions=[{"q": "At resonance the wire vibrates",
                    "options": ["with the largest amplitude", "not at all", "with the smallest amplitude"], "answer": 0,
                    "why": "The natural frequency of the wire equals the driving frequency."},
                   {"q": "If the load M is increased the resonant length",
                    "options": ["increases", "decreases", "stays the same"], "answer": 0,
                    "why": "l is proportional to sqrt(T): a tighter wire needs a longer length to keep the same frequency."}],
        sources=[LAB12, CBSE, SIM],
        check={"params": {}, "reading": "f_est", "textbook": "eng_sono_f"},
    )


# ===================================================================================== clocked logic
def _trainer_bodies(nled: int) -> list[dict]:
    out = [B("tr", "box", name="Digital trainer", info="A 5 volt rail, input switches and output lamps.",
             size=[0.5, 0.04, 0.22], pos=[0, 0.02, 0], color="#2f343c")]
    for i in range(nled):
        out.append(B("led%d" % i, "sphere", name="Output lamp", r=0.01, pos=[0.1 + i * 0.04, 0.05, 0], color="red"))
    for i in range(3):
        out.append(B("sw%d" % i, "box", name="Input switch", size=[0.014, 0.012, 0.02], pos=[-0.2 + i * 0.05, 0.046, 0],
                     color="#d9d9d4"))
    return out


def flip_flops_nand() -> dict:
    return lab(
        id="flip-flops-nand", rig="flip-flops-nand",
        title="Clocked RS flip-flop built from NAND gates", group=GRP_D, level="B.Sc. (Hons.) Physics",
        topic=CH_DIG, chapter=CH_DIG,
        aim="Build a flip-flop from 2-input NAND gates on the trainer, pulse the clock once for every combination "
            "of inputs and the stored bit, and write down its characteristic table.",
        kernel="eng_ff", params={"kind": 1.0}, autorun=True,
        camera={"pos": [0.0, 0.5, 0.5], "look": [0, 0.03, 0]}, floor=-0.03, bodies=_trainer_bodies(2),
        knobs=[knob("a", "Input S", "a", 0, 1, 1, 0), knob("b", "Input R", "b", 0, 1, 1, 0),
               knob("q0", "Stored bit before the pulse", "q0", 0, 1, 1, 0),
               knob("kind", "Circuit (0 RS, 1 clocked RS, 2 D, 3 JK)", "kind", 0, 3, 1, 1)],
        instruments=[inst("Q", "readout", "Output Q", "Q", digits=0), inst("Qb", "readout", "Output Q-bar", "Qb", digits=0)],
        steps=["Wire the NAND gates as shown, with pin 14 of each package on the +5 V rail and pin 7 on ground.",
               "Set the stored bit with the direct set / reset line, set the data inputs, then press the clock once.",
               "Read Q on the lamp for each of the eight combinations of S, R and the stored bit.",
               "Write the characteristic table and compare it with the equation Q+ = S + R'Q.",
               "Note what happens for S = R = 1, which is not allowed."],
        theory="Two cross-coupled NAND gates are a latch: each output feeds the other's input, so the pair holds a "
               "bit. Two more NAND gates gate the inputs S and R with the clock, so the state can change only while "
               "the clock is high. The next state is Q+ = S + R'Q for S R = 0. When S = R = 1 both outputs would be "
               "driven high and, when the clock falls, which way the latch settles depends on the gates' timing: the "
               "combination is forbidden.",
        safety="The trainer's 5 volt rail only. Wire with the power off and never join two outputs together.",
        tour=[{"say": "Four NAND gates: two cross-coupled as the latch and two gating the inputs with the clock."},
              {"set": {"a": 1}, "say": "S = 1 and a clock pulse sets the flip-flop: Q goes to 1."}],
        questions=[{"q": "In the clocked RS flip-flop, S = 0 and R = 0 with a clock pulse",
                    "options": ["leaves Q unchanged", "sets Q", "resets Q"], "answer": 0,
                    "why": "Both gating gates output 1, which the latch holds."},
                   {"q": "Why is S = R = 1 forbidden?",
                    "options": ["The outcome depends on gate timing", "It draws too much current", "It sets Q twice"],
                    "answer": 0, "why": "Both outputs are driven to 1 and the final state is undefined."}],
        sources=[DU, MANO, TTL, SIM],
        check={"params": {"kind": 1.0}, "reading": "sig", "textbook": "eng_ff_sig"},
    )


def jk_master_slave() -> dict:
    return lab(
        id="jk-master-slave", rig="flip-flops-nand",
        title="JK master-slave flip-flop from NAND gates", group=GRP_D, level="B.Sc. (Hons.) Physics",
        topic=CH_DIG, chapter=CH_DIG,
        aim="Wire a master-slave JK flip-flop from NAND gates (the circuit inside a 7476), take its truth table with "
            "one clock pulse per row and see that J = K = 1 toggles the output exactly once.",
        kernel="eng_ff", params={"kind": 4.0, "a": 0.0, "b": 0.0}, autorun=True,
        camera={"pos": [0.0, 0.5, 0.5], "look": [0, 0.03, 0]}, floor=-0.03, bodies=_trainer_bodies(2),
        knobs=[knob("a", "Input J", "a", 0, 1, 1, 0), knob("b", "Input K", "b", 0, 1, 1, 0),
               knob("q0", "Stored bit before the pulse", "q0", 0, 1, 1, 0),
               knob("tw", "Clock high for (gate delays)", "tw", 8, 60, 1, 24)],
        instruments=[inst("Q", "readout", "Output Q", "Q", digits=0), inst("Qb", "readout", "Output Q-bar", "Qb", digits=0),
                     inst("M", "readout", "Master latch", "M", digits=0)],
        steps=["Wire the nine NAND gates: a master latch, a slave latch and an inverted clock for the slave.",
               "Set J and K, and the stored bit, and press the clock once.",
               "Note that the master follows J and K while the clock is high, and the slave copies the master only "
               "when the clock falls.",
               "Take all eight rows and compare them with Q+ = J Q-bar + K-bar Q.",
               "Hold J = K = 1 and pulse the clock: Q toggles once per pulse, however long the clock is high."],
        theory="A level-triggered JK flip-flop with J = K = 1 would flip over and over for as long as the clock is "
               "high (race-around). The master-slave circuit prevents it: the master accepts J and K while the clock "
               "is high but the slave is shut; when the clock falls the master is shut and the slave takes what the "
               "master held. The output therefore changes once, at the falling edge. Characteristic equation: "
               "Q+ = J Q-bar + K-bar Q. J = K = 1 toggles; J = K = 0 holds.",
        safety="The trainer's 5 volt rail only. Wire with the power off.",
        tour=[{"say": "A master latch feeding a slave latch, which is opened by the inverted clock."},
              {"set": {"a": 1, "b": 1}, "say": "J = K = 1: one clock pulse flips Q exactly once."}],
        questions=[{"q": "In a master-slave JK flip-flop the output changes",
                    "options": ["when the clock falls", "while the clock is high", "when J changes"], "answer": 0,
                    "why": "The slave latch opens only when the clock goes low."},
                   {"q": "J = K = 1 and one clock pulse give",
                    "options": ["Q toggled once", "Q set to 1", "Q reset to 0"], "answer": 0,
                    "why": "Q+ = Q-bar for J = K = 1."}],
        sources=[DU, MANO, TTL, SIM],
        check={"params": {"kind": 4.0}, "reading": "sig", "textbook": "eng_ff_sig"},
    )


def counter_4bit() -> dict:
    return lab(
        id="counter-4bit", rig="flip-flops-nand",
        title="4-bit ripple counter from JK flip-flops and its timing diagram", group=GRP_D,
        level="B.Sc. (Hons.) Physics", topic=CH_DIG, chapter=CH_DIG,
        aim="Join four master-slave JK flip-flops (J = K = 1) so that each clocks the next, count sixteen input pulses "
            "and draw the timing diagram, noting how the carry ripples.",
        kernel="eng_count", params={"down": 0.0}, autorun=True,
        camera={"pos": [0.0, 0.5, 0.5], "look": [0, 0.03, 0]}, floor=-0.03, bodies=_trainer_bodies(4),
        knobs=[knob("down", "Count down (1) or up (0)", "down", 0, 1, 1, 0)],
        instruments=[inst("w", "readout", "Count on the lamps", "word", digits=0),
                     inst("rp", "readout", "Output changes after the last pulse", "ripple", digits=0),
                     inst("gl", "readout", "Wrong counts shown on the way", "glitch", digits=0)],
        steps=["Hold J and K of every flip-flop high. Join Q of each stage to the clock of the next.",
               "Clear the counter. Press the clock once at a time and write down the four lamps after each pulse.",
               "Draw the timing diagram of the clock and Q0 to Q3: each stage divides the frequency by two.",
               "Watch the lamps closely when the count goes from 7 to 8: the stages change one after another.",
               "Reverse the connection (Q-bar to the next clock) and count down."],
        theory="Every stage toggles on the falling edge of its clock, so Q0 has half the clock frequency, Q1 a quarter, "
               "and so on: the four outputs count in binary. The clock of each stage is the output of the one before, "
               "so the change ripples through them one after another, each stage taking about four gate delays. For "
               "a moment the counter shows wrong values, such as 0110, 0100 and 0000 on the way from 0111 to 1000. "
               "An asynchronous counter is therefore too slow when the count must be read at once.",
        safety="The trainer's 5 volt rail only. Wire with the power off.",
        tour=[{"say": "Four stages: each one's output clocks the next."},
              {"say": "From 7 to 8 the carry has to ripple through all four stages."}],
        questions=[{"q": "Q0 of a 4-bit ripple counter has a frequency of",
                    "options": ["half the clock", "a quarter of the clock", "the clock"], "answer": 0,
                    "why": "Each flip-flop toggles once per clock pulse, dividing by two."},
                   {"q": "A ripple counter may show wrong values for an instant because",
                    "options": ["the stages change one after another", "the clock is noisy", "J and K are low"],
                    "answer": 0, "why": "Each stage is clocked by the one before and waits for its gate delays."}],
        sources=[DU, MANO, TTL, SIM],
        check={"params": {"down": 0.0}, "reading": "sum", "textbook": "eng_count_sum"},
    )


def shift_register() -> dict:
    return lab(
        id="shift-register", rig="flip-flops-nand",
        title="4-bit shift register from D flip-flops", group=GRP_D, level="B.Sc. (Hons.) Physics",
        topic=CH_DIG, chapter=CH_DIG,
        aim="Join four edge-triggered D flip-flops so that each passes its bit to the next on the clock, load a "
            "4-bit word serially, one bit per pulse, and read it back in parallel.",
        kernel="eng_shift", params={"word": 11.0}, autorun=True,
        camera={"pos": [0.0, 0.5, 0.5], "look": [0, 0.03, 0]}, floor=-0.03, bodies=_trainer_bodies(4),
        knobs=[knob("si", "Serial data input", "si", 0, 1, 1, 0),
               knob("word", "Word to load (most significant bit first)", "word", 0, 15, 1, 11)],
        instruments=[inst("w", "readout", "Parallel word Q0..Q3", "word_out", digits=0),
                     inst("q3", "readout", "Q3 (first bit in)", "Q3", digits=0)],
        steps=["Join Q of each D flip-flop to the D input of the next, and all the clocks together.",
               "Set the serial input to the first bit of the word, most significant first, and press the clock.",
               "Set the next bit and press the clock again; repeat until all four bits are in.",
               "Read Q3, Q2, Q1, Q0 on the lamps: they hold the word, the first bit in having moved furthest.",
               "Keep pulsing with the input low and watch the bits shift out."],
        theory="Each D flip-flop copies its D input to Q on the rising clock edge, so with Q of one joined to D of the "
               "next, a bit moves one place along on every pulse. The new bit enters at the first stage and the "
               "oldest leaves at the last. All four copy at the same edge, each from the value its neighbour had "
               "just before it, so the bits move cleanly even though the flip-flops change at once: the register "
               "turns serial data into a parallel word.",
        safety="The trainer's 5 volt rail only. Wire with the power off.",
        tour=[{"say": "Four D flip-flops in a row, one clock for all."},
              {"say": "Each pulse moves every bit one place to the right."}],
        questions=[{"q": "A 4-bit serial-in register needs how many pulses to load a word?",
                    "options": ["4", "1", "8"], "answer": 0, "why": "One bit enters per pulse."},
                   {"q": "Why does the register not simply copy the first bit to all four stages?",
                    "options": ["Each stage sees its neighbour's old value at the edge", "The clock is slow",
                                "The bits are inverted"], "answer": 0,
                    "why": "All stages sample at the same edge, before the neighbour has changed."}],
        sources=[DU, MANO, TTL, SIM],
        check={"params": {"word": 11.0}, "reading": "word", "textbook": "eng_shift_word"},
    )


BUILDERS: tuple[Any, ...] = (convex_mirror_using_lens, concave_lens_using_convex, liquid_lens_plane_mirror,
                             liquid_concave_mirror, slab_lateral_deviation, image_nature_candle_screen,
                             inductor_impedance, ac_mains_frequency_sonometer, flip_flops_nand, jk_master_slave,
                             counter_4bit, shift_register)
