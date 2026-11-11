"""v0.777 HOOLA DESIGN AI ("Ask Hoola": one line -> a designed frame; change the selection; the hoola_design tool).

The model here is a FAKE (agent/door.acreate is replaced): what is tested is everything the code does around it -
the spec is validated strictly, turned into ops the document's own rules accept, laid out, every text checked for
contrast, invented facts blanked; a bad answer is asked for once more and then fails loudly (502); no model = a
built-in layout that says so; an edit maps handles back and never deletes; the route is rate-limited, tenant-checked
and its ops reach a connected editor live; the tool makes / lists / extends files and never makes a public link."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.design import ai, ailayout, icons, templates
from app.design.doc import APPLIED, Doc, new_document

H = {"Authorization": "Bearer kd"}
PAGE = "0:1"
# every property the AI code may write on a node (docs/HOOLA_DESIGN_PLAN.md section 2, + its own settle mark)
ALLOWED = {"type", "parent", "idx", "name", "x", "y", "w", "h", "opacity", "fills", "strokes", "strokeWeight", "strokeAlign",
           "strokeCap", "strokeJoin", "radius", "effects", "clip", "layout", "sizeH", "sizeV", "minH", "chars", "font",
           "fontSize", "fontWeight", "lineHeight", "letterSpacing", "align", "autoResize", "textCase", "path", "aiSettle"}

CARD = {"notes": "A sign-in card.", "frames": [{
    "type": "frame", "name": "Sign in", "preset": "phone", "layout": "column", "pad": [56, 24, 24, 24], "gap": 24, "fill": "#0F172A",
    "children": [
        {"type": "text", "chars": "Welcome back", "size": 32, "weight": 700, "color": "#1E293B"},        # unreadable on #0F172A
        {"type": "text", "chars": "Sign in to see your orders and your saved addresses on this phone.", "size": 16, "color": "#E2E8F0"},
        {"type": "frame", "name": "Card", "layout": "column", "pad": 20, "gap": 12, "radius": 20, "fill": "#FFFFFF", "shadow": "md",
         "children": [
             {"type": "text", "chars": "Mobile number", "size": 14, "weight": 600, "color": "#0F172A"},
             {"type": "frame", "name": "Field", "layout": "row", "gap": 12, "pad": [0, 16, 0, 16], "h": 56, "radius": 14,
              "align": "center", "fill": "#F1F5F9", "children": [
                  {"type": "icon", "icon": "phone", "size": 20, "color": "#475569"},
                  {"type": "text", "chars": "Call 98765 43210 or pay ₹499", "size": 16, "color": "#475569", "w": "fill"}]},
             {"type": "frame", "name": "Button", "layout": "row", "pad": [16, 24, 16, 24], "radius": 999, "fill": "#4F46E5",
              "justify": "center", "align": "center", "children": [
                  {"type": "text", "chars": "Continue", "size": 16, "weight": 600, "color": "#FFFFFF"}]}]},
        {"type": "image", "label": "A happy customer", "h": 160, "radius": 20},
        {"type": "line", "color": "#334155"}]}]}


@pytest.fixture()
def design_env(env, tmp_path, monkeypatch):
    monkeypatch.setenv("API_KEY", "kd")
    monkeypatch.setenv("DESIGN_DIR", str(tmp_path / "design"))
    from app.config import get_settings
    get_settings.cache_clear()
    ai._CALLS.clear()
    ai._CLIENT = None
    yield monkeypatch
    get_settings.cache_clear()
    ai._CALLS.clear()
    ai._CLIENT = None


def client():
    from app.main import app
    return TestClient(app)


class FakeModel:
    """Replaces the house door's model call: answers with the queued texts and keeps what it was asked."""

    def __init__(self, monkeypatch, *answers):
        self.answers, self.asked = list(answers), []
        from app.agent import door

        async def acreate(_client, kw):
            self.asked.append(kw)
            text = self.answers.pop(0) if self.answers else "{}"
            if isinstance(text, Exception):
                raise text
            return SimpleNamespace(content=[SimpleNamespace(text=text if isinstance(text, str) else json.dumps(text))])
        monkeypatch.setattr(door, "acreate", acreate)

    def said(self, i: int) -> str:
        return self.asked[i]["messages"][0]["content"]


def new_file(c, **body):
    r = c.post("/api/design/files", headers=H, json=body)
    assert r.status_code == 200, r.text
    return r.json()


def doc_of(c, fid, headers=H):
    return c.get(f"/api/design/files/{fid}/doc", headers=headers).json()["doc"]["nodes"]


def kids_of(nodes):
    def kids(pid):
        return sorted((n for n in nodes if nodes[n].get("parent") == pid), key=lambda n: (nodes[n].get("idx", ""), n))
    return kids


def built(raw, prompt="a sign in screen", preset="phone"):
    spec = ai.clean_spec(json.loads(json.dumps(raw)), ai.Facts(prompt), {}, preset)
    return spec, ai.build(spec, ai.id_maker(9), PAGE, (100, 50))


