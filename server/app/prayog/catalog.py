"""The Prayogshala catalogue, L1: 22 physics practicals from the NCERT Class XI / XII laboratory manuals, written as LSL
data (no code). Every lab passes `lsl.check` and its own NCERT check (`lsl.run_check`, 1 %) in the tests.

Coordinates are metres in the 3D stage unless a lab scales them (vernier / screw gauge are magnified and say so)."""
from __future__ import annotations

import math
from typing import Any

DEG = math.pi / 180
R2D = 180 / math.pi
S11 = {"title": "NCERT Physics Textbook Class XI + Laboratory Manual Physics Class XI"}
S12 = {"title": "NCERT Physics Textbook Class XII + Laboratory Manual Physics Class XII"}
SIM = {"title": "Hoola Prayogshala kernel", "note": "readings come from the simulation code; checked against the NCERT formula in Hoola's tests"}


def B(id: str, kind: str, **kw: Any) -> dict:
    return {"id": id, "kind": kind, **kw}


def knob(id, label, param, mn, mx, st, val, unit="", k=1.0, **kw) -> dict:
    d = {"id": id, "label": label, "param": param, "min": mn, "max": mx, "step": st, "value": val}
    if unit:
        d["unit"] = unit
    if k != 1.0:
        d["k"] = k
    d.update(kw)
    return d


def inst(id, kind, label, var=None, **kw) -> dict:
    d = {"id": id, "kind": kind, "label": label}
    if var:
        d["var"] = var
    d.update(kw)
    return d


def col(id, label, frm="manual", unit="", k=1.0, **kw) -> dict:
    d = {"id": id, "label": label, "from": frm}
    if unit:
        d["unit"] = unit
    if k != 1.0:
        d["k"] = k
    d.update(kw)
    return d


def lab(**kw) -> dict:
    d = {"lsl": 1, "field": "physics", "lang": "hi-IN"}
    d.update(kw)
    return d


def board(w=1.0, d=0.6, y=-0.01) -> dict:
    return B("board", "box", name="Lakdi ka board", size=[w, 0.02, d], pos=[0, y, 0], color="wood", cut=False)


def dial(id, pos, name, info="") -> list[dict]:
    x, y, z = pos
    return [B(id + "_box", "box", name=name, info=info, size=[0.12, 0.04, 0.1], pos=[x, y + 0.02, z], color="#2b2f36"),
            B(id + "_face", "box", size=[0.1, 0.001, 0.07], pos=[x, y + 0.041, z + 0.005], color="white"),
            B(id + "_scale", "torus", r=0.035, tube=0.0012, arc=2.4, pos=[x, y + 0.043, z + 0.02], rot=[-1.5708, 0, 0.37], color="ink")]


def needle(id, pos, var, k, c=0.0, mn=-1.2, mx=1.2) -> dict:
    x, y, z = pos
    return B(id, "needle", length=0.038, pos=[x, y + 0.044, z + 0.02], rot=[-1.5708, 0, 0],
             bind={"rz": {"var": var, "k": k, "c": c, "min": mn, "max": mx}}, color="red")


# ======================================================================================================== MECHANICS
def pendulum() -> dict:
    return lab(
        id="simple-pendulum", title="Simple pendulum: L aur T", group="Physics · Mechanics", level="Class XI",
        topic="Oscillations", aim="Lambai L badal kar samay-avadhi T naapiye aur g nikaaliye.",
        kernel="pendulum", params={"b": 0.0}, speed=1, speeds=[0.25, 0.5, 1, 2],
        camera={"pos": [0.5, 0.0, 2.7], "look": [0, -0.15, 0]}, floor=-1.02,
        bodies=[
            B("base", "box", name="Stand ka base", size=[0.6, 0.04, 0.4], pos=[0, -1.0, 0], color="wood"),
            B("rod", "cylinder", name="Stand ki chhad", r=0.012, h=1.66, pos=[-0.25, -0.17, 0], color="steel"),
            B("arm", "box", size=[0.3, 0.02, 0.02], pos=[-0.12, 0.62, 0], color="steel"),
            B("clamp", "box", name="Split cork / clamp", info="Dhaaga yahan se latakta hai: yahi pivot hai.",
              size=[0.05, 0.05, 0.05], pos=[0, 0.62, 0], color="black"),
            B("bob", "sphere", name="Bob", info="Bhaari dhaatu ka gola. Iska vazan T ko nahi badalta.", r=0.035,
              pos=[0, 0.6, 0], color="brass", bind={"x": "bob_x", "y": "bob_y"}),
            B("thread", "rope", name="Dhaaga", info="Halka, na khinchne wala dhaaga. L = pivot se bob ke centre tak.",
              a=[0, 0.6, 0], b="bob", r=0.0015, color="ink"),
            B("lbl", "text", text="Pivot", size=0.04, pos=[0.12, 0.66, 0]),
        ],
        knobs=[knob("L", "Lambai L", "L", 20, 150, 1, 100, "cm", 0.01),
               knob("amp", "Shuruaati kona", "theta0", 2, 30, 1, 5, "°", DEG, hint="Chhota kona (< 10°) rakhiye: tab T = 2π√(L/g)"),
               knob("g", "Grah ka g (Chaand 1.6, Prithvi 9.8, Brihaspati 24.8)", "g", 1.6, 24.8, 0.1, 9.8, "m/s²")],
        instruments=[inst("sw", "stopwatch", "Stopwatch (20 dolan ginkar)"),
                     inst("ang", "readout", "Kona θ", "theta", k=R2D, unit="°", digits=1),
                     inst("gr", "graph", "θ samay ke saath", "theta", k=R2D, xlabel="t (s)")],
        table={"columns": [col("L", "L", "knob:L", "cm", 0.01), col("T", "T = t₂₀ ÷ 20", "inst:sw", "s", div=20, digits=3)],
               "calc": "pendulum_g", "rows_min": 3, "truth": "p.g", "result_digits": 2,
               "hint": "Har L par: Stopwatch start, 20 dolan ginkar stop, phir 'Reading record karo'."},
        steps=["Lambai L = 100 cm rakhiye aur kona 5°.", "Chalao dabaiye; jab bob ek kinare par ho tab Stopwatch start kijiye.",
               "20 poore dolan ginkar Stopwatch rokiye aur reading record kijiye.",
               "L ko 80, 60, 40 cm karke dohraiye.", "Table se g = 4π²L/T² ka ausat dekhiye."],
        theory="Chhote kone par simple pendulum ki samay-avadhi T = 2π√(L/g). Isliye T² aur L seedhe anupaat mein hain; "
               "graph T² vs L ki dhalaan 4π²/g hoti hai. Bob ka vazan T ko nahi badalta.",
        safety="Asli lab mein stand ko mez par pakka rakhiye aur bob ko zor se mat phenkiye.",
        tour=[{"cam": [0.5, 0.0, 2.7], "look": [0, -0.15, 0], "say": "Yeh simple pendulum hai: ek dhaage se latka bhaari bob. Upar clamp pivot hai."},
              {"cam": [0.25, 0.1, 1.2], "look": [0, -0.35, 0], "say": "Bob ko 5 degree par chhodte hain. Dekhiye, ek dolan mein lagbhag do second lagte hain.", "run": True},
              {"set": {"L": 40}, "say": "Ab lambai 40 centimetre. Dolan tez ho gaye: T ghat gaya, kyunki T, L ke square root ke saath badalta hai."},
              {"set": {"g": 1.6}, "say": "Yeh Chaand ka g hai. Wahan pendulum bahut dheere jhoolta hai."},
              {"set": {"g": 9.8, "L": 100}, "say": "Ab Table tab kholiye, aur har lambai par 20 dolan ka samay record kijiye. Hoola g nikaal dega."}],
        questions=[{"q": "Lambai 4 guna karne par T kitna ho jayega?", "options": ["2 guna", "4 guna", "Utna hi", "16 guna"], "answer": 0,
                    "why": "T ∝ √L, aur √4 = 2."},
                   {"q": "Bhaari bob lagane par T?", "options": ["Badhega", "Ghatega", "Nahi badlega"], "answer": 2,
                    "why": "T = 2π√(L/g) mein vazan hai hi nahi."}],
        sources=[S11, SIM],
        check={"params": {"L": 1.0, "theta0": 0.0873}, "reading": "T", "textbook": "pendulum_T"},
    )


def _spring_bodies(name_info: str) -> list[dict]:
    return [
        B("stand", "box", name="Stand", size=[0.04, 0.9, 0.04], pos=[-0.25, 0.15, 0], color="steel"),
        B("base", "box", size=[0.6, 0.04, 0.35], pos=[-0.1, -0.32, 0], color="wood"),
        B("arm", "box", size=[0.3, 0.02, 0.03], pos=[-0.1, 0.6, 0], color="steel"),
        B("hook", "box", size=[0.03, 0.02, 0.03], pos=[0, 0.59, 0], color="black"),
        B("pan", "cylinder", name="Hanger + vazan", info=name_info, r=0.03, h=0.03, pos=[0, 0.58, 0], color="brass",
          bind={"y": "bob_y"}),
        B("spring", "spring", name="Spring", info="Hooke ka niyam: khinchaav F = k x (lochdaar seema ke andar).",
          a=[0, 0.58, 0], b={"body": "pan", "off": [0, 0.015, 0]}, r=0.018, turns=16, wire=0.0018, color="steel"),
        B("ptr", "box", name="Pointer", size=[0.06, 0.003, 0.003], pos=[-0.06, 0.58, 0], color="red", bind={"y": "bob_y"}),
        B("ruler", "scale", name="Meter scale (cm)", length=0.6, spacing=0.01, major=10, labels=True, label_step=10,
          tick=0.012, font=0.02, pos=[-0.1, 0.58, 0.001], rot=[0, 0, -1.5708]),
    ]


def hooke() -> dict:
    return lab(
        id="hookes-law", title="Hooke ka niyam: spring constant", group="Physics · Mechanics", level="Class XI",
        topic="Mechanical Properties of Solids", aim="Vazan badhakar spring ka khinchaav naapiye aur spring constant k nikaaliye.",
        kernel="spring", params={"c": 0.6, "x0": 0.0}, autorun=True,
        camera={"pos": [0.35, 0.25, 1.3], "look": [-0.05, 0.25, 0]}, floor=-0.34,
        bodies=_spring_bodies("Har 50 g ka slotted vazan."),
        knobs=[knob("m", "Latka vazan", "m", 50, 500, 50, 100, "g", 0.001),
               knob("k", "Spring badliye (k chhupa hai)", "k", 10, 40, 1, 20, "N/m", hidden=True)],
        instruments=[inst("ext", "readout", "Khinchaav (pointer, scale par)", "ext", k=100, unit="cm", lc=0.1, digits=1),
                     inst("gr", "graph", "Khinchaav vs vazan", "ext", k=100, x="knob:m", xlabel="m (g)", dots=True)],
        table={"columns": [col("m", "Vazan m", "knob:m", "g", 0.001), col("ext", "Khinchaav x", "inst:ext", "cm", 0.01, digits=1)],
               "calc": "spring_k_static", "rows_min": 3, "truth": "p.k", "result_digits": 1,
               "hint": "Har vazan ke baad pointer ruk jaaye, phir reading record kijiye."},
        steps=["Bina vazan ke pointer ki jagah dekhiye.", "50 g, 100 g, 150 g... latkaiye.",
               "Har baar pointer rukne par khinchaav record kijiye.", "Graph seedhi rekha hai? Uski dhalaan se k = mg/x."],
        theory="Lochdaar seema ke andar spring ka khinchaav x vazan ke seedhe anupaat mein hai: mg = k x. Graph x vs m seedhi rekha.",
        safety="Spring ko seema se zyada mat kheenchiye: phir woh wapas poora nahi lautta.",
        tour=[{"say": "Spring stand se latki hai; neeche hanger par vazan lagte hain. Pointer scale par khinchaav dikhata hai."},
              {"set": {"m": 300}, "say": "300 gram lagaya: spring zyada khinchi. Doguna vazan, doguna khinchaav."},
              {"set": {"m": 100}, "say": "Ab Table mein har vazan par khinchaav record kijiye. Hoola k nikaal dega."}],
        questions=[{"q": "Vazan 3 guna karne par khinchaav?", "options": ["3 guna", "9 guna", "Utna hi"], "answer": 0,
                    "why": "mg = kx: x vazan ke seedhe anupaat mein hai."}],
        sources=[S11, SIM],
        check={"params": {"m": 0.2, "c": 0.6, "x0": 0.0}, "reading": "ext", "textbook": "spring_ext"},
    )


