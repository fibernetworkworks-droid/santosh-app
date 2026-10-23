"""v0.140 How Claude gets premium work out of Opus 5.5, done for every Hoola app: art direction (design DNA) before any
screen, a layout fingerprint that keeps every look / app different, the app's own 3D scenes (data, drawn by the kit with
three.js), and Opus looking at its own real screenshots and redrawing what scores below the bar."""
import json
import re

import pytest

from tests.test_v128_appdesign import FakeAI, good_screen

T = "default"

SCENE = {"camera": {"fov": 38, "distance": 6, "height": 1}, "light": "studio", "interact": "drag", "autorotate": 0.3,
         "objects": [{"shape": "disc", "size": [1.8, 0.08, 1.8], "rot": [70, 0, 0], "material": "glossy", "colour": "ink",
                      "anim": [{"type": "spin", "speed": 1}],
                      "children": [{"shape": "disc", "size": [0.6, 0.1, 0.6], "material": "satin", "colour": "accent"}]},
                     {"shape": "star", "size": [0.6, 0.6, 0.25], "pos": [1.6, 1.2, 0.5], "material": "glow", "colour": "accent",
                      "args": {"spikes": 5}, "anim": [{"type": "float", "speed": 1, "amount": 0.6}]}],
         "particles": {"count": 60, "colour": "accent", "size": 0.05, "spread": 6}}


def dna(n, system="bento", hero="3d_object", scene=True):
    return {"concept": f"Groove {n}", "idea": "every screen spins around a record", "mood": ["warm", "night", "rhythmic"],
            "layout": {"system": system, "hero": hero, "rhythm": "staggered", "density": "airy", "notes": "big left-aligned type"},
            "signature": f"a vinyl groove arc {n} behind every header", "shape": "pill corners", "type": "huge tight headlines",
            "colour": "ink dominant, accent sparks", "texture": "grain",
            "structure": {"nav": "floating_pill", "card": "glass", "header": "big_type", "button": "pill", "transition": "zoom"},
            "motion": {"language": "things orbit and settle", "entrance": "m_blur_in", "micro": ["m_glow", "m_tilt"], "transition": "zoom"},
            "three_d": {"use": scene, "why": "the record is the product", "where": ["home"], "scenes": {"hero": SCENE} if scene else {}},
            "icons": "2px rounded line", "imagery": "drawn records and waves",
            "avoid": ["a grid of identical cards", "a brand's look"], "screens": {"home": "the record spins as the hero"}}


def scene_screen(sid, prompt):
    out = good_screen(sid, prompt)
    if sid == "home":
        out["html"] = out["html"].replace('<div class="body">', '<div class="body"><div class="obj3d wide" data-scene="hero" '
                                                                 'aria-label="A spinning record"></div>', 1)
    return out


@pytest.fixture
def art_env(env, monkeypatch, tmp_path):
    monkeypatch.setenv("APP_DIR", str(tmp_path / "apps"))
    monkeypatch.setenv("APP_WORKER", "false")
    monkeypatch.setenv("APP_FONTS_FETCH", "false")
    monkeypatch.setenv("APP_FONTS_DIR", str(tmp_path / "fonts"))
    monkeypatch.setenv("SEMANTIC_OFF", "1")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.appmaker import ai as AI
    fake = FakeAI()
    calls = {"art": [], "critique": [], "screens": []}

    def ask_json(system, prompt, max_tokens=7000):
        sid = re.search(r"SCREEN_ID: scr-([\w-]+)", prompt).group(1)
        calls["screens"].append((sid, prompt))
        if "FIX THESE" in prompt:                        # the redraw after the director's notes: a better home
            out = scene_screen(sid, prompt)
            out["html"] = out["html"].replace("Sharma home", "Sharma home, redrawn")
            return out
        return scene_screen(sid, prompt)

    def ask_art(system, prompt, max_tokens=6000):
        calls["art"].append(prompt)
        n = len(calls["art"])
        if n in (1, 2):                                  # look 2 first comes out too close to look 1
            return dna(n)
        alt = {3: ("editorial", "big_type", "masonry", "m_typewriter", "dots", "tall serif numerals counting each track"),
               4: ("poster", "collage", "zigzag", "m_unfold", "paper", "torn paper strips stapled over photos")}
        system, hero, rhythm, entrance, texture, sig = alt[min(n, 4)]
        d = dna(n, system=system, hero=hero, scene=n == 3)
        d["layout"]["rhythm"], d["motion"]["entrance"], d["texture"], d["signature"] = rhythm, entrance, texture, sig
        if n == 3:
            d["three_d"]["scenes"] = {"hero": {"objects": [{"shape": "torus_knot", "material": "metal", "colour": "accent"}]}}
        return d

    def ask_critique(system, prompt, image, max_tokens=1800):
        calls["critique"].append((prompt, image[:4]))
        sid = re.search(r"\(([\w-]+)\) - ", prompt).group(1)
        redrawn = any(s == sid and "FIX THESE" in p for s, p in calls["screens"])
        if sid == "home" and not redrawn:
            return {"score": 5.5, "scores": {"hierarchy": 5, "uniqueness": 4}, "good": ["warm colours"],
                    "fixes": ["make the hero record twice as big", "add the groove arc behind the header"]}
        return {"score": 8.7, "scores": {"hierarchy": 9}, "good": ["clear focus"], "fixes": []}
    monkeypatch.setattr(AI, "ask_json", ask_json)
    monkeypatch.setattr(AI, "ask_edit", fake)
    monkeypatch.setattr(AI, "ask_art", ask_art)
    monkeypatch.setattr(AI, "ask_critique", ask_critique)
    return calls