# ----------------------------------------------------------------------------------- spec -> ops (no model at all)
def test_valid_spec_becomes_ops_the_document_accepts():
    spec, b = built(CARD)
    doc = Doc(new_document(""))
    assert all(doc.apply(op) == APPLIED for op in b["ops"]), "every op must pass the server's own rules, parents first"
    nodes, kids = doc.nodes, kids_of(doc.nodes)
    root = nodes[b["roots"][0]]
    assert root["type"] == "FRAME" and root["parent"] == PAGE and (root["x"], root["y"], root["w"], root["h"]) == (100, 50, 390, 844)
    assert root["layout"] == {"mode": "v", "gap": 24, "pad": [56, 24, 24, 24], "alignMain": "start", "alignCross": "start", "wrap": False}
    assert all(set(n) <= ALLOWED for nid, n in nodes.items() if nid.startswith("9:")), "only contract properties"
    assert all(nid.startswith("9:") for nid in (op["id"] for op in b["ops"])), "ids only from the given id maker"
    top = kids(b["roots"][0])
    assert [nodes[k]["type"] for k in top] == ["TEXT", "TEXT", "FRAME", "FRAME", "RECT"]
    title, para, card, picture, divider = (nodes[k] for k in top)
    # auto layout really ran on the server: a column, children one under the other inside the padding, 24 apart
    assert title["x"] == 24 and title["y"] == 56 and para["y"] == title["y"] + title["h"] + 24
    assert para["sizeH"] == "fill" and para["autoResize"] == "h" and para["w"] == 390 - 48 and para["h"] >= 2 * para["lineHeight"]
    assert card["sizeH"] == "fill" and card["sizeV"] == "hug" and card["w"] == 342 and card["effects"][0]["type"] == "drop"
    assert card["h"] == 20 + sum(nodes[k]["h"] for k in kids(top[2])) + 2 * 12 + 20
    assert divider["h"] == 1 and divider["w"] == 342 and divider["name"] == "Divider"
    assert picture["name"].startswith("Image /") and picture["h"] == 160 and picture["layout"]["alignMain"] == "center"
    field = nodes[kids(top[2])[1]]
    icon, words = (nodes[k] for k in kids(kids(top[2])[1]))
    assert field["h"] == 56 and icon["w"] == icon["h"] == 20 and words["sizeH"] == "fill"
    assert words["x"] == 16 + 20 + 12 and words["w"] == field["w"] - 32 - 20 - 12
    vec = nodes[kids(kids(kids(top[2])[1])[0])[0]]
    assert vec["type"] == "VECTOR" and vec["path"].startswith("M") and vec["strokes"] and vec["fills"] == []
    # every text carries its line height in px, so the browser's real layout gives the same heights
    assert all(isinstance(n["lineHeight"], (int, float)) for n in nodes.values() if n.get("type") == "TEXT")


def test_contrast_is_checked_in_code_and_fixed_once():
    spec, b = built(CARD)
    nodes = b["nodes"]
    title = next(n for n in nodes.values() if n.get("chars") == "Welcome back")
    assert title["fills"][0]["color"] != "#1E293B" and ai.contrast(title["fills"][0]["color"], "#0F172A") >= 4.5
    assert b["fixed"] >= 1
    kids = kids_of(nodes)
    for nid, n in nodes.items():                               # every text now reads on what is really behind it
        if n.get("type") == "TEXT":
            box = ai._abs_boxes(nodes, kids, b["roots"][0])
            bgs = ai.background_of(nodes, kids, box, nid)
            assert min(ai.contrast(n["fills"][0]["color"], bg) for bg in bgs) >= 4.5, n["chars"]
    ok = next(n for n in nodes.values() if n.get("chars") == "Continue")
    assert ok["fills"][0]["color"] == "#FFFFFF", "a colour that already reads is left alone"
    # a text over a gradient must read on BOTH ends; a shape under it in a free frame counts as its background
    assert ai.readable("#777777", ["#FFFFFF", "#000000"])[1] is True
    free = {"frames": [{"type": "frame", "preset": "instagram", "layout": "none", "fill": "#FFFFFF", "children": [
        {"type": "rect", "x": 0, "y": 0, "w": 1080, "h": 540, "fill": "#111827"},
        {"type": "text", "chars": "On the dark block", "size": 48, "color": "#1F2937", "x": 80, "y": 200},
        {"type": "text", "chars": "On the white part", "size": 48, "color": "#1F2937", "x": 80, "y": 700}]}]}
    _, fb = built(free, "post", "instagram")
    dark, light = (next(n for n in fb["nodes"].values() if n.get("chars") == c) for c in ("On the dark block", "On the white part"))
    assert ai.contrast(dark["fills"][0]["color"], "#111827") >= 4.5 and light["fills"][0]["color"] == "#1F2937"


def test_invented_facts_become_blanks_and_real_ones_stay():
    spec, _ = built(CARD, prompt="a sign in screen")
    chars = [c["chars"] for c in spec["frames"][0]["children"][2]["children"][1]["children"] if c["type"] == "text"][0]
    assert chars == "Call [phone number] or pay ₹[price]" and spec["blanked"] == 2
    spec, _ = built(CARD, prompt="sign in screen, support line 98765 43210, plan costs Rs 499")
    chars = [c["chars"] for c in spec["frames"][0]["children"][2]["children"][1]["children"] if c["type"] == "text"][0]
    assert chars == "Call 98765 43210 or pay ₹499" and spec["blanked"] == 0
    f = ai.Facts("mail us")
    assert f.guard("Lorem ipsum dolor sit amet") == "[Your text]" and f.guard("write to hi@shop.in") == "write to [email]"
    assert f.guard("Offers from 5 brands, 24 x 7") == "Offers from 5 brands, 24 x 7", "ordinary numbers are not facts to blank"