def shm() -> dict:
    return lab(
        id="spring-oscillation", title="Spring-mass dolan: T aur m", group="Physics · Mechanics", level="Class XI",
        topic="Oscillations", aim="Spring par vazan ke dolan ka samay naapiye aur k nikaaliye (T = 2π√(m/k)).",
        kernel="spring", params={"c": 0.0, "x0": 0.03}, speeds=[0.25, 0.5, 1, 2],
        camera={"pos": [0.35, 0.25, 1.3], "look": [-0.05, 0.25, 0]}, floor=-0.34,
        bodies=_spring_bodies("Vazan ko 3 cm kheench kar chhodte hain."),
        knobs=[knob("m", "Vazan m", "m", 50, 500, 50, 200, "g", 0.001),
               knob("k", "Spring badliye (k chhupa hai)", "k", 10, 40, 1, 20, "N/m", hidden=True)],
        instruments=[inst("sw", "stopwatch", "Stopwatch (10 dolan)"),
                     inst("gr", "graph", "x samay ke saath", "x", k=100, xlabel="t (s)")],
        table={"columns": [col("m", "m", "knob:m", "g", 0.001), col("T", "T = t₁₀ ÷ 10", "inst:sw", "s", div=10, digits=3)],
               "calc": "spring_k_shm", "rows_min": 3, "truth": "p.k", "result_digits": 1},
        steps=["Vazan 200 g rakhiye, Chalao dabaiye.", "10 dolan ka samay naapiye, record kijiye.",
               "Vazan badal kar dohraiye.", "k = 4π²m/T² ka ausat dekhiye."],
        theory="Spring par latke vazan ka dolan saral aavart gati (SHM) hai: T = 2π√(m/k). Bhaari vazan, dheere dolan.",
        tour=[{"say": "Vazan ko 3 centimetre kheench kar chhod diya hai. Dekhiye: upar-neeche ek jaisa dolan.", "run": True},
              {"set": {"m": 450}, "say": "Bhaari vazan: dolan dheere. T, vazan ke square root ke saath badhta hai."}],
        questions=[{"q": "Vazan 4 guna karne par T?", "options": ["2 guna", "4 guna", "Aadha"], "answer": 0,
                    "why": "T ∝ √m."}],
        sources=[S11, SIM],
        check={"params": {"m": 0.2}, "reading": "T", "textbook": "spring_T"},
    )


def incline() -> dict:
    return lab(
        id="inclined-plane-friction", title="Jhuka tal aur gharshan", group="Physics · Mechanics", level="Class XI",
        topic="Laws of Motion", aim="Block ko jhuke tal par upar chalane ke liye kam se kam bal naapiye aur gharshan gunaank μ nikaaliye.",
        kernel="incline", params={"len": 1.4}, autorun=True,
        camera={"pos": [0.3, 0.2, 2.2], "look": [0.1, -0.1, 0]}, floor=-0.62,
        bodies=[
            B("table", "box", name="Mez", size=[2.0, 0.04, 0.6], pos=[0.2, -0.6, 0], color="wood", cut=False),
            B("pivot", "box", size=[0.02, 0.02, 0.32], pos=[-0.6, -0.56, 0], color="black", bind={"rz": "p.angle"}),
            B("plank", "box", name="Jhuka tal (plank)", info="Iska kona θ knob se badaliye.", size=[1.5, 0.03, 0.3],
              pos=[0.75, 0, 0], parent="pivot", color="wood"),
            B("block", "box", name="Lakdi ka block", info="Jab tak gharshan rok sake, block ruka rehta hai.",
              size=[0.12, 0.08, 0.1], pos=[0, 0.055, 0], parent="pivot", color="#8c5a2b", bind={"x": "s"}),
            B("pulley", "torus", name="Ghirni (pulley)", r=0.03, tube=0.008, pos=[1.52, 0.03, 0], parent="pivot", color="steel"),
            B("hanger", "box", size=[0.001, 0.001, 0.001], pos=[1.52, 0.03, 0], parent="pivot", bind={"rz": {"var": "p.angle", "k": -1}}),
            B("pan", "cylinder", name="Palda (pan) + vazan", info="Vazan ka bal block ko dhaage se upar kheenchta hai.", r=0.05,
              h=0.02, pos=[0.035, -0.4, 0], parent="hanger", color="brass"),
            B("str1", "rope", a={"body": "block", "off": [0.06, 0, 0]}, b={"body": "pulley", "off": [0, 0.03, 0]}, r=0.0012, color="ink"),
            B("str2", "rope", a={"body": "pulley", "off": [0.03, 0, 0]}, b={"body": "pan", "off": [0, 0.01, 0]}, r=0.0012, color="ink"),
        ],
        knobs=[knob("ang", "Tal ka kona θ", "angle", 5, 45, 1, 20, "°", DEG, reset=True),
               knob("F", "Palde mein vazan", "F", 0, 1200, 10, 0, "g", 0.0098, reset=True,
                    hint="Dheere badhaiye; jis vazan par block upar chalna shuru kare, woh record kijiye."),
               knob("mu", "Satah (gharshan μ chhupa)", "mu", 0.1, 0.6, 0.05, 0.3, hidden=True, reset=True)],
        instruments=[inst("mv", "readout", "Block chal raha hai? (1 = haan)", "moving", digits=0),
                     inst("acc", "readout", "Tvaran a", "a", unit="m/s²", digits=2)],
        table={"columns": [col("angle", "Kona θ", "knob:ang", "°", DEG, digits=0), col("F", "Kam se kam vazan", "knob:F", "g", 0.0098, digits=0)],
               "calc": "incline_mu", "rows_min": 2, "truth": "p.mu", "result_digits": 2},
        steps=["Kona 20° rakhiye.", "Palde mein vazan 10 g karke badhaiye.", "Jis vazan par block upar chalne lage, record kijiye.",
               "Kona 25°, 30° par dohraiye.", "μ = (F - mg sinθ)/(mg cosθ) ka ausat dekhiye."],
        theory="Block ko upar chalane ke liye bal F = mg(sinθ + μcosθ). Gharshan bal satah ke saath, chalne ki disha ke ulta. "
               "Is lab mein sthir aur gatik gharshan ka μ ek hi maana gaya hai.",
        tour=[{"say": "Jhuke tal par 1 kilo ka block hai. Dhaaga ghirni se hokar palde tak jaata hai."},
              {"set": {"F": 500}, "say": "500 gram: block abhi bhi ruka hai. Gharshan aur vazan ka hissa usse rok rahe hain."},
              {"set": {"F": 800}, "say": "800 gram: ab block upar chal pada. Iske beech kahin seema hai: wahi naapni hai."}],
        questions=[{"q": "Kona badhane par block ko upar chalane ke liye vazan?", "options": ["Zyada chahiye", "Kam chahiye", "Utna hi"],
                    "answer": 0, "why": "sinθ badhta hai: vazan ka neeche wala hissa badhta hai."}],
        sources=[S11, SIM],
        check={"params": {"angle": 0.3491}, "reading": "F_min", "textbook": "incline_Fmin"},
    )


def stokes() -> dict:
    return lab(
        id="terminal-velocity", title="Stokes ka niyam: antim veg", group="Physics · Mechanics", level="Class XI",
        topic="Mechanical Properties of Fluids", aim="Glycerine mein girti steel ki goli ka antim veg naapiye aur shyanata η nikaaliye.",
        kernel="stokes", speeds=[1, 5, 20, 50], speed=5,
        camera={"pos": [0.4, -0.3, 1.5], "look": [0, -0.4, 0]}, floor=-1.0,
        bodies=[
            B("jar", "cylinder", name="Glycerine ka jaar", info="Lamba, chauda jaar: deewar ka asar kam.", r=0.05, h=0.9, open=True,
              pos=[0, -0.45, 0], color="glass", opacity=0.25),
            B("liq", "cylinder", name="Glycerine", r=0.048, h=0.86, pos=[0, -0.47, 0], color="glycerine", opacity=0.35),
            B("m1", "torus", name="Pehla nishaan (0.30 m)", r=0.052, tube=0.002, pos=[0, -0.3, 0], rot=[1.5708, 0, 0], color="red"),
            B("m2", "torus", name="Doosra nishaan (0.60 m)", r=0.052, tube=0.002, pos=[0, -0.6, 0], rot=[1.5708, 0, 0], color="red"),
            B("ball", "sphere", name="Steel ki goli", info="Dikhane ke liye 10 guna badi banayi hai.", r=0.01, pos=[0, 0, 0],
              color="steel", bind={"y": "ball_y", "sx": {"var": "p.r", "k": 1000}, "sy": {"var": "p.r", "k": 1000}, "sz": {"var": "p.r", "k": 1000}}),
            B("base", "box", size=[0.2, 0.02, 0.2], pos=[0, -0.91, 0], color="wood"),
        ],
        knobs=[knob("r", "Goli ki trijya r", "r", 0.5, 3, 0.1, 1, "mm", 0.001, reset=True),
               knob("eta", "Taral (η chhupa)", "eta", 0.5, 2.0, 0.01, 1.49, "Pa·s", hidden=True, reset=True)],
        instruments=[inst("sw", "stopwatch", "Stopwatch (do nishaanon ke beech)"),
                     inst("v", "readout", "Photogate veg", "v", k=100, unit="cm/s", digits=3)],
        table={"columns": [col("r", "r", "knob:r", "mm", 0.001), col("v", "Antim veg", "inst:v", "cm/s", 0.01, digits=3)],
               "calc": "stokes_eta", "rows_min": 2, "truth": "p.eta", "result_digits": 2,
               "hint": "Goli pehle nishaan se aage nikal jaaye (veg sthir), tab reading record kijiye."},
        steps=["r = 1 mm rakhiye, Chalao dabaiye.", "Goli do nishaanon ke beech sthir veg se girti hai: samay naapiye ya photogate dekhiye.",
               "Reading record kijiye.", "r badal kar dohraiye; v ∝ r²."],
        theory="Goli par neeche vazan, upar uchhaal aur shyan bal 6πηrv. Sab barabar hone par antim veg v = 2r²(ρ-σ)g / 9η.",
        tour=[{"say": "Glycerine bahut gaadha taral hai. Steel ki goli usmein chhodi jaati hai.", "run": True},
              {"say": "Kuch hi pal mein goli ka veg sthir ho jaata hai: yeh antim veg hai."},
              {"set": {"r": 2}, "say": "Doguni trijya: antim veg chaar guna. Kyunki v, r ke square ke saath badhta hai."}],
        questions=[{"q": "Trijya doguni karne par antim veg?", "options": ["2 guna", "4 guna", "Utna hi"], "answer": 1, "why": "v ∝ r²."}],
        sources=[S11, SIM],
        check={"params": {"r": 0.001}, "reading": "v_t", "textbook": "stokes_v"},
    )


# ======================================================================================================== HEAT
def _thermo(id, x, var, name) -> list[dict]:
    return [B(id + "_glass", "cylinder", name=name, r=0.006, h=0.3, pos=[x, 0.13, 0], color="glass", opacity=0.35),
            B(id + "_bulb", "sphere", r=0.009, pos=[x, -0.02, 0], color="mercury"),
            B(id + "_hg", "cylinder", r=0.0028, h=0.01, pos=[x, -0.01, 0], color="mercury",
              bind={"sy": {"var": var, "k": 0.25, "min": 0.01}, "y": {"var": var, "k": 0.00125}}),
            B(id + "_sc", "scale", length=0.25, spacing=0.0025, major=10, labels=True, label_step=10, tick=0.006, font=0.012,
              pos=[x + 0.008, -0.01, 0], rot=[0, 0, 1.5708], down=True)]