def test_dna_and_scene_are_cleaned_and_compared():
    from app.appmaker import artdirect as AD
    d = AD.clean_dna({**dna(1), "layout": {"system": "rm -rf", "hero": "big_type"}, "texture": "<script>",
                      "structure": {"nav": "evil", "card": "glass"}, "motion": {"entrance": "x", "micro": ["m_glow", "nope"]}},
                     "aurora_glass", ["home", "cart"])
    assert d["layout"]["system"] == "asymmetric" and d["layout"]["hero"] == "big_type" and d["texture"] == ""
    assert d["structure"] == {"card": "glass"} and d["motion"]["entrance"] == "m_stagger" and d["motion"]["micro"] == ["m_glow"]
    assert "hero" in d["three_d"]["scenes"] and d["three_d"]["where"] == ["home"]
    bad = {"objects": [{"shape": "sphere", "size": [99, 1, 1], "pos": [1e9, "x", None], "material": "lava", "colour": "url(x)",
                        "children": [{"shape": "box", "children": [{"shape": "box", "children": [{"shape": "box"}]}]}]}]
           + [{"shape": "box"}] * 40 + [{"shape": "teapot"}], "particles": {"count": 99999}, "light": "x", "camera": {"fov": 999}}
    c = AD.clean_scene(bad)
    o = c["objects"][0]
    assert o["size"][0] == 4 and o["pos"] == [6, 0, 0] and o["material"] == "satin" and o["colour"] == "primary"
    assert len(AD.shapes_of(c)) == AD.MAX_OBJECTS and c["particles"]["count"] == 300 and c["light"] == "studio"
    assert c["camera"]["fov"] == 60 and "teapot" not in AD.shapes_of(c)
    assert not o["children"][0]["children"][0]["children"]          # three levels at most
    assert AD.clean_scene({"objects": [{"shape": "teapot"}]}) is None
    a, b = AD.fingerprint(AD.clean_dna(dna(1), "aurora_glass", ["home"])), AD.fingerprint(AD.clean_dna(dna(2), "aurora_glass", ["home"]))
    d3 = dna(3, system="editorial", hero="big_type", scene=False)
    d3["layout"]["rhythm"] = "masonry"
    d3["motion"]["entrance"] = "m_typewriter"
    d3["texture"] = "dots"
    d3["signature"] = "tall serif numerals counting each track"
    other = AD.fingerprint(AD.clean_dna(d3, "aurora_glass", ["home"]))
    assert AD.closeness(a, b) >= AD.SIBLING_CLOSE and AD.closeness(a, other) < AD.SIBLING_CLOSE
    js = AD.scenes_js({"hero": SCENE, "x": {"objects": [{"shape": "box"}], "n": "</script><script>alert(1)"}})
    assert js.startswith("window.HOOLA_SCENES = ") and "</script>" not in js


def test_looks_get_their_own_dna_unique_and_3d(art_env):
    pytest.importorskip("playwright")
    from app.appmaker import service as S
    from app.appmaker import kit as K
    v = S.new(T, "Sharma Sweets ki app, ghar pe delivery, order WhatsApp par", name="Sharma Sweets")
    S.approve_plan(T, v["id"])
    r = S._load(v["id"])
    looks = S._j(r.looks, [])
    assert len(looks) == 3 and len(art_env["art"]) == 4                     # look 2 was asked again (too close to look 1)
    assert "YOUR FIRST DIRECTION WAS TOO CLOSE TO" in art_env["art"][2] and "THE OTHER LOOKS OF THIS APP" in art_env["art"][1]
    systems = [lk["art"]["layout"]["system"] for lk in looks]
    assert len(set(systems)) == 3 and all(lk["art"]["by"] == "Claude Opus 5.5" for lk in looks)
    assert looks[0]["tokens"]["nav"] == "floating_pill" and looks[0]["tokens"]["card"] == "glass"   # DNA set the structure
    # every look's home prompt carried its own DNA
    home_prompts = [p for s, p in art_env["screens"] if s == "home"]
    assert all("DESIGN DNA of this app" in p and "SIGNATURE element" in p for p in home_prompts)
    assert "Groove 1" in home_prompts[0] and "Groove 3" not in home_prompts[0]
    # the 3D scene really drew in the look (three.js + the scene runtime + the data file)
    site = K.app_dir(T, r.id) / "looks" / "0" / "site"
    idx = (site / "index.html").read_text()
    assert "assets/scene3d.js" in idx and "assets/scenes.js" in idx and (site / "assets" / "three.min.js").exists()
    assert json.loads((site / "assets" / "scenes.js").read_text().split("=", 1)[1].rstrip(";\n"))["hero"]["objects"]
    v2 = S.get(T, r.id)
    assert v2["looks"][0]["art"]["concept"] == "Groove 1" and v2["looks"][0]["art"]["three_d"]