def test_oversize_spec_is_clamped():
    def deep(n):
        return {"type": "frame", "layout": "column", "children": [deep(n - 1)] if n else [{"type": "text", "chars": "bottom"}]}
    huge = {"frames": [{"type": "frame", "layout": "column", "children": [{"type": "text", "chars": f"row {i}"} for i in range(10000)]},
                       {"type": "frame", "layout": "column", "children": [deep(30), {"type": "text", "chars": "x" * 50000, "size": 99999}]}]
            + [{"type": "frame", "children": [{"type": "rect"}]} for _ in range(20)]}
    spec = ai.clean_spec(huge, None, {}, "")
    assert ai.count_nodes(spec) <= ai.MAX_NODES and len(spec["frames"]) <= ai.MAX_FRAMES and spec["dropped"] > 0
    assert len(spec["frames"][0]["children"]) <= ai.MAX_KIDS

    def depth(n):
        return 1 + max((depth(c) for c in n.get("children", [])), default=0)
    assert max(depth(f) for f in spec["frames"]) <= ai.MAX_DEPTH
    big = [c for c in spec["frames"][1]["children"] if c["type"] == "text"][0]
    assert len(big["chars"]) == ai.MAX_CHARS and big["size"] == 400
    b = ai.build(spec, ai.id_maker(3), PAGE, (0, 0))
    doc = Doc(new_document(""))
    assert all(doc.apply(op) == APPLIED for op in b["ops"]) and len(b["ops"]) < 1200


def test_hostile_spec_is_neutralised():
    hostile = {"__proto__": {"polluted": True}, "constructor": {"prototype": {"x": 1}}, "frames": [{
        "type": "frame", "name": "<script>alert(1)</script>", "preset": "phone", "layout": "column", "__proto__": {"a": 1},
        "id": "0:0", "parent": "0:0", "idx": "zzzz", "del": 1, "reactions": [{"action": "url", "url": "javascript:alert(1)"}],
        "w": 1e308, "h": -5, "gap": float("inf"), "pad": [1e99, "x", None, -4], "radius": "9e99", "opacity": 7,
        "fill": "url(javascript:alert(1))", "stroke": {"color": "red; background:url(x)", "width": 1e9},
        "children": [
            {"type": "script", "chars": "alert(1)"}, {"type": "DOCUMENT"}, {"type": "PAGE", "children": []}, "just a string", 42, None,
            {"type": "text", "chars": "<img src=x onerror=alert(1)>\u0000‮", "size": 10 ** 400, "weight": "bold",
             "color": "expression(alert(1))", "font": "Comic Sans; }", "onclick": "alert(1)", "__proto__": {"b": 2}},
            {"type": "icon", "icon": "../../etc/passwd"}, {"type": "icon", "icon": "heart", "size": 1e12, "path": "M0 0 <script>"},
            {"type": "image", "hash": "f" * 64, "label": "x" * 5000, "src": "http://evil.example/x.png"},
            {"type": "rect", "w": "fill", "h": "9999999999", "fill": {"from": "#fff", "to": "nope", "angle": "NaN"}, "path": "M0 0"},
        ]}]}
    spec = ai.clean_spec(hostile, ai.Facts(""), {}, "")
    b = ai.build(spec, ai.id_maker(4), PAGE, (0, 0))
    doc = Doc(new_document(""))
    assert all(doc.apply(op) == APPLIED for op in b["ops"])
    made = {nid: n for nid, n in doc.nodes.items() if nid.startswith("4:")}
    assert all(set(n) <= ALLOWED for n in made.values()), "no key the spec smuggled in reaches a node"
    assert {n["type"] for n in made.values()} <= {"FRAME", "TEXT", "RECT", "VECTOR"}
    assert "0:0" in doc.nodes and doc.nodes["0:0"]["type"] == "DOCUMENT" and PAGE in doc.nodes, "the root and the page are untouched"
    blob = json.dumps(made)
    assert "javascript:" not in blob and "evil.example" not in blob and "onerror=alert" in blob, "text stays text, nothing else survives"
    assert "\\u0000" not in blob and "__proto__" not in blob and "polluted" not in blob and "reactions" not in blob
    root = made[b["roots"][0]]
    assert root["name"] == "<script>alert(1)</script>" and (root["w"], root["h"]) == (390, 844), "a name is only ever drawn as text"
    text = next(n for n in made.values() if n["type"] == "TEXT")
    assert text["fontSize"] == 400 and text["font"] == "Inter" and text["fills"][0]["color"].startswith("#")
    for n in made.values():                                        # every number is finite and sane (a hugging frame may add its padding)
        for k in ("x", "y", "w", "h", "radius", "opacity", "fontSize", "strokeWeight"):
            v = n.get(k)
            assert v is None or (isinstance(v, (int, float)) and v == v and abs(v) <= 20000), (k, v)
    assert text["opacity"] if "opacity" in text else True
    assert root.get("opacity", 1) == 1 and root["layout"]["pad"] == [400, 0, 0, 0] and root["layout"]["gap"] == 0 and root["radius"] == 9
    assert not any(p.get("type") == "image" for n in made.values() for p in n.get("fills", [])), "an unknown asset hash is a placeholder"
    for junk in ("nope", [], {"frames": []}, {"frames": [{"type": "text", "chars": "no frame"}]}, {"frames": "x"}):
        with pytest.raises(ai.SpecError):
            ai.clean_spec(junk, None, {}, "")