def cooling() -> dict:
    return lab(
        id="newtons-cooling", title="Newton ka thanda hone ka niyam", group="Physics · Heat", level="Class XI",
        topic="Thermal Properties of Matter", aim="Garam paani ke thande hone ka graph banaiye aur cooling constant k nikaaliye.",
        kernel="cooling", speed=10, speeds=[1, 5, 10, 30],
        camera={"pos": [0.25, 0.12, 0.6], "look": [0, 0.07, 0]}, floor=-0.1,
        bodies=[
            B("stand", "box", size=[0.3, 0.02, 0.2], pos=[0, -0.08, 0], color="wood"),
            B("beaker", "cylinder", name="Calorimeter / beaker", r=0.06, h=0.14, open=True, pos=[0, 0, 0], color="glass", opacity=0.3),
            B("water", "cylinder", name="Garam paani", r=0.057, h=0.11, pos=[0, -0.013, 0], color="water", opacity=0.55),
            *_thermo("t1", 0.02, "T", "Thermometer (0-100 °C)"),
        ],
        knobs=[knob("T0", "Shuru ka taapmaan", "T0", 60, 95, 1, 90, "°C", reset=True),
               knob("Ts", "Kamre ka taapmaan", "Ts", 15, 40, 1, 30, "°C", reset=True),
               knob("k", "Bartan + hawa (k chhupa)", "k", 0.005, 0.05, 0.001, 0.02, "1/s", hidden=True, reset=True)],
        instruments=[inst("T", "readout", "Thermometer", "T", unit="°C", lc=0.5, digits=1),
                     inst("sw", "stopwatch", "Samay"),
                     inst("gr", "graph", "T samay ke saath (cooling curve)", "T", xlabel="t (s)")],
        table={"columns": [col("t", "Samay t", "inst:sw", "s", digits=0), col("T", "Taapmaan T", "inst:T", "°C", digits=1)],
               "calc": "cooling_k", "rows_min": 3, "truth": "p.k", "result_digits": 4,
               "hint": "Chalao ke saath Stopwatch start kijiye; har 30-60 s par reading record kijiye."},
        steps=["Paani 90 °C, kamra 30 °C.", "Chalao + Stopwatch saath shuru.", "Har 30 s par T record kijiye (lagbhag 10 readings).",
               "Graph dekhiye: shuru mein tez, phir dheere thanda."],
        theory="Newton ka niyam: thande hone ki dar dT/dt = -k(T - Ts). Isliye T - Ts samay ke saath exponential ghatta hai.",
        tour=[{"say": "Beaker mein 90 degree ka paani, kamra 30 degree. Simulation 10 guna tez chal raha hai.", "run": True},
              {"say": "Shuru mein paani tez thanda hota hai, kyunki kamre se farq zyada hai. Graph tab dekhiye."}],
        questions=[{"q": "Paani 90 se 80 °C jaldi aata hai ya 50 se 40 °C?", "options": ["90 se 80", "50 se 40", "Barabar"], "answer": 0,
                    "why": "Kamre se farq jitna zyada, thande hone ki dar utni zyada."}],
        sources=[S11, SIM],
        check={"params": {}, "reading": "T60", "textbook": "cooling_T60"},
    )


def boyle() -> dict:
    return lab(
        id="boyles-law", title="Boyle ka niyam: P aur V", group="Physics · Heat", level="Class XI",
        topic="Kinetic Theory", aim="Sthir taapmaan par gas ka aayatan badal kar daab naapiye: PV sthir rehta hai?",
        kernel="boyle", autorun=True,
        camera={"pos": [0.25, 0.15, 0.7], "look": [0.04, 0.1, 0]}, floor=-0.02,
        bodies=[
            B("base", "box", size=[0.35, 0.02, 0.2], pos=[0.05, -0.01, 0], color="wood"),
            B("barrel", "cylinder", name="Syringe ki nali", r=0.03, h=0.3, open=True, pos=[0, 0.15, 0], color="glass", opacity=0.25),
            B("gas", "gas", name="Gas ke anu", info="Anu sirf samjhane ke liye; daab ideal gas niyam se aata hai.", size=[0.05, 0.1, 0.05],
              count=60, r=0.004, pos=[0, 0, 0], color="blue", illustrative=True, bind={"h": "piston_h"}),
            B("piston", "cylinder", name="Piston", r=0.029, h=0.01, pos=[0, 0, 0], color="black", bind={"y": "piston_h"}),
            B("prod", "cylinder", r=0.004, h=0.2, pos=[0, 0.105, 0], parent="piston", color="steel"),
            B("dialc", "cylinder", name="Daab gauge (kPa)", r=0.05, h=0.01, pos=[0.13, 0.08, 0], rot=[1.5708, 0, 0], color="white"),
            B("ring", "torus", r=0.05, tube=0.003, pos=[0.13, 0.08, 0.006], color="ink"),
            B("ndl", "needle", length=0.042, pos=[0.13, 0.08, 0.008], color="red",
              bind={"rz": {"var": "P_kPa", "k": -0.012, "c": 1.2, "min": -1.3, "max": 1.3}}),
            B("lbl", "text", text="kPa", size=0.015, pos=[0.13, 0.055, 0.01]),
        ],
        knobs=[knob("V", "Aayatan V", "V", 20, 200, 5, 100, "mL", 1e-6),
               knob("T", "Taapmaan (Boyle mein sthir)", "Temp", 250, 400, 10, 300, "K")],
        instruments=[inst("P", "readout", "Daab P", "P_kPa", unit="kPa", digits=1),
                     inst("PV", "readout", "P × V", "PV", unit="J", digits=3),
                     inst("gr", "graph", "P vs V", "P_kPa", x="V_mL", xlabel="V (mL)", dots=True)],
        table={"columns": [col("P", "Daab P", "inst:P", "kPa", 1000, digits=1), col("V", "Aayatan V", "knob:V", "mL", 1e-6)],
               "calc": "boyle_pv", "rows_min": 3, "result_digits": 3},
        steps=["V = 100 mL, daab padhiye, record kijiye.", "V ko 80, 60, 40 mL kijiye; har baar record.",
               "PV ka ausat dekhiye: har reading mein lagbhag barabar?", "Graph P vs V hyperbola banta hai."],
        theory="Sthir taapmaan par di hui gas ke liye P ∝ 1/V, yaani PV = nRT sthir. Anu deewar se zyada baar takraate hain jab jagah kam ho.",
        tour=[{"say": "Syringe mein band gas. Piston neeche dabane par aayatan ghatta hai."},
              {"set": {"V": 50}, "say": "Aadha aayatan: daab doguna. Anu deewaron se doguni baar takraate hain."},
              {"set": {"V": 100}, "say": "Table mein P aur V record kijiye: P guna V har baar lagbhag barabar aayega."}],
        questions=[{"q": "Aayatan aadha karne par daab?", "options": ["Doguna", "Aadha", "Utna hi"], "answer": 0, "why": "PV sthir."}],
        sources=[S11, SIM],
        check={"params": {"V": 5e-5}, "reading": "P", "textbook": "boyle_P"},
    )


def mixtures() -> dict:
    return lab(
        id="specific-heat-mixtures", title="Mishran vidhi: vishisht ushma", group="Physics · Heat", level="Class XI",
        topic="Thermal Properties of Matter", aim="Garam dhaatu ko paani mein daal kar antim taapmaan naapiye aur dhaatu ki vishisht ushma c nikaaliye.",
        kernel="mixtures", speed=20, speeds=[5, 20, 60],
        camera={"pos": [0.25, 0.12, 0.55], "look": [0, 0.05, 0]}, floor=-0.08,
        bodies=[
            B("jacket", "cylinder", name="Bahari bartan (insulation)", r=0.07, h=0.12, open=True, pos=[0, 0, 0], color="#cfd4da", opacity=0.25),
            B("cal", "cylinder", name="Taambe ka calorimeter", r=0.05, h=0.1, open=True, pos=[0, -0.005, 0], color="copper", opacity=0.6),
            B("water", "cylinder", name="Paani", r=0.048, h=0.07, pos=[0, -0.018, 0], color="water", opacity=0.55),
            B("solid", "box", name="Garam dhaatu ka tukda", info="Ise ubalte paani mein 100 °C tak garam kiya tha.", size=[0.03, 0.03, 0.03],
              pos=[-0.015, -0.035, 0], color="steel"),
            B("stir", "cylinder", name="Hilaane ki chhad", r=0.002, h=0.16, pos=[-0.03, 0.04, 0.02], rot=[0, 0, 0.2], color="copper"),
            *_thermo("tw", 0.025, "Tw", "Thermometer: paani"),
        ],
        knobs=[knob("m1", "Dhaatu ka vazan", "m1", 50, 200, 10, 100, "g", 0.001, reset=True),
               knob("T1", "Dhaatu ka taapmaan", "T1", 60, 100, 1, 100, "°C", reset=True),
               knob("m2", "Paani ka vazan", "m2", 100, 250, 10, 150, "g", 0.001, reset=True),
               knob("c1", "Dhaatu (c chhupa)", "c1", 380, 900, 10, 900, "J/(kg·K)", hidden=True, reset=True)],
        instruments=[inst("Ts", "readout", "Dhaatu ka taapmaan", "Ts", unit="°C", lc=0.1, digits=1),
                     inst("Tw", "readout", "Paani + calorimeter", "Tw", unit="°C", lc=0.1, digits=1),
                     inst("gr", "graph", "Paani ka taapmaan", "Tw", xlabel="t (s)")],
        table={"columns": [col("Tf", "Antim taapmaan", "inst:Tw", "°C", digits=1)], "calc": "mix_c", "rows_min": 1,
               "truth": "p.c1", "result_digits": 0, "hint": "Jab dono taapmaan barabar ho jaayein, Tf record kijiye."},
        steps=["Dhaatu 100 g, 100 °C; paani 150 g, 25 °C.", "Chalao dabaiye: dhaatu paani mein hai.",
               "Dono taapmaan milne tak rukiye; Tf record kijiye.", "c = (m₂c₂ + m_c c_c)(Tf - T₂) / m₁(T₁ - Tf)."],
        theory="Ushma ka santulan: dhaatu ne jo ushma di = paani + calorimeter ne jo li (bahar koi ushma nahi gayi maana hai).",
        safety="Asli lab mein garam dhaatu chimte se uthaiye; ubalta paani jala sakta hai.",
        tour=[{"say": "Taambe ke calorimeter mein 25 degree ka paani. Isme 100 degree ki dhaatu daali hai.", "run": True},
              {"say": "Dhaatu thandi ho rahi hai aur paani garam: dono ek taapmaan par mil jaayenge."}],
        questions=[{"q": "Kam vishisht ushma wali dhaatu (jaise taamba) daalne par paani ka taapmaan?", "options": ["Kam badhega", "Zyada badhega", "Utna hi"],
                    "answer": 0, "why": "Kam c = kam ushma jama, to paani kam garam hota hai."}],
        sources=[S11, SIM],
        check={"params": {}, "reading": "Tf", "textbook": "mix_Tf"},
    )


# ======================================================================================================== WAVES
def resonance() -> dict:
    return lab(
        id="resonance-tube", title="Resonance tube: dhwani ka veg", group="Physics · Waves", level="Class XI",
        topic="Waves", aim="Paani ka star badal kar do resonance lambaaiyaan l₁, l₂ dhoondhiye aur v = 2f(l₂ - l₁) nikaaliye.",
        kernel="resonance", params={"h": 0.1}, autorun=True,
        camera={"pos": [0.45, -0.3, 1.5], "look": [0.05, -0.45, 0]}, floor=-1.05,
        bodies=[
            B("tube", "cylinder", name="Resonance tube", info="Neeche se paani: upar khula, paani par band.", r=0.02, h=1.0, open=True,
              pos=[0, -0.5, 0], color="glass", opacity=0.25),
            B("water", "cylinder", name="Paani ka star", r=0.019, h=1.0, pos=[0, -0.5, 0], color="water", opacity=0.6,
              bind={"y": {"var": "p.h", "k": -0.5}, "sy": {"var": "p.h", "k": -1, "c": 1}}),
            B("fork1", "box", name="Tuning fork", info="Isse ek hi aavritti f ki dhwani.", size=[0.006, 0.1, 0.006], pos=[-0.012, 0.08, 0], color="steel"),
            B("fork2", "box", size=[0.006, 0.1, 0.006], pos=[0.012, 0.08, 0], color="steel"),
            B("forkb", "box", size=[0.03, 0.008, 0.006], pos=[0, 0.03, 0], color="steel"),
            B("forkh", "cylinder", r=0.003, h=0.05, pos=[0, 0.005, 0], color="steel"),
            B("ruler", "scale", name="Meter scale (cm)", length=1.0, spacing=0.01, major=10, labels=True, label_step=10, tick=0.01, font=0.02,
              pos=[0.03, 0, 0], rot=[0, 0, -1.5708]),
            B("lvl", "box", name="Paani ka nishaan", size=[0.06, 0.002, 0.002], pos=[0.03, 0, 0], color="red", bind={"y": {"var": "p.h", "k": -1}}),
            *dial("db", [0.25, -0.35, 0], "Loudness meter", "Jab hawa ka stambh resonance mein ho, awaaz sabse tez."),
            needle("dbn", [0.25, -0.35, 0], "loud", -2.4, 1.2),
            B("stand", "box", size=[0.3, 0.03, 0.3], pos=[0, -1.02, 0], color="wood"),
        ],
        knobs=[knob("h", "Hawa ka stambh (paani tak)", "h", 2, 95, 0.1, 10, "cm", 0.01,
                    hint="Dheere neeche laaiye; jahan awaaz sabse tez ho, record kijiye."),
               knob("f", "Tuning fork", "f", 256, 512, 1, 512, "Hz"),
               knob("Tc", "Kamre ka taapmaan", "Tc", 0, 40, 1, 20, "°C")],
        instruments=[inst("ld", "meter", "Awaaz kitni tez", "loud", range=[0, 1], digits=2),
                     inst("gr", "graph", "Awaaz vs hawa ka stambh", "loud", x="p.h", xk=100, xlabel="h (cm)", dots=True)],
        table={"columns": [col("h", "Resonance lambaai", "knob:h", "cm", 0.01, digits=1)], "calc": "res_v", "rows_min": 2,
               "result_digits": 1, "hint": "Pehli tez awaaz (l₁) aur doosri (l₂) dono record kijiye."},
        steps=["Fork 512 Hz, hawa ka stambh 10 cm.", "Dheere stambh badhaiye; pehli tez awaaz par record (l₁ ≈ 15-16 cm).",
               "Aage badhaiye; doosri tez awaaz par record (l₂ ≈ 49 cm).", "v = 2f(l₂ - l₁): end correction kat jaata hai."],
        theory="Ek sire se band nali mein resonance tab hota hai jab l + e = λ/4, 3λ/4, ... (e = 0.3d end correction). "
               "Isliye l₂ - l₁ = λ/2 aur v = fλ = 2f(l₂ - l₁). 0 °C par v = 331.3 m/s; har °C par lagbhag 0.6 m/s badhta hai.",
        tour=[{"say": "Nali mein paani hai; upar tuning fork baj raha hai. Paani neeche karke hawa ka stambh lamba karte hain."},
              {"set": {"h": 15.6}, "say": "Yahan awaaz sabse tez hai: pehla resonance. Hawa ka stambh lagbhag chauthai tarang-lambaai hai."},
              {"set": {"h": 49.1}, "say": "Yeh doosra resonance hai. Dono ka farq aadhi tarang-lambaai: isse dhwani ka veg nikalta hai."}],
        questions=[{"q": "Kamre ka taapmaan badhne par resonance lambaai?", "options": ["Badhegi", "Ghategi", "Utni hi"], "answer": 0,
                    "why": "Garam hawa mein v zyada, to λ = v/f lamba."}],
        sources=[S11, SIM],
        check={"params": {}, "rows": [{"take": {"l1": "h"}}, {"take": {"l2": "h"}}], "calc": "res_v", "textbook": "sound_v"},
    )