def test_design_uses_dna_and_opus_reviews_its_own_screenshots(art_env):
    pytest.importorskip("playwright")
    from app.appmaker import service as S
    v = S.new(T, "Sharma Sweets ki app, ghar pe delivery, order WhatsApp par", name="Sharma Sweets")
    S.approve_plan(T, v["id"])
    out = S.choose_look(T, v["id"], 0)
    r = S._load(v["id"])
    plan = S._j(r.plan, {})
    assert plan["art"]["concept"] == "Groove 1" and out["art"]["signature"]
    # every screen prompt carries the DNA; the design finished and was checked
    later = [p for s, p in art_env["screens"] if "ONE of three alternative looks" not in p]
    assert later and all("DESIGN DNA of this app" in p for p in later)
    assert r.status == "ready", r.error
    # critique: home scored 5.5 -> redrawn with the notes -> 8.7; tabs looked at once each
    board = S._j(r.board, {})
    sc = board["scores"]
    assert sc["home"]["score"] == 8.7 and sc["home"]["before"] == 5.5 and sc["home"]["by"] == "Claude Opus 5.5"
    assert all(k in sc for k in plan["tabs"] if k in plan["screens"])
    assert any("FIX THESE" in p and "make the hero record twice as big" in p for s, p in art_env["screens"] if s == "home")
    assert all(img in (b"\xff\xd8\xff\xe0", b"\xff\xd8\xff\xdb", b"\xff\xd8\xff\xe1") or img[:2] == b"\xff\xd8"
               for _p, img in art_env["critique"])                         # it judged real JPEG screenshots
    home = json.loads(S._scr_path(r, "home").read_text())
    assert "redrawn" in home["html"] and home["critique"]["score"] == 8.7
    n = len(art_env["critique"])
    S._critique_pass(S._load(r.id), plan, {})                              # same screens again: not judged twice
    assert len(art_env["critique"]) == n
    assert S.STATS["refined"] >= 1 and S.STATS["critiques"] >= 2


def test_android_build_gets_dna_and_scene_stills(art_env, monkeypatch, tmp_path):
    pytest.importorskip("playwright")
    from app.appmaker import service as S
    from app.appmaker.android import gen as G
    from app.appmaker.android import service as AN
    v = S.new(T, "Sharma Sweets ki app, ghar pe delivery, order WhatsApp par", name="Sharma Sweets")
    S.approve_plan(T, v["id"])
    S.choose_look(T, v["id"], 0)
    r = S._load(v["id"])
    ctx = S._ctx(r)
    work = tmp_path / "w"
    scenes = AN._scenes(r, ctx, work)
    png = (work / "scenes" / "hero.png")
    assert scenes == {"hero": str(png)} and png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n" and png.stat().st_size > 2000
    lines = AN._dna_lines(ctx, "home", {"scenes": scenes})
    assert "DESIGN DNA of this app" in lines and 'Scene3D("NAME")' in lines and "hero" in lines
    # the generator copies the still into the APK assets (only a real PNG with a plain name)
    from app.appmaker.android import fixture_make  # noqa: F401  (fixture spec has a scene too)
    spec = json.loads((G.TEMPLATE.parent / "fixture" / "spec.json").read_text())
    spec["scenes"] = {"hero": str(png), "../evil": str(png), "fake": str(tmp_path / "nope.png")}
    spec["fonts"] = {}
    out = tmp_path / "proj"
    G.write_project(spec, out)
    assets = out / "app/src/main/assets/scenes"
    assert sorted(p.name for p in assets.iterdir()) == ["hero.png"]
    assert (out / "app/src/main/java/hoola/kit/Scene3D.kt").exists()
    from app.appmaker.android import prompts as P
    assert "Scene3D(name: String" in P.kit_sheet()