def test_fonts_scripts_presets_icons_and_placement():
    assert ai.font_for("Poppins", "नमस्ते दुनिया") == "Poppins" and ai.font_for("Inter", "नमस्ते दुनिया") == "Noto Sans Devanagari"
    assert ai.font_for("Inter", "வணக்கம்") == "Noto Sans Tamil" and ai.font_for("papyrus", "Hello") == "Inter"
    three = {"frames": [{"type": "frame", "layout": "column", "children": [
        {"type": "text", "chars": "A" * 50, "font": "Sora"}, {"type": "text", "chars": "B" * 30, "font": "Inter"},
        {"type": "text", "chars": "C", "font": "Lobster"}]}]}
    fonts = {c["font"] for c in ai.clean_spec(three, None, {}, "")["frames"][0]["children"]}
    assert fonts == {"Sora", "Inter"}, "at most two font families"
    assert ai.preset_for("Diwali sale poster for my sweet shop") == "poster" and ai.preset_for("make an instagram post") == "instagram"
    assert ai.preset_for("login screen of my app") == "phone" and ai.preset_for("anything", "slide") == "slide" and ai.preset_for("hello") == ""
    assert len(icons.ICONS) >= 30 and icons.resolve("Shopping Cart") == "cart" and icons.resolve("nope") == ""
    for name in icons.ICONS:
        art = icons.build(name, 24)
        assert art["path"].startswith("M") and 0 <= art["x"] <= 24 and art["x"] + art["w"] <= 24.01 and art["y"] + art["h"] <= 24.01
        assert set(c for c in art["path"] if c.isalpha()) <= set("MLCZ")
    # new frames: on the asked spot when it is free, else to the right of what is there; several stand side by side
    nodes = {"0:0": {"type": "DOCUMENT"}, PAGE: {"type": "PAGE", "parent": "0:0", "idx": "a1"},
             "1:1": {"type": "FRAME", "parent": PAGE, "idx": "a1", "x": 0, "y": 40, "w": 390, "h": 844}}
    assert ai.place(nodes, PAGE, (390, 844), (2000, 500))[:2] == (2000 - 195, 500 - 422)
    assert ai.place(nodes, PAGE, (390, 844), (200, 300))[:2] == (490, 40) and ai.place(nodes, PAGE, (390, 844), None)[2] == "a1"
    spec = ai.clean_spec({"frames": [{"type": "frame", "preset": "phone", "children": [{"type": "text", "chars": f"s{i}"}]} for i in range(9)]}, None, {}, "")
    b = ai.build(spec, ai.id_maker(5), PAGE, (0, 0), "a1")
    xs = [b["nodes"][r]["x"] for r in b["roots"]]
    assert len(xs) == 6 and xs == [i * (390 + ai.FRAME_GAP) for i in range(6)]
    assert all(b["nodes"][r]["idx"] > "a1" for r in b["roots"]) and len({b["nodes"][r]["idx"] for r in b["roots"]}) == 6


def test_templates_are_good_specs_filled_from_her_words():
    cases = [("Diwali sale poster for my sweet shop", "poster", "Diwali sale"), ("food delivery app home screen", "phone", "Food delivery"),
             ("landing page for a yoga studio", "web", "Yoga studio"), ("business card for Asha Boutique", "card", "Asha Boutique"),
             ("instagram post: grand opening of Sharma Electronics", "instagram", "Grand opening of Sharma Electronics"),
             ("pitch deck slide about solar pumps", "slide", "Solar pumps"), ("logo for Chai Point", "logo", "Chai Point"),
             ("whatsapp status for monsoon offer", "whatsapp", "Monsoon offer"), ("दिवाली सेल का पोस्टर बनाओ", "poster", "दिवाली सेल")]
    for prompt, preset, headline in cases:
        assert ai.preset_for(prompt) == preset, prompt
        spec = ai.clean_spec(templates.make(prompt, preset, {}, 0), None, {}, preset)
        b = ai.build(spec, ai.id_maker(2), PAGE, (0, 0))
        doc = Doc(new_document(""))
        assert all(doc.apply(op) == APPLIED for op in b["ops"]), prompt
        texts = [n["chars"] for n in b["nodes"].values() if n.get("type") == "TEXT"]
        assert headline in texts, (prompt, texts[:6])
        assert b["fixed"] == 0, f"a built-in layout must not need a contrast fix: {prompt}"
        root = b["nodes"][b["roots"][0]]
        assert (root["w"], root["h"])[0] == ai.PRESETS[preset][1]
        blob = " ".join(texts)
        assert "lorem" not in blob.lower() and not any(ch.isdigit() for ch in blob.replace("+91", "").replace(" 1", "").replace(" 2", "").replace(" 3", "")), \
            f"no invented number in a template: {prompt}"
        kids = kids_of(b["nodes"])
        for nid, n in b["nodes"].items():                           # nothing sticks out of its auto layout parent
            parent = b["nodes"].get(n.get("parent"))
            if parent and isinstance(parent.get("layout"), dict) and n.get("type") != "VECTOR":
                assert n.get("x", 0) >= -0.5 and n.get("x", 0) + n["w"] <= parent["w"] + 0.5, (prompt, n.get("name"), n.get("x"), n["w"], parent["w"])
    hindi = ai.clean_spec(templates.make("दिवाली सेल का पोस्टर बनाओ", "poster", {}, 0), None, {}, "poster")
    b = ai.build(hindi, ai.id_maker(2), PAGE, (0, 0))
    assert {n["font"] for n in b["nodes"].values() if n.get("type") == "TEXT" and ai.script_of(n["chars"])} == {"Noto Sans Devanagari"}
    flow = templates.make("3 screens onboarding flow for a grocery app", "phone", {}, 0)
    assert [f["name"] for f in flow["frames"]] == ["Welcome", "Sign in", "Home"]
    kit = {"name": "Asha Boutique", "colors": {"primary": "#7C3AED", "dark": "#2E1065"}, "contact": {"phone": "98200 11122"}}
    branded = json.dumps(templates.make("instagram post for our new collection", "instagram", kit, 0))
    assert "Asha Boutique" in branded and "#7C3AED" in branded and "98200 11122" in branded