def sonometer() -> dict:
    return lab(
        id="sonometer", title="Sonometer: taar ki aavritti", group="Physics · Waves", level="Class XI",
        topic="Waves", aim="Bridge khiska kar taar ko tuning fork ke saath resonance mein laaiye; l aur T se taar ka μ nikaaliye.",
        kernel="sonometer", params={"l": 0.3}, autorun=True,
        camera={"pos": [0.5, 0.4, 1.35], "look": [0.5, -0.05, 0]}, floor=-0.3,
        bodies=[
            B("box", "box", name="Sonometer ka khokhla box", size=[1.1, 0.08, 0.16], pos=[0.47, -0.04, 0], color="wood"),
            B("brA", "box", name="Sthir bridge", size=[0.012, 0.03, 0.12], pos=[0, 0.015, 0], color="#d8c8a8"),
            B("brB", "box", name="Khisakne wala bridge", info="Ise khiska kar taar ki lambaai l badaliye.", size=[0.012, 0.03, 0.12],
              pos=[0, 0.015, 0], color="#d8c8a8", bind={"x": "p.l"}),
            B("wire0", "rope", a=[-0.06, 0.03, 0], b=[1.03, 0.03, 0], r=0.0008, color="steel"),
            B("wire", "rope", name="Kampit taar", a=[0, 0.031, 0], b={"body": "brB", "off": [0, 0.016, 0]}, bow="amp", color="steel"),
            B("rider", "cone", name="Kaagaz ka sawaar", info="Resonance par yeh uchhal kar gir jaata hai.", r=0.008, h=0.012,
              pos=[0, 0.04, 0], rot=[3.1416, 0, 0], color="red", bind={"x": {"var": "p.l", "k": 0.5}, "y": {"var": "loud", "k": 0.03}}),
            B("pulley", "torus", r=0.025, tube=0.006, pos=[1.05, 0.005, 0], color="steel"),
            B("hang", "rope", a=[1.075, 0.005, 0], b=[1.075, -0.22, 0], r=0.0008, color="ink"),
            B("wt", "cylinder", name="Latka vazan (tanaav T)", r=0.025, h=0.06, pos=[1.075, -0.25, 0], color="brass"),
            B("ruler", "scale", length=1.0, spacing=0.01, major=10, labels=True, label_step=10, tick=0.008, font=0.016, pos=[0, 0.0, 0.081]),
            *dial("db", [0.45, -0.2, 0.25], "Resonance meter"),
            needle("dbn", [0.45, -0.2, 0.25], "loud", -2.4, 1.2),
        ],
        knobs=[knob("l", "Bridges ke beech lambaai l", "l", 10, 90, 0.1, 30, "cm", 0.01),
               knob("Tn", "Latka vazan", "Tn", 1, 6, 0.5, 4, "kg", 9.8),
               knob("f", "Tuning fork", "f", 256, 512, 1, 256, "Hz"),
               knob("mu", "Taar (μ chhupa)", "mu", 0.0005, 0.003, 0.0001, 0.001, "kg/m", hidden=True)],
        instruments=[inst("ld", "meter", "Kampan kitna zyada", "loud", range=[0, 1], digits=2)],
        table={"columns": [col("f", "Fork f", "knob:f", "Hz"), col("l", "Resonance lambaai l", "knob:l", "cm", 0.01, digits=1),
                           col("Tn", "Vazan", "knob:Tn", "kg", 9.8)],
               "calc": "sono_mu", "rows_min": 2, "truth": "p.mu", "result_digits": 5},
        steps=["Vazan 4 kg, fork 256 Hz.", "Bridge khiskaiye: jahan sawaar uchhle (meter full), record kijiye.",
               "Doosre fork (320, 384, 512 Hz) ke saath dohraiye: f × l sthir?", "μ = T / (4 l² f²)."],
        theory="Taar ki mool aavritti f = (1/2l)√(T/μ). Sthir T par f × l sthir; sthir f par l ∝ √T.",
        tour=[{"say": "Sonometer: ek taar, do bridge, aur latka vazan jo tanaav deta hai."},
              {"set": {"l": 38.7}, "say": "Yahan taar fork ke saath resonance mein hai: sawaar uchhal raha hai."},
              {"set": {"f": 512, "l": 19.3}, "say": "Doguni aavritti ka fork: lambaai aadhi. f guna l sthir rehta hai."}],
        questions=[{"q": "Tanaav 4 guna karne par resonance lambaai (same fork)?", "options": ["2 guna", "4 guna", "Aadhi"], "answer": 0,
                    "why": "l ∝ √T."}],
        sources=[S11, SIM],
        check={"params": {}, "reading": "l_res", "textbook": "sono_l"},
    )


# ======================================================================================================== ELECTRICITY
def _wire(id, pts, color="red") -> dict:
    return B(id, "wire", pts=pts, r=0.003, color=color)


def ohm() -> dict:
    net = {"nodes": 4, "els": [
        {"id": "E", "kind": "V", "a": 1, "b": 0, "value": "Eb"}, {"id": "K", "kind": "S", "a": 1, "b": 4, "param": "key"},
        {"id": "AM", "kind": "R", "a": 4, "b": 2, "value": 0.01}, {"id": "RH", "kind": "R", "a": 2, "b": 3, "value": {"param": "Rh", "k": 1, "c": 0.01}},
        {"id": "RX", "kind": "R", "a": 3, "b": 0, "value": "Rx"}, {"id": "VM", "kind": "R", "a": 3, "b": 0, "value": 1e6}]}
    return lab(
        id="ohms-law", title="Ohm ka niyam: V aur I", group="Physics · Electricity", level="Class XII",
        topic="Current Electricity", aim="Rheostat se dhaara badal kar V aur I naapiye; V/I se taar ka pratirodh R nikaaliye.",
        kernel="circuit", cfg={"net": net}, params={"Eb": 3.0, "Rh": 10.0, "Rx": 5.0, "key": 1.0}, autorun=True,
        camera={"pos": [0.0, 0.95, 0.95], "look": [0, 0, 0]}, floor=-0.03,
        bodies=[
            board(1.0, 0.75),
            B("bat", "cylinder", name="Battery (3 V)", r=0.03, h=0.12, pos=[-0.38, 0.03, 0.22], rot=[0, 0, 1.5708], color="#2b2f36"),
            *dial("am", [0.0, 0.0, 0.22], "Ammeter (0-1.5 A)", "Series mein: poori dhaara isse guzarti hai."),
            needle("amn", [0.0, 0.0, 0.22], "I_AM", -1.6, 1.2),
            B("rh", "cylinder", name="Rheostat", info="Slider khiska kar pratirodh, isliye dhaara, badaliye.", r=0.025, h=0.22,
              pos=[0.35, 0.03, 0.22], rot=[0, 0, 1.5708], color="#c9b07a"),
            B("rhs", "box", name="Rheostat slider", size=[0.02, 0.03, 0.06], pos=[0.25, 0.065, 0.22], color="black",
              bind={"x": {"var": "p.Rh", "k": 0.01}}),
            B("rx", "spring", name="Pratirodh taar (coil)", info="Iska pratirodh naapna hai.", a=[-0.15, 0.03, -0.12], b=[0.15, 0.03, -0.12],
              r=0.012, turns=18, wire=0.0015, color="copper"),
            *dial("vm", [0.0, 0.0, -0.3], "Voltmeter (0-3 V)", "Taar ke parallel: uske siron ka vibhavantar."),
            needle("vmn", [0.0, 0.0, -0.3], "V_VM", -0.8, 1.2),
            _wire("w1", [[-0.32, 0.03, 0.22], [-0.06, 0.03, 0.22]]), _wire("w2", [[0.06, 0.03, 0.22], [0.24, 0.03, 0.22]]),
            _wire("w3", [[0.46, 0.03, 0.22], [0.46, 0.03, -0.12], [0.15, 0.03, -0.12]]),
            _wire("w4", [[-0.15, 0.03, -0.12], [-0.44, 0.03, -0.12], [-0.44, 0.03, 0.22]], "black"),
            _wire("w5", [[-0.15, 0.03, -0.12], [-0.06, 0.03, -0.3]], "black"), _wire("w6", [[0.15, 0.03, -0.12], [0.06, 0.03, -0.3]]),
        ],
        knobs=[knob("Rh", "Rheostat", "Rh", 0, 20, 0.5, 10, "Ω"), knob("key", "Chaabi (0 khuli / 1 band)", "key", 0, 1, 1, 1),
               knob("Rx", "Taar badliye (R chhupa)", "Rx", 2, 10, 0.5, 5, "Ω", hidden=True)],
        instruments=[inst("I", "readout", "Ammeter", "I_AM", unit="A", lc=0.01, digits=2),
                     inst("V", "readout", "Voltmeter", "V_VM", unit="V", lc=0.01, digits=2),
                     inst("gr", "graph", "V vs I", "V_VM", x="I_AM", xlabel="I (A)", dots=True)],
        table={"columns": [col("V", "V", "inst:V", "V", digits=2), col("I", "I", "inst:I", "A", digits=2)], "calc": "ohm_R",
               "rows_min": 3, "truth": "p.Rx", "result_digits": 2},
        steps=["Chaabi band kijiye.", "Rheostat 20 Ω se shuru: V aur I record.", "Rheostat 15, 10, 5 Ω: har baar record.",
               "Graph V vs I seedhi rekha: dhalaan = R."],
        theory="Ohm ka niyam: sthir taapmaan par V = IR. Ammeter series mein (bahut kam pratirodh), voltmeter parallel mein (bahut zyada).",
        safety="Asli circuit mein dhaara zyada der band mat chhodiye: taar garam hokar R badal jaata hai.",
        tour=[{"say": "Battery, chaabi, ammeter, rheostat aur taar: sab series mein. Voltmeter taar ke parallel."},
              {"set": {"Rh": 2}, "say": "Rheostat kam kiya: dhaara badhi, aur taar par voltage bhi badha."},
              {"set": {"Rh": 10}, "say": "Har reading mein V divided by I lagbhag barabar aata hai: yahi R hai."}],
        questions=[{"q": "Voltmeter ko series mein lagaane par?", "options": ["Dhaara lagbhag ruk jaayegi", "Kuch nahi badlega", "Dhaara badhegi"],
                    "answer": 0, "why": "Voltmeter ka pratirodh bahut zyada hota hai."}],
        sources=[S12, SIM],
        check={"params": {"key": 1.0}, "measure": {"mode": "ratio", "num": "V_VM", "den": "I_AM", "as": "R", "vars": []},
               "reading": "R", "textbook": "ohm_R"},
    )