def test_server_layout_matches_the_browsers_rules():
    nodes = {"r": {"type": "FRAME", "w": 400, "h": 300, "layout": {"mode": "h", "gap": 10, "pad": [20, 20, 20, 20], "alignMain": "between", "alignCross": "center"}},
             "a": {"type": "RECT", "parent": "r", "w": 50, "h": 40}, "b": {"type": "RECT", "parent": "r", "w": 100, "h": 100, "sizeH": "fill"},
             "c": {"type": "RECT", "parent": "r", "w": 30, "h": 60, "sizeV": "fill"}}
    kids = {"r": ["a", "b", "c"]}
    ailayout.run(nodes, lambda i: kids.get(i, []), "r")
    assert (nodes["b"]["w"], nodes["b"]["x"]) == (400 - 40 - 50 - 30 - 20, 80) and nodes["c"]["h"] == 260 and nodes["c"]["x"] == 350
    assert nodes["a"]["y"] == 20 + (260 - 40) / 2
    assert ailayout.text_lines({"chars": "one two three four five six", "fontSize": 20}, 100)[0] > 1
    assert ailayout.text_width("नमस्ते", "Noto Sans Devanagari", 20) < ailayout.text_width("नमस्तेनमस्ते", "Noto Sans Devanagari", 20)


# ----------------------------------------------------------------------------------- the model (fake) + the route
def test_route_adds_a_design_live_to_a_connected_editor(design_env):
    fake = FakeModel(design_env, CARD)
    with client() as c:
        fid = new_file(c, name="Live")["id"]
        with c.websocket_connect(f"/api/design/ws?file={fid}", headers=H) as sock:
            init = sock.receive_json()
            assert init["t"] == "init"
            r = c.post(f"/api/design/files/{fid}/ai", headers=H, json={"prompt": "a sign in screen for my shop", "page": PAGE, "x": 500, "y": 500})
            assert r.status_code == 200, r.text
            out = r.json()
            frame = sock.receive_json()                             # the SAME ops arrive on the open socket
            while frame["t"] != "ops":
                frame = sock.receive_json()
            assert frame["by"] == 0 and frame["seq"] == out["seq"] and len(frame["ops"]) == out["nodes"]
            assert frame["ops"][0]["id"] == out["roots"][0] and frame["ops"][0]["p"]["type"] == "FRAME"
            own = {op["id"].split(":")[0] for op in frame["ops"]}
            assert len(own) == 1 and own != {str(init["cid"])} and own != {"0"}, "ids minted under a client number of their own"
        assert out["engine"] == "model" and out["mode"] == "new" and out["frames"][0]["name"] == "Sign in" and out["rejected"] == 0
        assert out["contrast_fixed"] >= 1 and out["blanked"] == 2 and out["left"] == 19 and out["notes"] == "A sign-in card."
        nodes = doc_of(c, fid)
        root = nodes[out["roots"][0]]
        assert root["parent"] == PAGE and root["w"] == 390 and isinstance(root["aiSettle"], str)
        assert (root["x"], root["y"]) == (500 - 195, 500 - 422), "centred on the asked point (the page was empty)"
        # the model was asked through the house door with the rulebook, the preset the words name, and her words
        kw = fake.asked[0]
        assert "8-point scale" in kw["system"] and "4.5:1" in kw["system"] and "lorem ipsum" in kw["system"] and "arrow-right" in kw["system"]
        assert "a sign in screen for my shop" in fake.said(0) and '"phone"' in fake.said(0) and len(fake.asked) == 1
        # a second design goes to the right of the first; "Remove" on the client is an ordinary delete of the roots
        fake.answers.append(CARD)
        second = c.post(f"/api/design/files/{fid}/ai", headers=H, json={"prompt": "another sign in screen", "x": 500, "y": 500}).json()
        assert doc_of(c, fid)[second["roots"][0]]["x"] == root["x"] + 390 + 100