def meter_bridge() -> dict:
    net = {"nodes": 4, "els": [
        {"id": "E", "kind": "V", "a": 1, "b": 4, "value": 2.0}, {"id": "K", "kind": "S", "a": 4, "b": 0, "param": "key"},
        {"id": "WA", "kind": "R", "a": 1, "b": 2, "value": {"param": "lj", "k": 2.0}},
        {"id": "WB", "kind": "R", "a": 2, "b": 0, "value": {"param": "lj", "k": -2.0, "c": 2.0}},
        {"id": "RK", "kind": "R", "a": 1, "b": 3, "value": "Rk"}, {"id": "SX", "kind": "R", "a": 3, "b": 0, "value": "Sx"},
        {"id": "G", "kind": "R", "a": 3, "b": 2, "value": 50.0}]}
    return lab(
        id="meter-bridge", title="Meter bridge: anjaan pratirodh", group="Physics · Electricity", level="Class XII",
        topic="Current Electricity", aim="Jockey khiska kar galvanometer ko shoonya par laaiye (null point) aur S = R(100 - l)/l nikaaliye.",
        kernel="circuit", cfg={"net": net}, params={"lj": 0.5, "Rk": 4.0, "Sx": 6.0, "key": 1.0}, autorun=True,
        camera={"pos": [0.0, 0.7, 0.8], "look": [0, 0, 0.02]}, floor=-0.03,
        bodies=[
            board(1.25, 0.6),
            B("strip", "box", name="Taambe ki pattiyan", size=[1.1, 0.006, 0.03], pos=[0, 0.006, -0.12], color="copper"),
            B("wire", "rope", name="1 m ka manganin taar", a=[-0.5, 0.012, 0.05], b=[0.5, 0.012, 0.05], r=0.0012, color="steel"),
            B("ruler", "scale", name="Meter scale", length=1.0, spacing=0.01, major=10, labels=True, label_step=10, tick=0.012, font=0.02,
              pos=[-0.5, 0.002, 0.09], rot=[-1.5708, 0, 0]),
            B("jockey", "cone", name="Jockey", info="Taar ko halke se chhuiye: dabaaiye mat, ghisaai se R badalta hai.", r=0.01, h=0.05,
              pos=[-0.5, 0.04, 0.05], rot=[3.1416, 0, 0], color="brass", bind={"x": "p.lj"}),
            B("rk", "box", name="Resistance box R", info="Gyaat pratirodh: knob se chuniye.", size=[0.14, 0.05, 0.08], pos=[-0.25, 0.025, -0.2], color="#2b2f36"),
            B("sx", "spring", name="Anjaan taar S", a=[0.18, 0.02, -0.2], b=[0.32, 0.02, -0.2], r=0.01, turns=14, wire=0.0015, color="copper"),
            *dial("g", [0.0, 0.0, -0.2], "Galvanometer", "Shoonya par (null point) koi dhaara nahi."),
            needle("gn", [0.0, 0.0, -0.2], "I_G", -40000.0),
            B("bat", "cylinder", name="Cell + chaabi", r=0.025, h=0.1, pos=[0, 0.025, 0.24], rot=[0, 0, 1.5708], color="#2b2f36"),
            _wire("w1", [[-0.55, 0.015, -0.12], [-0.55, 0.015, 0.24], [-0.05, 0.015, 0.24]]),
            _wire("w2", [[0.55, 0.015, -0.12], [0.55, 0.015, 0.24], [0.05, 0.015, 0.24]], "black"),
            B("gw", "rope", a=[0.0, 0.04, -0.15], b={"body": "jockey", "off": [0, -0.02, 0]}, r=0.0012, color="ink"),
        ],
        knobs=[knob("lj", "Jockey ki jagah l", "lj", 1, 99, 0.1, 50, "cm", 0.01, hint="Galvanometer shoonya kahan hota hai?"),
               knob("Rk", "Resistance box R", "Rk", 1, 20, 1, 4, "Ω"),
               knob("Sx", "Anjaan taar (S chhupa)", "Sx", 2, 15, 0.5, 6, "Ω", hidden=True)],
        instruments=[inst("G", "readout", "Galvanometer", "I_G", k=1e6, unit="µA", digits=1),
                     inst("gm", "meter", "Galvanometer (|dhaara|, kam = behtar)", "I_G", k=-1e5, range=[-1, 1], digits=2)],
        table={"columns": [col("R", "R", "knob:Rk", "Ω"), col("l", "Null point l", "knob:lj", "cm", 0.01, digits=1)], "calc": "bridge_S",
               "rows_min": 2, "truth": "p.Sx", "result_digits": 2},
        steps=["R = 4 Ω chuniye.", "Jockey khiskaiye: galvanometer shoonya kahan hota hai?", "Null point l record kijiye.",
               "R badal kar (null point 30-70 cm ke beech rakhiye) dohraiye.", "S = R(100 - l)/l ka ausat."],
        theory="Meter bridge Wheatstone bridge hai: null par R/S = l/(100 - l). Null point beech mein ho to galti sabse kam.",
        tour=[{"say": "Ek meter lamba taar, ek taraf resistance box R, doosri taraf anjaan taar S. Beech mein galvanometer."},
              {"set": {"lj": 40}, "say": "40 centimetre par galvanometer lagbhag shoonya: yahi null point hai."},
              {"set": {"lj": 70}, "say": "Yahan dhaara hai: sui ek taraf. Null point par R by S barabar l by 100 minus l."}],
        questions=[{"q": "Null point par galvanometer mein dhaara?", "options": ["Shoonya", "Sabse zyada", "Battery jitni"], "answer": 0,
                    "why": "B aur J ka vibhav barabar hota hai."}],
        sources=[S12, SIM],
        check={"params": {"Rk": 4.0, "Sx": 6.0}, "measure": {"mode": "null", "param": "lj", "var": "I_G", "lo": 0.01, "hi": 0.99},
               "reading": "lj", "textbook": "bridge_l"},
    )


def potentiometer() -> dict:
    net = {"nodes": 6, "els": [
        {"id": "E0", "kind": "V", "a": 3, "b": 0, "value": "E0"}, {"id": "RH", "kind": "R", "a": 3, "b": 1, "value": "Rh"},
        {"id": "WA", "kind": "R", "a": 1, "b": 2, "value": {"param": "lj", "k": 4.0}},
        {"id": "WB", "kind": "R", "a": 2, "b": 0, "value": {"param": "lj", "k": -4.0, "c": 4.0}},
        {"id": "EC", "kind": "V", "a": 1, "b": 4, "value": "Ec"}, {"id": "RI", "kind": "R", "a": 4, "b": 5, "value": "r_int"},
        {"id": "G", "kind": "R", "a": 5, "b": 2, "value": 50.0}, {"id": "K2", "kind": "S", "a": 5, "b": 6, "param": "k2"},
        {"id": "RB", "kind": "R", "a": 6, "b": 1, "value": "Rb"}]}
    return lab(
        id="potentiometer-internal-resistance", title="Potentiometer: cell ka aantarik pratirodh", group="Physics · Electricity",
        level="Class XII", topic="Current Electricity",
        aim="K₂ khuli aur band karke do balancing lambaaiyaan l₁, l₂ naapiye; r = R(l₁ - l₂)/l₂.",
        kernel="circuit", cfg={"net": net}, params={"lj": 0.3, "E0": 6.0, "Rh": 2.0, "Ec": 1.5, "r_int": 1.0, "Rb": 10.0, "k2": 0.0},
        autorun=True, camera={"pos": [0.0, 0.7, 0.85], "look": [0, 0, 0]}, floor=-0.03,
        bodies=[
            board(1.25, 0.65),
            B("wire", "rope", name="Potentiometer taar (4 m, yahan chhota dikhaya)", a=[-0.5, 0.012, 0.05], b=[0.5, 0.012, 0.05], r=0.0012, color="steel"),
            B("ruler", "scale", name="Scale (0-400 cm)", length=1.0, spacing=0.0125, major=8, labels=True, label_step=50, tick=0.012,
              font=0.02, pos=[-0.5, 0.002, 0.09], rot=[-1.5708, 0, 0]),
            B("jockey", "cone", name="Jockey", r=0.01, h=0.05, pos=[-0.5, 0.04, 0.05], rot=[3.1416, 0, 0], color="brass", bind={"x": "p.lj"}),
            B("drv", "box", name="Chalak battery (6 V) + rheostat", size=[0.2, 0.05, 0.08], pos=[-0.35, 0.025, 0.25], color="#2b2f36"),
            B("cell", "cylinder", name="Jaanch wala cell (Leclanché)", info="Iska aantarik pratirodh r naapna hai.", r=0.025, h=0.09,
              pos=[-0.3, 0.025, -0.2], rot=[0, 0, 1.5708], color="#5b3a1e"),
            B("rb", "box", name="Resistance box R + chaabi K₂", size=[0.14, 0.05, 0.08], pos=[0.3, 0.025, -0.2], color="#2b2f36"),
            *dial("g", [0.0, 0.0, -0.2], "Galvanometer"), needle("gn", [0.0, 0.0, -0.2], "I_G", -40000.0),
            B("gw", "rope", a=[0.0, 0.04, -0.15], b={"body": "jockey", "off": [0, -0.02, 0]}, r=0.0012, color="ink"),
            _wire("w1", [[-0.5, 0.015, 0.05], [-0.55, 0.015, 0.05], [-0.55, 0.015, 0.25], [-0.45, 0.015, 0.25]]),
            _wire("w2", [[0.5, 0.015, 0.05], [0.55, 0.015, 0.05], [0.55, 0.015, 0.25], [-0.25, 0.015, 0.25]], "black"),
            _wire("w3", [[-0.55, 0.015, 0.05], [-0.55, 0.015, -0.2], [-0.345, 0.015, -0.2]]),
            _wire("w4", [[-0.255, 0.015, -0.2], [-0.06, 0.015, -0.2]], "black"),
        ],
        knobs=[knob("lj", "Jockey ki jagah l", "lj", 4, 396, 0.5, 120, "cm", 0.0025),
               knob("k2", "Chaabi K₂ (0 khuli / 1 band)", "k2", 0, 1, 1, 0),
               knob("Rb", "Resistance box R", "Rb", 2, 20, 1, 10, "Ω"),
               knob("ri", "Cell (r chhupa)", "r_int", 0.5, 3, 0.1, 1, "Ω", hidden=True)],
        instruments=[inst("G", "readout", "Galvanometer", "I_G", k=1e6, unit="µA", digits=1)],
        table={"columns": [col("k2", "K₂", "knob:k2", digits=0), col("l", "Balancing lambaai", "knob:lj", "cm", 0.0025, digits=1)],
               "calc": "pot_r", "rows_min": 2, "truth": "p.r_int", "result_digits": 2,
               "hint": "K₂ khuli (0) par balance l₁ record; phir K₂ band (1) par balance l₂ record."},
        steps=["K₂ khuli rakhiye. Jockey khiska kar galvanometer shoonya: l₁ record (K₂ = 0).",
               "K₂ band kijiye (R = 10 Ω). Naya balance l₂ record (K₂ = 1).", "r = R(l₁ - l₂)/l₂.", "R badal kar dohraiye."],
        theory="Potentiometer dhaara nahi leta, isliye balance par cell ka poora emf E = k l₁. Shunt R lagane par terminal voltage V = k l₂. "
               "r = R(E/V - 1) = R(l₁ - l₂)/l₂.",
        tour=[{"say": "Lamba taar, uspar sthir dhaara. Jaanch wala cell galvanometer ke zariye jockey se juda hai."},
              {"set": {"lj": 150}, "say": "Balance par galvanometer shoonya: cell se koi dhaara nahi, isliye poora emf naapa."},
              {"set": {"k2": 1}, "say": "K2 band: cell se dhaara behti hai, aantarik pratirodh par voltage girta hai, balance pehle aata hai."}],
        questions=[{"q": "K₂ band karne par balancing lambaai?", "options": ["Ghategi", "Badhegi", "Utni hi"], "answer": 0,
                    "why": "Terminal voltage emf se kam hota hai."}],
        sources=[S12, SIM],
        check={"params": {}, "rows": [
            {"set": {"k2": 0}, "measure": {"mode": "null", "param": "lj", "var": "I_G"}, "take": {"lj": "l"}, "add": {"k2": 0}},
            {"set": {"k2": 1}, "measure": {"mode": "null", "param": "lj", "var": "I_G"}, "take": {"lj": "l"}, "add": {"k2": 1}}],
            "calc": "pot_r", "textbook": "pot_r"},
    )


def diode() -> dict:
    net = {"nodes": 2, "els": [
        {"id": "E", "kind": "V", "a": 1, "b": 0, "value": "Eb"}, {"id": "R", "kind": "R", "a": 1, "b": 2, "value": "Rs"},
        {"id": "D1", "kind": "D", "a": 2, "b": 0, "Is": "Is", "n": "nD"}, {"id": "VM", "kind": "R", "a": 2, "b": 0, "value": 1e6}]}
    return lab(
        id="pn-junction-diode", title="p-n diode: forward I-V", group="Physics · Electricity", level="Class XII",
        topic="Semiconductor Electronics", aim="Forward bias mein voltage badha kar diode ki dhaara naapiye; knee voltage dhoondhiye.",
        kernel="circuit", cfg={"net": net}, params={"Eb": 0.5, "Rs": 100.0, "Is": 7e-9, "nD": 1.8}, autorun=True,
        camera={"pos": [0.0, 0.6, 0.65], "look": [0, 0, 0]}, floor=-0.03,
        bodies=[
            board(0.9, 0.6),
            B("bat", "box", name="Badalne wala DC source", size=[0.16, 0.06, 0.1], pos=[-0.3, 0.03, 0.18], color="#2b2f36"),
            B("rs", "box", name="Pratirodh 100 Ω", info="Dhaara ko seemit rakhta hai.", size=[0.06, 0.012, 0.012], pos=[0.0, 0.02, 0.18], color="#d9b46a"),
            B("dio", "cylinder", name="Silicon diode", info="Kaali patti = cathode (n-side).", r=0.008, h=0.05, pos=[0.25, 0.02, 0.0],
              rot=[1.5708, 0, 0], color="black"),
            B("band", "cylinder", r=0.0085, h=0.006, pos=[0.25, 0.02, -0.018], rot=[1.5708, 0, 0], color="white"),
            *dial("ma", [0.0, 0.0, -0.18], "Milliammeter (0-25 mA)"), needle("man", [0.0, 0.0, -0.18], "I_D1", -96.0, 1.2),
            *dial("vm", [0.3, 0.0, -0.2], "Voltmeter (0-1 V)"), needle("vmn", [0.3, 0.0, -0.2], "V_D1", -2.4, 1.2),
            _wire("w1", [[-0.22, 0.02, 0.18], [-0.03, 0.02, 0.18]]), _wire("w2", [[0.03, 0.02, 0.18], [0.25, 0.02, 0.18], [0.25, 0.02, 0.025]]),
            _wire("w3", [[0.25, 0.02, -0.025], [0.25, 0.02, -0.08], [-0.38, 0.02, -0.08], [-0.38, 0.02, 0.18]], "black"),
        ],
        knobs=[knob("Eb", "Source voltage", "Eb", 0, 3, 0.05, 0.5, "V")],
        instruments=[inst("V", "readout", "Diode par voltage", "V_D1", unit="V", lc=0.01, digits=2),
                     inst("I", "readout", "Dhaara", "I_D1", k=1000, unit="mA", digits=2),
                     inst("gr", "graph", "I vs V (characteristic)", "I_D1", k=1000, x="V_D1", xlabel="V (V)", dots=True)],
        table={"columns": [col("V", "V", "inst:V", "V", digits=2), col("I", "I", "inst:I", "mA", 0.001, digits=2)], "calc": "diode_knee",
               "rows_min": 4, "result_digits": 2},
        steps=["Source 0 se 0.1 V karke badhaiye.", "Har baar V aur I record (kam se kam 8 readings).",
               "Graph dekhiye: ek voltage ke baad dhaara tezi se badhti hai: knee voltage.", "Silicon diode ke liye lagbhag 0.6-0.7 V."],
        theory="Forward bias mein diode ki dhaara I = Is(e^(V/nV_T) - 1): shuru mein lagbhag shoonya, knee ke baad tezi se. "
               "Is lab ka model 1N4007 jaise silicon diode jaisa hai (Is = 7 nA, n = 1.8).",
        safety="Asli lab mein series pratirodh hamesha lagaiye; bina uske diode jal sakta hai.",
        tour=[{"say": "Source, 100 ohm pratirodh aur silicon diode forward bias mein."},
              {"set": {"Eb": 0.5}, "say": "Aadha volt: dhaara lagbhag shoonya. Diode abhi 'khula' nahi."},
              {"set": {"Eb": 2}, "say": "2 volt: dhaara milliampere mein, diode par sirf lagbhag 0.65 volt. Baaki pratirodh par."}],
        questions=[{"q": "Knee ke baad source badhane par diode ka voltage?", "options": ["Thoda hi badhta hai", "Utna hi badhta hai", "Ghatta hai"],
                    "answer": 0, "why": "Dhaara exponential badhti hai; zyada voltage pratirodh par girta hai."}],
        sources=[S12, SIM],
        check={"params": {"Eb": 2.0}, "measure": {"mode": "value", "vars": ["V_D1"]}, "reading": "V_D1", "textbook": "diode_V"},
    )


def rc() -> dict:
    net = {"nodes": 3, "els": [
        {"id": "E", "kind": "V", "a": 1, "b": 0, "value": 5.0}, {"id": "K", "kind": "S", "a": 1, "b": 2, "param": "key"},
        {"id": "R", "kind": "R", "a": 2, "b": 3, "value": "Rr"}, {"id": "C1", "kind": "C", "a": 3, "b": 0, "value": "Cc"}]}
    return lab(
        id="rc-charging", title="Capacitor ka charge hona: τ = RC", group="Physics · Electricity", level="Class XII",
        topic="Electrostatic Potential and Capacitance", aim="Switch band karke capacitor ka voltage dekhiye; 63% tak ka samay τ naapiye.",
        kernel="circuit", cfg={"net": net}, params={"Rr": 10000.0, "Cc": 1e-4, "key": 0.0}, autorun=True,
        camera={"pos": [0.0, 0.55, 0.6], "look": [0, 0, 0]}, floor=-0.03,
        bodies=[
            board(0.9, 0.55),
            B("bat", "box", name="Battery 5 V", size=[0.14, 0.05, 0.08], pos=[-0.3, 0.025, 0.15], color="#2b2f36"),
            B("sw", "box", name="Switch", size=[0.05, 0.02, 0.03], pos=[0.0, 0.02, 0.15], color="black",
              bind={"rz": {"var": "p.key", "k": 0.5, "c": -0.5}}),
            B("res", "box", name="Pratirodh R", size=[0.06, 0.012, 0.012], pos=[0.25, 0.02, 0.05], rot=[0, 1.5708, 0], color="#d9b46a"),
            B("cap", "cylinder", name="Capacitor C", info="Do plate; charge jama hota hai.", r=0.03, h=0.07, pos=[0.25, 0.04, -0.15], color="#3e63dd"),
            B("lvl", "box", name="Charge (dikhane ke liye)", size=[0.012, 0.1, 0.012], pos=[0.32, 0.0, -0.15], color="gold",
              illustrative=True, bind={"sy": {"var": "V_C1", "k": 0.2, "min": 0.001}, "y": {"var": "V_C1", "k": 0.01}}),
            *dial("vm", [-0.15, 0.0, -0.15], "Voltmeter (0-5 V)"), needle("vmn", [-0.15, 0.0, -0.15], "V_C1", -0.48, 1.2),
            _wire("w1", [[-0.23, 0.02, 0.15], [-0.03, 0.02, 0.15]]), _wire("w2", [[0.03, 0.02, 0.15], [0.25, 0.02, 0.15], [0.25, 0.02, 0.08]]),
            _wire("w3", [[0.25, 0.02, 0.02], [0.25, 0.02, -0.12]]),
            _wire("w4", [[0.25, 0.02, -0.19], [0.25, 0.02, -0.24], [-0.38, 0.02, -0.24], [-0.38, 0.02, 0.15]], "black"),
        ],
        knobs=[knob("key", "Switch (0 khula / 1 band)", "key", 0, 1, 1, 0, reset=False),
               knob("Rr", "Pratirodh R", "Rr", 1, 20, 1, 10, "kΩ", 1000.0, reset=True),
               knob("Cc", "Capacitor C", "Cc", 50, 500, 10, 100, "µF", 1e-6, reset=True)],
        instruments=[inst("V", "readout", "Capacitor par voltage", "V_C1", unit="V", lc=0.01, digits=2),
                     inst("sw", "stopwatch", "Stopwatch (switch ke saath shuru)"),
                     inst("gr", "graph", "V_C samay ke saath", "V_C1", range=[0, 5], xlabel="t (s)")],
        table={"columns": [col("tau", "63% (3.16 V) tak ka samay", "inst:sw", "s", digits=2)], "calc": "rc_tau", "rows_min": 1,
               "result_digits": 2, "hint": "Stopwatch aur switch saath; voltage 3.16 V par stopwatch rokiye."},
        steps=["R = 10 kΩ, C = 100 µF: τ = RC = 1 s hona chahiye.", "Stopwatch start karke turant switch band (1).",
               "Voltage 3.16 V (5 V ka 63%) par stopwatch rokiye; record kijiye.", "R ya C doguna karke dohraiye: τ doguna?"],
        theory="Charge hote capacitor ka voltage V = E(1 - e^(-t/RC)). t = RC par V = 0.632 E. Isliye τ = RC 'time constant' hai.",
        tour=[{"say": "Battery, switch, pratirodh aur capacitor. Switch abhi khula hai."},
              {"set": {"key": 1}, "say": "Switch band: capacitor charge ho raha hai. Shuru mein tez, phir dheere.", "run": True},
              {"say": "Ek second mein voltage 63 pratishat tak pahuncha: R guna C barabar ek second."}],
        questions=[{"q": "R doguna karne par 63% tak pahunchne ka samay?", "options": ["Doguna", "Aadha", "Utna hi"], "answer": 0,
                    "why": "τ = RC."}],
        sources=[S12, SIM],
        check={"params": {"key": 1.0}, "measure": {"mode": "time_to", "var": "V_C1", "final": 5.0}, "reading": "t_V_C1",
               "textbook": "rc_tau"},
    )


# ======================================================================================================== OPTICS
def _bench(left=-0.05, right=1.05, y=-0.12) -> list[dict]:
    w = right - left
    return [B("bench", "box", name="Optical bench", size=[w, 0.03, 0.08], pos=[left + w / 2, y, 0], color="wood", cut=False),
            B("ruler", "scale", name="Bench scale (cm)", length=round(w, 3), spacing=0.01, major=10, labels=True, label_step=10, tick=0.01,
              font=0.016, start=round(left * 100), pos=[left, y + 0.017, 0.041], rot=[-1.5708, 0, 0])]


def mirror() -> dict:
    return lab(
        id="concave-mirror", title="Avatal darpan: u-v se f", group="Physics · Optics", level="Class XII",
        topic="Ray Optics and Optical Instruments", aim="Vastu ki doori u badal kar parde par saaf pratibimb dhoondhiye (v); f = uv/(u + v).",
        kernel="mirror", params={"h": 0.05}, autorun=True,
        camera={"pos": [0.35, 0.18, 0.95], "look": [0.3, 0.0, 0]}, floor=-0.15,
        bodies=[
            *_bench(-0.05, 1.0),
            B("mir", "dish", name="Avatal darpan (R = 30 cm)", info="Ismein f = R/2 = 15 cm.", R=0.3, r=0.06, pos=[0, 0, 0], color="#c8d4e0"),
            B("ms", "cylinder", r=0.004, h=0.1, pos=[-0.01, -0.06, 0], color="steel"),
            B("obj", "arrow", name="Vastu (jalti mombatti ki jagah)", dir=[0, 1, 0], len=0.05, head=0.012, pos=[0, 0, 0], color="red",
              bind={"x": "p.u"}),
            B("img", "arrow", name="Pratibimb", info="Ulta aur asli ho to parde par aata hai.", dir=[0, 1, 0], len=0.05, head=0.012,
              pos=[0, 0, 0], color="blue", bind={"x": "img_x", "len": "img_h"}),
            B("scr", "plane", name="Parda (screen)", size=[0.1, 0.1], pos=[0, 0, 0], rot=[0, 1.5708, 0], color="white", opacity=0.8,
              bind={"x": "p.scr"}),
            B("rays", "rays", name="Kiranen", var="rays", color="ray"),
        ],
        knobs=[knob("u", "Vastu ki doori u", "u", 20, 80, 0.5, 45, "cm", 0.01, hint="u > f rakhiye taaki pratibimb asli bane."),
               knob("scr", "Parde ki doori", "scr", 5, 100, 0.5, 30, "cm", 0.01, hint="Parda khiskaiye jab tak pratibimb sabse saaf na ho.")],
        instruments=[inst("sh", "meter", "Parde par pratibimb kitna saaf", "sharp", range=[0, 1], digits=2),
                     inst("mg", "readout", "Aavardhan (m)", "img_h", k=20, digits=2, hint=True)],
        table={"columns": [col("u", "u", "knob:u", "cm", 0.01, digits=1), col("v", "v (saaf parda)", "knob:scr", "cm", 0.01, digits=1)],
               "calc": "mirror_f", "rows_min": 3, "result_k": 100, "result_unit": "cm", "result_digits": 1},
        steps=["u = 45 cm rakhiye.", "Parda khiskaiye: meter full (sabse saaf) par ruk jaaiye.", "u aur v record kijiye.",
               "u = 40, 35, 30, 25 cm par dohraiye.", "f = uv/(u + v) ka ausat: R/2 = 15 cm aana chahiye."],
        theory="Darpan sutra 1/v + 1/u = 1/f (yahan sab doori darpan se dhanaatmak li hain, asli pratibimb ke liye). "
               "Is lab ki kiranen asli gol satah se trace hoti hain, chhote kone par sutra 1% ke andar milta hai.",
        tour=[{"say": "Optical bench par avatal darpan. Laal teer vastu hai, kiranen darpan se laut kar milti hain."},
              {"set": {"scr": 22.5}, "say": "Parda yahan: pratibimb sabse saaf. Ulta aur chhota, kyunki vastu 2f se door hai."},
              {"set": {"u": 30, "scr": 30}, "say": "Vastu C par, yaani 30 centimetre: pratibimb bhi wahin, aur utna hi bada."}],
        questions=[{"q": "Vastu f aur 2f ke beech ho to pratibimb?", "options": ["2f se door, bada", "f ke andar", "Aabhasi"], "answer": 0,
                    "why": "u ghatne par v badhta hai."}],
        sources=[S12, SIM],
        check={"params": {"u": 0.45}, "reading": "v", "textbook": "mirror_v"},
    )