def test_invalid_json_gets_one_retry_with_the_error(design_env):
    fake = FakeModel(design_env, "Sure! Here is your design: ```json\n{\"frames\": [{\"type\": \"frame\", \"children\": [", CARD)
    with client() as c:
        fid = new_file(c)["id"]
        r = c.post(f"/api/design/files/{fid}/ai", headers=H, json={"prompt": "a sign in screen"})
        assert r.status_code == 200, r.text
        assert len(fake.asked) == 2 and "YOUR PREVIOUS ANSWER COULD NOT BE USED" in fake.said(1) and "a sign in screen" in fake.said(1)
        assert r.json()["engine"] == "model" and len(doc_of(c, fid)) > 10
    # an answer wrapped in a fence and a sentence is read without a retry
    assert ai.parse_json("Here you go:\n```json\n{\"frames\": []}\n```\nHope it helps")["frames"] == []


def test_garbage_twice_is_a_loud_502_and_nothing_is_added(design_env):
    fake = FakeModel(design_env, "I can not do that.", {"frames": [{"type": "nothing"}]})
    with client() as c:
        fid = new_file(c)["id"]
        r = c.post(f"/api/design/files/{fid}/ai", headers=H, json={"prompt": "a poster"})
        assert r.status_code == 502 and "Nothing was added" in r.json()["detail"] and len(fake.asked) == 2
        assert set(doc_of(c, fid)) == {"0:0", PAGE}
        fake.answers.append(RuntimeError("connection reset"))                         # the model itself fails: also plain, no retry storm
        r = c.post(f"/api/design/files/{fid}/ai", headers=H, json={"prompt": "a poster"})
        assert r.status_code == 502 and "connection reset" not in r.text and len(fake.asked) == 3
        assert set(doc_of(c, fid)) == {"0:0", PAGE}


def test_no_model_configured_falls_back_to_a_template_and_says_so(design_env):
    design_env.setenv("ANTHROPIC_API_KEY", "")
    design_env.setenv("CHAT_LLM", "claude")
    from app.config import get_settings
    get_settings.cache_clear()
    fake = FakeModel(design_env)
    assert ai.model_ready() == ""
    with client() as c:
        fid = new_file(c)["id"]
        r = c.post(f"/api/design/files/{fid}/ai", headers=H, json={"prompt": "Diwali sale poster for my sweet shop"})
        assert r.status_code == 200, r.text
        out = r.json()
        assert out["engine"] == "template" and "built-in" in out["notes"] and fake.asked == []
        nodes = doc_of(c, fid)
        assert (nodes[out["roots"][0]]["w"], nodes[out["roots"][0]]["h"]) == (1240, 1754)
        assert "Diwali sale" in [n.get("chars") for n in nodes.values()]
        edit = c.post(f"/api/design/files/{fid}/ai", headers=H, json={"prompt": "make it dark", "mode": "edit", "selection": out["roots"]})
        assert edit.status_code == 503 and "AI model" in edit.json()["detail"], "an edit needs a model and says so"
    design_env.setenv("ANTHROPIC_API_KEY", "test")
    design_env.setenv("DESIGN_AI_ENGINE", "template")                                 # the owner's switch: built-in layouts only
    get_settings.cache_clear()
    assert ai.model_ready() == ""