def lens() -> dict:
    return lab(
        id="convex-lens", title="Uttal lens: u-v se f", group="Physics · Optics", level="Class XII",
        topic="Ray Optics and Optical Instruments", aim="Lens se vastu ki doori badal kar parde par saaf pratibimb dhoondhiye; f = uv/(u + v).",
        kernel="lens", params={"h": 0.05}, autorun=True,
        camera={"pos": [0.0, 0.2, 1.2], "look": [0.0, 0.0, 0]}, floor=-0.15,
        bodies=[
            *_bench(-0.85, 0.85),
            B("lens", "lens", name="Uttal lens (f ≈ 20 cm)", info="Kaanch n = 1.5, dono satah R = 20 cm.", r=0.025, thick=0.008, pos=[0, 0, 0],
              color="glass", opacity=0.45),
            B("ls", "cylinder", r=0.004, h=0.07, pos=[0, -0.075, 0], color="steel"),
            B("obj", "arrow", name="Vastu", dir=[0, 1, 0], len=0.05, head=0.012, pos=[0, 0, 0], color="red", bind={"x": {"var": "p.u", "k": -1}}),
            B("img", "arrow", name="Pratibimb", dir=[0, 1, 0], len=0.05, head=0.012, pos=[0, 0, 0], color="blue",
              bind={"x": "img_x", "len": "img_h"}),
            B("scr", "plane", name="Parda", size=[0.1, 0.1], pos=[0, 0, 0], rot=[0, 1.5708, 0], color="white", opacity=0.8, bind={"x": "p.scr"}),
            B("rays", "rays", name="Kiranen", var="rays", color="ray"),
        ],
        knobs=[knob("u", "Vastu ki doori u", "u", 25, 80, 0.5, 40, "cm", 0.01),
               knob("scr", "Parde ki doori", "scr", 5, 85, 0.5, 30, "cm", 0.01)],
        instruments=[inst("sh", "meter", "Parde par pratibimb kitna saaf", "sharp", range=[0, 1], digits=2)],
        table={"columns": [col("u", "u", "knob:u", "cm", 0.01, digits=1), col("v", "v (saaf parda)", "knob:scr", "cm", 0.01, digits=1)],
               "calc": "lens_f", "rows_min": 3, "result_k": 100, "result_unit": "cm", "result_digits": 1},
        steps=["u = 40 cm.", "Parda khiskaiye jab tak pratibimb sabse saaf.", "u, v record; u = 35, 30, 50, 60 cm par dohraiye.",
               "f = uv/(u + v) ka ausat."],
        theory="Lens sutra 1/v + 1/u = 1/f (asli pratibimb, doori lens se). Lensmaker: 1/f = (n - 1)(1/R₁ + 1/R₂) = 0.5 × 10 → f = 20 cm. "
               "Asli lens ki motaai se thoda farq aata hai (yahan 1% se kam).",
        tour=[{"say": "Uttal lens beech mein, vastu baayein, parda daayein."},
              {"set": {"scr": 40.4}, "say": "u 40 par parda lagbhag 40: kyunki vastu 2f par hai, pratibimb bhi 2f par."},
              {"set": {"u": 30, "scr": 60}, "say": "Vastu paas laayi: pratibimb door aur bada ho gaya."}],
        questions=[{"q": "Vastu f se kam doori par ho to?", "options": ["Parde par koi pratibimb nahi (aabhasi)", "Chhota asli", "2f par"], "answer": 0,
                    "why": "Kiranen phailti hain; pratibimb lens ke usi taraf aabhasi banta hai."}],
        sources=[S12, SIM],
        check={"params": {"u": 0.4}, "reading": "v", "textbook": "lens_v"},
    )


def prism() -> dict:
    return lab(
        id="prism-minimum-deviation", title="Prism: nyoontam vichalan", group="Physics · Optics", level="Class XII",
        topic="Ray Optics and Optical Instruments", aim="Aapatan kon i badal kar vichalan δ ka graph banaiye; δm se n nikaaliye.",
        kernel="prism", params={"i": 0.8}, autorun=True,
        camera={"pos": [0.0, 0.06, 0.5], "look": [0.0, 0.05, 0]}, floor=-0.05,
        bodies=[
            B("paper", "box", name="Drawing board", size=[0.5, 0.004, 0.3], pos=[0, -0.03, 0], color="white", cut=False),
            B("pr", "prism", name="Kaanch ka prism (A = 60°)", angle="A", side=0.12, depth=0.04, pos=[0, 0, 0], color="glass", opacity=0.45),
            B("rays", "rays", name="Kiran (pin se)", var="rays", color="ray", virtual="ink"),
        ],
        knobs=[knob("i", "Aapatan kon i", "i", 30, 75, 0.5, 46, "°", DEG),
               knob("n", "Kaanch (n chhupa)", "n", 1.4, 1.8, 0.01, 1.5, hidden=True)],
        instruments=[inst("d", "readout", "Vichalan kon δ (protractor)", "dev", k=R2D, unit="°", lc=0.1, digits=1),
                     inst("gr", "graph", "δ vs i", "dev", k=R2D, x="p.i", xk=R2D, xlabel="i (°)", dots=True)],
        table={"columns": [col("i", "i", "knob:i", "°", DEG, digits=1), col("d", "δ", "inst:d", "°", DEG, digits=1)],
               "calc": "prism_n", "rows_min": 5, "truth": "p.n", "result_digits": 3},
        steps=["i = 35° se 70° tak 5° ke kadam.", "Har i par δ record kijiye.", "Graph: δ pehle ghatta, phir badhta hai; sabse neeche δm.",
               "n = sin((A + δm)/2) / sin(A/2)."],
        theory="Nyoontam vichalan par kiran prism ke andar aadhar ke samaanaantar chalti hai, aur i = e. Tab n = sin((A + δm)/2) / sin(A/2).",
        tour=[{"say": "Kaanch ka prism, 60 degree ka. Kiran baayein satah par girti hai aur aadhar ki taraf mudti hai."},
              {"set": {"i": 35}, "say": "Chhota aapatan kon: vichalan zyada."},
              {"set": {"i": 48.5}, "say": "Yahan vichalan sabse kam hai: kiran prism ke andar seedhi, aadhar ke samaanaantar."}],
        questions=[{"q": "Nyoontam vichalan par i aur e?", "options": ["Barabar", "i doguna", "e shoonya"], "answer": 0, "why": "Kiran samamit raaste par chalti hai."}],
        sources=[S12, SIM],
        check={"params": {}, "reading": "dm", "textbook": "prism_dm"},
    )


def slab() -> dict:
    return lab(
        id="glass-slab-apparent-depth", title="Kaanch ki slab: abhaasi gehraai", group="Physics · Optics", level="Class XII",
        topic="Ray Optics and Optical Instruments", aim="Slab ke neeche nishaan upar uthta dikhta hai: asli / abhaasi gehraai se n nikaaliye.",
        kernel="slab", autorun=True,
        camera={"pos": [0.12, 0.05, 0.32], "look": [0.0, -0.03, 0]}, floor=-0.12,
        bodies=[
            B("slab", "box", name="Kaanch ki slab", size=[0.2, 0.05, 0.12], pos=[0, 0, 0], color="glass", opacity=0.3,
              bind={"sy": {"var": "p.t", "k": 20}, "y": {"var": "p.t", "k": -0.5}}),
            B("mk1", "box", name="Nishaan (asli jagah)", size=[0.03, 0.002, 0.004], pos=[0, 0, 0], color="black", bind={"y": {"var": "p.t", "k": -1}}),
            B("mk2", "box", size=[0.004, 0.002, 0.03], pos=[0, 0, 0], color="black", bind={"y": {"var": "p.t", "k": -1}}),
            B("ghost", "box", name="Nishaan jahan dikhta hai", info="Upar se dekhne par.", size=[0.03, 0.002, 0.004], pos=[0, 0, 0], color="red",
              opacity=0.6, illustrative=True, bind={"y": {"var": "app", "k": -1}}),
            B("micro", "cylinder", name="Travelling microscope", r=0.012, h=0.08, pos=[0, 0.09, 0], color="#2b2f36"),
            B("rays", "rays", name="Kiranen", var="rays", color="ray"),
        ],
        knobs=[knob("t", "Slab ki motaai", "t", 2, 10, 0.1, 5, "cm", 0.01),
               knob("n", "Padarth (paani 1.33, kaanch 1.5, heera 2.42)", "n", 1.33, 2.42, 0.01, 1.5)],
        instruments=[inst("a", "readout", "Microscope: abhaasi gehraai", "app", k=100, unit="cm", lc=0.01, digits=2),
                     inst("s", "readout", "Nishaan kitna utha", "shift", k=100, unit="cm", lc=0.01, digits=2)],
        table={"columns": [col("t", "Asli gehraai", "knob:t", "cm", 0.01, digits=2), col("a", "Abhaasi gehraai", "inst:a", "cm", 0.01, digits=2)],
               "calc": "slab_n", "rows_min": 2, "truth": "p.n", "result_digits": 3},
        steps=["Slab 5 cm, kaanch.", "Microscope se abhaasi gehraai padhiye, record kijiye.", "Motaai badal kar dohraiye.", "n = asli / abhaasi."],
        theory="Ghane maadhyam se hawa mein kiran normal se door mudti hai, isliye neeche ki cheez upar uthi dikhti hai. Seedhe upar se: n = asli gehraai / abhaasi gehraai.",
        tour=[{"say": "Kaanch ki slab ke neeche ek nishaan. Upar se dekhne par woh upar utha dikhta hai."},
              {"set": {"n": 2.42}, "say": "Heera: nishaan aur zyada upar dikhta hai, kyunki n bada hai."}],
        questions=[{"q": "Paani se bhare taalaab ki gehraai upar se?", "options": ["Kam dikhti hai", "Zyada dikhti hai", "Utni hi"], "answer": 0,
                    "why": "Abhaasi = asli / n."}],
        sources=[S12, SIM],
        check={"params": {}, "reading": "app", "textbook": "slab_app"},
    )