def test_edit_maps_handles_validates_props_and_never_deletes(design_env):
    fake = FakeModel(design_env, CARD)
    with client() as c:
        fid = new_file(c)["id"]
        made = c.post(f"/api/design/files/{fid}/ai", headers=H, json={"prompt": "a sign in screen"}).json()
        root = made["roots"][0]
        before = doc_of(c, fid)
        kids = kids_of(before)
        title, para, card = kids(root)[:3]
        fake.answers.append({"notes": "Dark premium look, Hindi title.", "changes": [
            {"handle": "n1", "set": {"fill": "#020617", "gap": 30, "type": "PAGE", "parent": "0:0", "idx": "a", "x": 9999, "reactions": [{}]}},
            {"handle": "n2", "set": {"chars": "वापसी पर स्वागत है", "size": 36, "color": "#0B1220", "__proto__": {"x": 1}, "path": "M0 0"}},
            {"handle": "n4", "set": {"radius": 28, "fill": {"from": "#1E293B", "to": "#0F172A", "angle": 180}}},
            {"handle": "n4", "delete": True}, {"handle": "n999", "set": {"fill": "#FF0000"}}, {"handle": "n3", "del": 1, "set": {}}],
            "add": [{"parent": "n4", "after": "n5", "node": {"type": "text", "chars": "Plans from ₹999 a month", "size": 14, "color": "#94A3B8"}},
                    {"parent": "n2", "node": {"type": "rect"}}, {"parent": "zz", "node": {"type": "rect"}}]})
        r = c.post(f"/api/design/files/{fid}/ai", headers=H, json={"prompt": "make it premium and dark, title in Hindi", "mode": "edit", "selection": [root]})
        assert r.status_code == 200, r.text
        out = r.json()
        after = doc_of(c, fid)
        assert set(before) <= set(after), "an edit never deletes a layer"
        assert len(out["added"]) == 1 and set(after) - set(before) == set(out["added"])
        # the model saw handles and words, never an id
        listing = fake.said(1)
        assert "n1 frame" in listing and '"Welcome back"' in listing and root not in listing and title not in listing
        # allowed changes landed, in contract words
        assert after[root]["fills"][0]["color"] == "#020617" and after[root]["layout"]["gap"] == 32, "spacing snaps to the 4-pt grid"
        assert after[title]["chars"] == "वापसी पर स्वागत है" and after[title]["fontSize"] == 36 and after[title]["font"] == "Noto Sans Devanagari"
        assert after[card]["radius"] == 28 and after[card]["fills"][0]["type"] == "linear"
        # forbidden ones did not: type / parent / order / position / prototype links, a delete, a handle outside the selection
        assert after[root]["type"] == "FRAME" and after[root]["parent"] == PAGE and after[root]["idx"] == before[root]["idx"]
        assert after[root]["x"] == before[root]["x"] and "reactions" not in after[root] and "path" not in after[title]
        refused = " ".join(out["refused"])
        for word in ("n1.type", "n1.parent", "n1.x", "n1.reactions", "n2.path", "never deletes", "n999", "not a frame"):
            assert word in refused, (word, refused)
        # the new child sits right after n5 inside the card, with a blank instead of the invented price
        new = after[out["added"][0]]
        order = kids_of(after)(card)
        assert new["parent"] == card and order.index(out["added"][0]) == 1 and new["chars"] == "Plans from ₹[price] a month"
        # contrast is checked again: the dark title on the darker screen was lightened, the text on the new dark card too
        assert ai.contrast(after[title]["fills"][0]["color"], "#020617") >= 4.5
        label = next(k for k in order if after[k].get("chars") == "Mobile number")
        assert min(ai.contrast(after[label]["fills"][0]["color"], bg) for bg in ("#1E293B", "#0F172A")) >= 4.5
        # the server laid the changed text and the grown card out again; an untouched text kept its measured size
        assert after[title]["h"] == after[title]["lineHeight"] and after[card]["h"] > before[card]["h"]
        assert (after[para]["w"], after[para]["h"]) == (before[para]["w"], before[para]["h"])
        # no selection / an unknown one / nothing changed
        assert c.post(f"/api/design/files/{fid}/ai", headers=H, json={"prompt": "x", "mode": "edit", "selection": []}).status_code == 400
        assert c.post(f"/api/design/files/{fid}/ai", headers=H, json={"prompt": "x", "mode": "edit", "selection": ["0:0", "9:9"]}).status_code == 400
        fake.answers.append({"notes": "It already is.", "changes": []})
        same = c.post(f"/api/design/files/{fid}/ai", headers=H, json={"prompt": "make the title Hindi", "mode": "edit", "selection": [title]}).json()
        assert same["touched"] == [] and same["notes"] == "It already is."


def test_rate_limit_prompt_cap_and_switch(design_env):
    design_env.setenv("DESIGN_AI_PER_HOUR", "2")
    from app.config import get_settings
    get_settings.cache_clear()
    FakeModel(design_env, CARD, CARD, CARD)
    with client() as c:
        fid = new_file(c)["id"]
        for bad in ({"prompt": ""}, {"prompt": "   "}, {"prompt": "x" * 2001}, {"prompt": 7}, {}):
            assert c.post(f"/api/design/files/{fid}/ai", headers=H, json=bad).status_code == 400, bad
        assert c.post(f"/api/design/files/{fid}/ai", headers=H, json=[1]).status_code in (400, 422)
        assert [c.post(f"/api/design/files/{fid}/ai", headers=H, json={"prompt": "a screen"}).status_code for _ in range(3)] == [200, 200, 429]
        assert "later" in c.post(f"/api/design/files/{fid}/ai", headers=H, json={"prompt": "a screen"}).json()["detail"]
        design_env.setenv("DESIGN_AI", "false")
        get_settings.cache_clear()
        ai._CALLS.clear()
        assert c.post(f"/api/design/files/{fid}/ai", headers=H, json={"prompt": "a screen"}).status_code == 403


def test_other_tenant_guest_and_signed_out_are_refused(design_env):
    from app import accounts
    from app.db import User, session
    fake = FakeModel(design_env, CARD, CARD)
    with client() as c:
        fid = new_file(c)["id"]
        with session() as s:
            u = User(email="other@example.com", name="Other Person")
            s.add(u)
            s.flush()
            uid = u.id
        other = {"Authorization": f"Bearer {accounts.issue_session(uid)}"}
        r = c.post(f"/api/design/files/{fid}/ai", headers=other, json={"prompt": "a screen"})
        assert r.status_code == 404 and fake.asked == [], "another tenant's file: not found, and the model is never asked"
        token = c.post(f"/api/design/files/{fid}/share", headers=H, json={"role": "view"}).json()["token"]
        for headers in ({}, {"Authorization": f"Bearer {token}"}, {"Authorization": "Bearer wrong"}):
            assert c.post(f"/api/design/files/{fid}/ai", headers=headers, json={"prompt": "a screen"}).status_code == 401, headers
        assert fake.asked == [] and set(doc_of(c, fid)) == {"0:0", PAGE}, "a view-only guest (a share link) can not ask"
        mine = new_file(c)["id"]                                                       # an edit can not reach into another file's layers
        made = c.post(f"/api/design/files/{mine}/ai", headers=H, json={"prompt": "a screen"}).json()
        r = c.post(f"/api/design/files/{fid}/ai", headers=H, json={"prompt": "dark", "mode": "edit", "selection": made["roots"]})
        assert r.status_code == 400 and len(fake.asked) == 1


# ----------------------------------------------------------------------------------- the agent tool
def test_tool_is_registered_tight_and_reaches_a_call():
    from app import voice
    from app.agent import admit, tools
    assert "hoola_design" in tools.HANDLERS and tools.FAMILY_OF["hoola_design"] == "design"
    assert sum(1 for t in tools.TOOLS if t["name"] == "hoola_design") == 1
    assert voice.call_route("hoola_design") == "kaam" and "hoola_design" in voice.VOICE_VIA_KAAM and "hoola_design" not in voice.VOICE_TOOL_NAMES
    from app.agent import toolsearch
    spec = next(t for t in tools.TOOLS if t["name"] == "hoola_design")
    assert toolsearch.schema_ok(spec) if hasattr(toolsearch, "schema_ok") else True
    opens = ["make a wireframe for my app", "ui screen for login", "hoola design mein ek file banao", "figma jaisa mockup banao",
             "open my design file", "app mockup chahiye", "ek वायरफ्रेम बनाओ"]
    stays = ["website design karo", "poster design banao", "design doc likho", "photo banao diwali ki", "logo banao", "namaste",
             "interior design ghar ka", "ek pdf report banao", "landing page banao", "is photo ka background hatao", "game design document"]
    for text in opens:
        assert "design" in admit._match(text.lower()) and "design" in admit._match(text.lower(), True), text
    for text in stays:
        assert "design" not in admit._match(text.lower()) and "design" not in admit._match(text.lower(), True), text
    # the bare word keeps opening the families that had it before this tool carried it
    assert {"graphic", "uiux"} <= admit._match("poster design banao") and "site" in admit._match("website design karo")


def test_tool_create_list_add_share(design_env):
    from app.agent import design_tools
    from app.agent.tools import Ctx, ToolError
    from app.config import get_settings
    from app.design import store
    fake = FakeModel(design_env, CARD, CARD)
    ctx = Ctx(tenant_id=get_settings().tenant_id, conversation_id="c1")
    run = lambda **a: asyncio.run(design_tools.hoola_design(ctx, **a))      # noqa: E731
    made = run(action="create", prompt="a sign in screen for my tailoring shop app")
    assert made["status"] == "done" and made["link"].endswith(f"/console/design#/f/{made['file_id']}") and made["engine"] == "model"
    assert made["name"] == "Tailoring shop" and made["frames"] == ["Sign in (390 x 844)"] and made["preview"] is None
    assert "no renderer" in made["preview_note"] and made["blanked"] == 2
    listed = run(action="list")
    assert [f["file_id"] for f in listed["files"]] == [made["file_id"]] and listed["files"][0]["layers"] > 10
    more = run(action="add", file="tailoring shop", prompt="one more screen", preset="android")
    assert more["file_id"] == made["file_id"] and len(fake.asked) == 2 and '"android"' in fake.said(1)
    with client() as c:
        nodes = doc_of(c, made["file_id"])
        tops = [n for n in nodes.values() if n.get("parent") == PAGE]
        assert sorted(n["w"] for n in tops) == [360, 390] and len({n["x"] for n in tops}) == 2
        # share: the tool never makes the public link ...
        said = run(action="share", file=made["file_id"])
        assert said["status"] == "her_tap" and "Share" in said["note"] and "view_link" not in said
        assert store.get_file(ctx.tenant_id, made["file_id"])["share"] is None
        # ... and only repeats one she already switched on herself
        token = c.post(f"/api/design/files/{made['file_id']}/share", headers=H, json={"role": "view"}).json()["token"]
        again = run(action="share", file=made["file_id"])
        assert again["status"] == "already_shared" and again["view_link"].endswith(f"#/s/{token}")
    # a failed design leaves no empty file behind and is said plainly
    fake.answers += ["nope", "still nope"]
    with pytest.raises(ToolError) as e:
        run(action="create", prompt="a poster", name="Broken")
    assert "Nothing was made" in str(e.value) and [f["name"] for f in run(action="list")["files"]] == ["Tailoring shop"]
    for bad in ({"action": "create"}, {"action": "add", "file": "no such file", "prompt": "x"}, {"action": "create", "prompt": "x", "preset": "billboard"},
                {"action": "delete", "file": made["file_id"]}, {"action": "share"}):
        with pytest.raises(ToolError):
            run(**bad)
    other = Ctx(tenant_id="someone-else", conversation_id="c2")                      # another tenant sees and reaches nothing
    assert asyncio.run(design_tools.hoola_design(other, action="list"))["files"] == []
    with pytest.raises(ToolError):
        asyncio.run(design_tools.hoola_design(other, action="add", file=made["file_id"], prompt="x"))


def test_tool_without_a_model_uses_a_template_and_says_so(design_env):
    design_env.setenv("ANTHROPIC_API_KEY", "")
    design_env.setenv("CHAT_LLM", "claude")
    from app.agent import design_tools
    from app.agent.tools import Ctx
    from app.config import get_settings
    get_settings.cache_clear()
    out = asyncio.run(design_tools.hoola_design(Ctx(tenant_id=get_settings().tenant_id, conversation_id=""), action="create",
                                                prompt="instagram post: grand opening of Sharma Electronics"))
    assert out["engine"] == "template" and "BUILT-IN" in out["note"] and out["frames"] == ["Post (1080 x 1080)"]