# ======================================================================================================== MAGNETISM
def induction() -> dict:
    return lab(
        id="electromagnetic-induction", title="Faraday: magnet aur coil", group="Physics · Magnetism", level="Class XII",
        topic="Electromagnetic Induction", aim="Magnet ko coil se alag-alag raftaar se guzaariye: peak emf raftaar ke saath kaise badalta hai?",
        kernel="induction", autorun=True, speeds=[0.1, 0.25, 0.5, 1],
        speed=0.25, camera={"pos": [0.0, 0.2, 0.42], "look": [0.0, -0.03, -0.04]}, floor=-0.08,
        bodies=[
            B("tbl", "box", size=[0.5, 0.01, 0.25], pos=[0, -0.06, 0], color="wood", cut=False),
            B("coil", "spring", name="Coil (N chakkar)", info="Magnet ka flux badalne par isme emf aata hai.", a=[-0.04, 0, 0], b=[0.04, 0, 0],
              r=0.026, turns=24, wire=0.0018, color="copper"),
            B("mag", "box", name="Chhad chumbak", size=[0.001, 0.001, 0.001], pos=[0, 0, 0], bind={"x": "z"}),
            B("magN", "box", name="Chumbak: N dhruv", size=[0.03, 0.012, 0.012], pos=[0.015, 0, 0], parent="mag", color="red"),
            B("magS", "box", name="Chumbak: S dhruv", size=[0.03, 0.012, 0.012], pos=[-0.015, 0, 0], parent="mag", color="blue"),
            *dial("g", [0.0, -0.055, -0.15], "Galvanometer", "Sui ki disha = dhaara ki disha (Lenz)."),
            needle("gn", [0.0, -0.055, -0.15], "emf", -6.0),
            _wire("w1", [[-0.04, -0.026, 0], [-0.04, -0.05, -0.1], [-0.05, -0.04, -0.15]]),
            _wire("w2", [[0.04, -0.026, 0], [0.04, -0.05, -0.1], [0.05, -0.04, -0.15]], "black"),
        ],
        knobs=[knob("v", "Magnet ki raftaar", "v", -2, 2, 0.1, 0.5, "m/s", reset=True, hint="Ulti disha (minus) mein sui ulti ghoomti hai."),
               knob("N", "Coil ke chakkar", "N", 50, 500, 10, 200)],
        instruments=[inst("e", "readout", "Emf (abhi)", "emf", k=1000, unit="mV", digits=1),
                     inst("pk", "readout", "Sabse zyada emf (Reset se saaf)", "emf", k=1000, unit="mV", digits=1, peak=True),
                     inst("gr", "graph", "Emf samay ke saath", "emf", k=1000, xlabel="t (s)")],
        table={"columns": [col("v", "Raftaar v", "knob:v", "m/s", digits=1), col("emf", "Peak emf", "inst:pk", "mV", 0.001, digits=1)],
               "calc": "induct_ratio", "rows_min": 2, "result_digits": 4, "hint": "Har raftaar par Reset, magnet ek baar guzarne do, peak record."},
        steps=["Raftaar 0.5 m/s: magnet coil se guzarta hai, sui hilti hai.", "Peak emf record kijiye.",
               "Raftaar 1.0, 1.5 m/s par dohraiye: emf / v sthir?", "Coil ke chakkar doguna: emf doguna."],
        theory="Faraday: emf = -N dΦ/dt. Tez magnet = flux tezi se badalta hai = zyada emf. Lenz: aane aur jaane par sui ulti disha mein.",
        tour=[{"say": "Chhad chumbak coil ki taraf aata hai: flux badhta hai, sui ek taraf.", "run": True},
              {"say": "Coil se nikalte waqt flux ghatta hai: sui ulti taraf. Yahi Lenz ka niyam hai."},
              {"set": {"v": 1.5}, "say": "Teen guna raftaar: peak emf bhi teen guna."}],
        questions=[{"q": "Magnet coil ke andar ruka rahe to emf?", "options": ["Shoonya", "Sabse zyada", "Ulta"], "answer": 0, "why": "Flux badal nahi raha."}],
        sources=[S12, SIM],
        check={"params": {}, "reading": "emf_peak", "textbook": "induct_peak"},
    )


# ======================================================================================================== MEASUREMENT
def vernier() -> dict:
    s = 10.0                       # 1 m = 10 stage units: 1 mm = 1 cm on screen (10x magnified)
    return lab(
        id="vernier-callipers", title="Vernier callipers se naapna", group="Physics · Measurement", level="Class XI",
        topic="Units and Measurement", aim="Main scale aur vernier padh kar gole ka vyaas naapiye (least count 0.1 mm).",
        kernel="gauge", params={"kind": 0.0}, autorun=True,
        camera={"pos": [0.25, -0.02, 0.75], "look": [0.25, -0.05, 0]}, floor=-0.36,
        bodies=[
            B("beam", "box", name="Main scale (mm)", info="Har chhota khaana 1 mm. Screen par 10 guna bada.", size=[1.1, 0.06, 0.01],
              pos=[0.5, 0.03, 0], color="steel"),
            B("ms", "scale", length=1.0, spacing=0.01, major=10, labels=True, label_step=1, tick=0.012, font=0.018, down=True,
              pos=[0, 0.06, 0.006]),
            B("jaw0", "box", name="Sthir jabda", size=[0.03, 0.34, 0.01], pos=[-0.015, -0.14, 0], color="steel"),
            B("slider", "box", name="Vernier (khisakne wala jabda)", info="10 vernier khaane = 9 mm: least count 0.1 mm.",
              size=[0.001, 0.001, 0.001], pos=[0, 0, 0], bind={"x": {"var": "jaw", "k": s}}),
            B("vplate", "box", size=[0.12, 0.04, 0.012], pos=[0.06, 0.08, 0.002], parent="slider", color="#b8c0c8"),
            B("jaw1", "box", size=[0.03, 0.34, 0.01], pos=[0.015, -0.14, 0], parent="slider", color="steel"),
            B("vs", "scale", name="Vernier scale", length=0.09, spacing=0.009, major=5, labels=True, label_step=5, tick=0.012, font=0.014,
              pos=[0, 0.06, 0.01], parent="slider", bind={"mark": "div"}),
            B("ball", "cylinder", name="Naapne ki goli", r=0.5, h=0.02, pos=[0, -0.2, -0.012], rot=[1.5708, 0, 0], color="brass",
              bind={"x": {"var": "p.L", "k": s / 2}, "sx": {"var": "p.L", "k": s}, "sz": {"var": "p.L", "k": s}}),
        ],
        knobs=[knob("L", "Doosri goli lijiye (asli naap chhupi)", "L", 5, 60, 0.05, 23.45, "mm", 0.001, hidden=True),
               knob("ze", "Zero error", "ze", -0.5, 0.5, 0.1, 0, "mm", 0.001, hint="Jabde band par vernier ka 0 main ke 0 se kitna khiska.")],
        instruments=[inst("lc", "readout", "Least count", "lc", k=1000, unit="mm", digits=2),
                     inst("msr", "readout", "Main scale reading (madad)", "main", k=1000, unit="mm", digits=1, hint=True),
                     inst("vsd", "readout", "Milne wala vernier khaana (madad)", "div", digits=0, hint=True)],
        table={"columns": [col("reading", "Vyaas (MSR + VSD × LC - zero error)", "manual", "mm", 0.001)], "calc": "gauge_mean", "rows_min": 1,
               "truth": "p.L", "result_k": 1000, "result_unit": "mm", "result_digits": 2},
        steps=["Vernier ka 0 main scale par kahan hai: usse pehle wala mm = MSR.", "Vernier ka kaunsa khaana main scale ki kisi rekha se milta hai (laal) = VSD.",
               "Reading = MSR + VSD × 0.1 mm - zero error.", "Table mein khud likhiye; 3 goliyon par dohraiye."],
        theory="10 vernier khaane = 9 main scale khaane, isliye least count = 1 mm - 0.9 mm = 0.1 mm.",
        tour=[{"say": "Vernier callipers: upar main scale, khisakne wale jabde par vernier scale. Screen par sab 10 guna bada hai."},
              {"cam": [0.25, 0.06, 0.25], "look": [0.25, 0.06, 0], "say": "Vernier ka shoonya 23 aur 24 millimetre ke beech. MSR 23 millimetre."},
              {"say": "Laal khaana main scale se milta hai. Uska number guna 0.1 millimetre jodiye."}],
        questions=[{"q": "Least count 0.1 mm kyun?", "options": ["10 VSD = 9 MSD", "Scale chhota hai", "Jabde patle hain"], "answer": 0,
                    "why": "1 MSD - 1 VSD = 0.1 mm."}],
        sources=[S11, SIM],
        check={"params": {"L": 0.02345}, "reading": "reading", "textbook": "gauge_L"},
    )


def screw_gauge() -> dict:
    s = 100.0                      # 1 mm = 0.1 stage unit (100x magnified)
    return lab(
        id="screw-gauge", title="Screw gauge se taar ka vyaas", group="Physics · Measurement", level="Class XI",
        topic="Units and Measurement", aim="Pitch 0.5 mm, 50 khaane: least count 0.01 mm. Taar ka vyaas naapiye.",
        kernel="gauge", params={"kind": 1.0, "L": 0.000512}, autorun=True,
        camera={"pos": [0.1, 0.12, 0.6], "look": [0.1, 0.0, 0]}, floor=-0.25,
        bodies=[
            B("frame", "box", name="U-frame", size=[0.04, 0.3, 0.03], pos=[-0.06, -0.08, 0], color="#2b2f36"),
            B("frameb", "box", size=[0.5, 0.04, 0.03], pos=[0.17, -0.21, 0], color="#2b2f36"),
            B("anvil", "cylinder", name="Sthir sira (anvil)", r=0.015, h=0.04, pos=[-0.02, 0, 0], rot=[0, 0, 1.5708], color="steel"),
            B("wire", "cylinder", name="Taar", info="Screen par 100 guna mota.", r=0.5, h=0.12, pos=[0, 0, 0], rot=[1.5708, 0, 0], color="copper",
              bind={"x": {"var": "p.L", "k": s / 2}, "sx": {"var": "p.L", "k": s}, "sz": {"var": "p.L", "k": s}}),
            B("sleeve", "cylinder", name="Sleeve (rekha scale, 0.5 mm)", r=0.02, h=0.4, pos=[0.3, 0, 0], rot=[0, 0, 1.5708], color="#c4ccd4"),
            B("ls", "scale", length=0.3, spacing=0.05, major=2, labels=True, label_step=1, tick=0.01, font=0.016, pos=[0.1, 0.02, 0.012]),
            B("sp", "box", name="Spindle", size=[0.001, 0.001, 0.001], pos=[0, 0, 0], bind={"x": {"var": "jaw", "k": s}}),
            B("spin", "cylinder", r=0.012, h=0.1, pos=[0.05, 0, 0], rot=[0, 0, 1.5708], parent="sp", color="steel"),
            B("thimble", "cylinder", name="Thimble (50 khaane)", info="Ek chakkar = 0.5 mm; ek khaana = 0.01 mm.", r=0.03, h=0.12,
              pos=[0.16, 0, 0], rot=[0, 0, 1.5708], parent="sp", color="#9aa3ad", bind={"rx": {"var": "jaw", "k": 12566.37}}),
            B("tm", "box", size=[0.12, 0.004, 0.004], pos=[0, 0.0, 0.03], parent="thimble", color="red"),
        ],
        knobs=[knob("L", "Doosra taar (asli naap chhupi)", "L", 0.2, 3.0, 0.001, 0.512, "mm", 0.001, hidden=True),
               knob("ze", "Zero error", "ze", -0.05, 0.05, 0.01, 0, "mm", 0.001)],
        instruments=[inst("lc", "readout", "Least count", "lc", k=1000, unit="mm", digits=3),
                     inst("psr", "readout", "Pitch scale reading (madad)", "main", k=1000, unit="mm", digits=2, hint=True),
                     inst("hsr", "readout", "Thimble ka khaana (madad)", "div", digits=0, hint=True)],
        table={"columns": [col("reading", "Vyaas (PSR + HSR × LC - zero error)", "manual", "mm", 0.001)], "calc": "gauge_mean", "rows_min": 1,
               "truth": "p.L", "result_k": 1000, "result_unit": "mm", "result_digits": 3},
        steps=["Sleeve par dikhti aakhri rekha = PSR (0.5 mm ke kadam).", "Thimble ka jo khaana rekha par hai = HSR.",
               "Vyaas = PSR + HSR × 0.01 mm - zero error.", "Taar ki 3 jagah naapiye; ausat lijiye."],
        theory="Least count = pitch / thimble ke khaane = 0.5 mm / 50 = 0.01 mm.",
        tour=[{"say": "Screw gauge: taar anvil aur spindle ke beech. Thimble ghumane par spindle aage badhta hai."},
              {"say": "Ek poora chakkar 0.5 millimetre. Thimble ke 50 khaane: har khaana 0.01 millimetre."}],
        questions=[{"q": "Pitch 1 mm aur 100 khaane ho to least count?", "options": ["0.01 mm", "0.1 mm", "1 mm"], "answer": 0, "why": "1/100 mm."}],
        sources=[S11, SIM],
        check={"params": {}, "reading": "reading", "textbook": "gauge_L"},
    )


BUILDERS = (pendulum, hooke, shm, incline, stokes, cooling, boyle, mixtures, resonance, sonometer, ohm, meter_bridge,
            potentiometer, diode, rc, mirror, lens, prism, slab, induction, vernier, screw_gauge)
