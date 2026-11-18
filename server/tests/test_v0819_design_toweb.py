"""v0.819 D7 bridge B: a Hoola Design frame -> Web Studio (docs/HOOLA_DESIGN_PLAN.md section 7 B).

frame_to_html: semantic, responsive, clean HTML + CSS (auto layout -> flex, a free composition -> a box of its own
aspect ratio in container units that stacks on a phone, text roles by size, buttons, pictures, gradients, shadows,
vectors / booleans as inline SVG, warnings for what does not translate) that passes the website builder's own cleaner
untouched. The route hands it to Web Studio through Web Studio's own code: a new site (site.service.new), a section
added to a built site's page (site.code.clean + the save job = a checked version), pictures in the SITE's photo store;
view-only / other tenants refused; nothing published."""
import io
import json
import os
import re
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient

from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

H = {"Authorization": "Bearer kd"}
SHA = "a" * 64


# ------------------------------------------------------------------------------------------- documents
def _base():
    return {"0:0": {"type": "DOCUMENT", "name": "Doc"}, "0:1": {"type": "PAGE", "parent": "0:0", "idx": "a", "name": "Page 1"}}


def hero_doc(sha=SHA):
    """A 1440 wide hero band: auto layout, a big title, a lead, two buttons (one with her own link), a photo, a star."""
    n = _base()
    n["1:1"] = dict(type="FRAME", parent="0:1", idx="a", name="Hero", x=0, y=0, w=1440, h=800,
                    fills=[{"type": "linear", "stops": [{"pos": 0, "color": "#1E1B4B"}, {"pos": 1, "color": "#7C3AED"}],
                            "from": [0, 0], "to": [1, 1]}],
                    layout={"mode": "v", "gap": 24, "pad": [96, 120, 96, 120], "alignMain": "center", "alignCross": "start"})
    n["1:2"] = dict(type="TEXT", parent="1:1", idx="a", name="Title", chars="Sweets made fresh every morning", font="Fraunces",
                    fontSize=72, fontWeight=700, fills=[{"type": "solid", "color": "#FFFFFF"}], autoResize="h", w=900, h=180)
    n["1:3"] = dict(type="TEXT", parent="1:1", idx="b", name="Lead", chars="Order on WhatsApp, pick up in 20 minutes.",
                    font="Inter", fontSize=20, fills=[{"type": "solid", "color": "#E0E7FF"}], lineHeight=30)
    n["1:4"] = dict(type="FRAME", parent="1:1", idx="c", name="Buttons", w=400, h=56, layout={"mode": "h", "gap": 12},
                    sizeH="hug", sizeV="hug", clip=False)
    n["1:5"] = dict(type="FRAME", parent="1:4", idx="a", name="Primary button", w=180, h=56, radius=12,
                    fills=[{"type": "solid", "color": "#F59E0B"}], sizeH="hug", sizeV="hug",
                    layout={"mode": "h", "pad": [16, 24, 16, 24], "alignMain": "center", "alignCross": "center"},
                    effects=[{"type": "drop", "x": 0, "y": 8, "blur": 24, "spread": 0, "color": "#000000", "opacity": 0.3}])
    n["1:6"] = dict(type="TEXT", parent="1:5", idx="a", name="Label", chars="Order now", fontSize=18, fontWeight=600,
                    fills=[{"type": "solid", "color": "#111111"}])
    n["1:7"] = dict(type="FRAME", parent="1:4", idx="b", name="Ghost", w=160, h=56, radius=12, strokeWeight=2,
                    strokes=[{"type": "solid", "color": "#FFFFFF"}], strokeAlign="inside", sizeH="hug", sizeV="hug",
                    layout={"mode": "h", "pad": [16, 24, 16, 24], "alignMain": "center", "alignCross": "center"},
                    reactions=[{"trigger": "click", "action": "url", "url": "https://example.com/menu"}])
    n["1:8"] = dict(type="TEXT", parent="1:7", idx="a", name="Label", chars="See menu", fontSize=18, fontWeight=600,
                    fills=[{"type": "solid", "color": "#FFFFFF"}])
    n["1:9"] = dict(type="RECT", parent="1:1", idx="d", name="Shop photo", w=600, h=320, radius=16,
                    fills=[{"type": "image", "hash": sha, "mode": "fill"}])
    n["1:10"] = dict(type="STAR", parent="1:1", idx="e", name="Sparkle", w=40, h=40, sides=5, ratio=0.4, x=1300, y=60,
                     fills=[{"type": "solid", "color": "#FDE68A"}], layoutPos="absolute")
    n["1:11"] = dict(type="TEXT", parent="1:1", idx="f", name="Small print", chars="Open 8 am to 10 pm", fontSize=14,
                     fills=[{"type": "solid", "color": "#C7D2FE"}], blend="overlay",
                     effects=[{"type": "blur", "blur": 4}])
    return {"nodes": n}


def card_doc(sha=SHA):
    """A 360 wide card WITHOUT auto layout: a backdrop, a round photo, texts with a styled run, a button, a boolean badge."""
    n = _base()
    n["2:1"] = dict(type="FRAME", parent="0:1", idx="b", name="Product card", w=360, h=480, radius=20,
                    fills=[{"type": "solid", "color": "#FFFFFF"}],
                    effects=[{"type": "drop", "x": 0, "y": 4, "blur": 16, "spread": 0, "color": "#0F172A", "opacity": 0.12}])
    n["2:2"] = dict(type="RECT", parent="2:1", idx="a", name="Background", x=0, y=0, w=360, h=480,
                    fills=[{"type": "solid", "color": "#FFF7ED"}])
    n["2:3"] = dict(type="ELLIPSE", parent="2:1", idx="b", name="Product image", x=60, y=30, w=240, h=240,
                    fills=[{"type": "image", "hash": sha}])
    n["2:4"] = dict(type="TEXT", parent="2:1", idx="c", name="Name", x=24, y=300, w=312, h=40, chars="Kaju katli",
                    fontSize=28, fontWeight=700, fills=[{"type": "solid", "color": "#1C1917"}])
    n["2:5"] = dict(type="TEXT", parent="2:1", idx="d", name="Price", x=24, y=350, w=200, h=24, chars="Rs 900 / kg", fontSize=18,
                    fills=[{"type": "solid", "color": "#57534E"}], runs=[{"s": 0, "e": 6, "fontWeight": 700, "color": "#B45309"}])
    n["2:6"] = dict(type="FRAME", parent="2:1", idx="e", name="Add", x=24, y=400, w=140, h=48, radius=24,
                    fills=[{"type": "solid", "color": "#B45309"}])
    n["2:7"] = dict(type="TEXT", parent="2:6", idx="a", name="t", x=30, y=12, w=80, h=24, chars="Add to cart", fontSize=16,
                    fills=[{"type": "solid", "color": "#FFFFFF"}])
    n["2:8"] = dict(type="GROUP", parent="2:1", idx="f", name="Badge", x=290, y=20, w=50, h=50, bool="subtract",
                    fills=[{"type": "solid", "color": "#DC2626"}])
    n["2:9"] = dict(type="ELLIPSE", parent="2:8", idx="a", x=0, y=0, w=50, h=50)
    n["2:10"] = dict(type="RECT", parent="2:8", idx="b", x=20, y=20, w=10, h=10)
    n["2:11"] = dict(type="VECTOR", parent="2:1", idx="g", name="Heart", x=300, y=420, w=24, h=22,
                     path="M12 21L2 10C-1 6 3 0 8 3L12 6L16 3C21 0 25 6 22 10Z", fills=[{"type": "solid", "color": "#DC2626"}])
    n["2:12"] = dict(type="RECT", parent="2:1", idx="h", name="Shine", x=10, y=10, w=20, h=20, mask=True)
    return {"nodes": n}


def nav_doc():
    """A nav bar: brand, links, and an INSTANCE of a button component with its label overridden."""
    n = _base()
    n["3:1"] = dict(type="FRAME", parent="0:1", idx="c", name="Nav bar", w=1440, h=80, fills=[{"type": "solid", "color": "#0B0A1A"}],
                    layout={"mode": "h", "pad": [20, 48, 20, 48], "alignMain": "between", "alignCross": "center"})
    n["3:2"] = dict(type="TEXT", parent="3:1", idx="a", name="Logo", chars="Sharma Sweets", fontSize=24, fontWeight=700,
                    fills=[{"type": "solid", "color": "#FFFFFF"}])
    n["3:3"] = dict(type="FRAME", parent="3:1", idx="b", name="Links", w=400, h=24, layout={"mode": "h", "gap": 32},
                    sizeH="hug", sizeV="hug")
    for i, t in enumerate(["Home", "Menu", "Contact"]):
        n[f"3:{10 + i}"] = dict(type="TEXT", parent="3:3", idx="abc"[i], name=t, chars=t, fontSize=16,
                               fills=[{"type": "solid", "color": "#D7D2F2"}])
    n["3:4"] = dict(type="INSTANCE", parent="3:1", idx="c", name="CTA", comp="9:1", w=140, h=44, ov={"9:2": {"chars": "Call us"}})
    n["9:1"] = dict(type="COMPONENT", parent="0:1", idx="z", name="Button", w=140, h=44, radius=22,
                    fills=[{"type": "solid", "color": "#FFB15C"}], sizeH="hug", sizeV="hug",
                    layout={"mode": "h", "pad": [12, 20, 12, 20], "alignMain": "center", "alignCross": "center"})
    n["9:2"] = dict(type="TEXT", parent="9:1", idx="a", name="Label", chars="Button", fontSize=16, fontWeight=600,
                    fills=[{"type": "solid", "color": "#1B1030"}])
    return {"nodes": n}


def all_doc(sha=SHA):
    n = {}
    for d in (hero_doc(sha), card_doc(sha), nav_doc()):
        n.update(d["nodes"])
    return {"nodes": n}


def png(w=64, h=48, rgba=False):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGBA" if rgba else "RGB", (w, h), (200, 120, 40, 120) if rgba else (200, 120, 40)).save(buf, "PNG")
    return buf.getvalue()


# ------------------------------------------------------------------------------------------- 1. the code
def test_hero_auto_layout_text_roles_buttons_picture():
    from app.design import toweb as W
    o = W.frame_to_html(hero_doc(), "1:1")
    h, css = o["html"], o["css"]
    assert h.startswith('<section class="d-hero">') and "<script" not in h and " style=" not in h
    assert not re.search(r"\son\w+=", h)
    assert h.count("<h1") == 1 and '<h1 class="d-title">Sweets made fresh every morning</h1>' in h
    assert '<p class="d-lead">' in h and '<p class="d-small-print">' in h
    # buttons: her prototype link is kept, the other one is "#" with a TODO - never an invented link
    assert '<a class="btn d-primary-button" href="#"><!-- TODO: link --><span class="d-label">Order now</span></a>' in h
    assert '<a class="btn d-ghost" href="https://example.com/menu">' in h
    assert re.search(r'<img class="d-shop-photo-img" src="/api/design/assets/a{64}" alt="Shop photo"', h)
    assert '<svg class="d-sparkle" viewBox="0 0 40 40"' in h and "<path d=\"M20 0L" in h
    # flexbox from auto layout; the band carries the gradient, the box the layout
    box = _block(css, ".d-hero-box")
    for d in ("display:flex", "flex-direction:column", "justify-content:center", "gap:24px", "padding:96px 120px",
              "max-width:1440px", "min-height:800px"):
        assert d in box, d
    assert "background:linear-gradient(119.05deg, #1E1B4B 0%, #7C3AED 100%)" in _block(css, ".d-hero")
    title = _block(css, ".d-title")
    assert "font-size:clamp(43px, 5vw, 72px)" in title and "width:900px" in title and "max-width:100%" in title
    assert '"Fraunces", var(--font-head' in title and "white-space:pre-line" in title
    assert "line-height:1.5" in _block(css, ".d-lead")                         # 30 px on 20 px = a unitless ratio
    assert "box-shadow:0 8px 24px 0 rgba(0, 0, 0, 0.3)" in _block(css, ".d-primary-button")
    assert "border:2px solid #FFFFFF" in _block(css, ".d-ghost")
    assert "object-fit:cover" in _block(css, ".d-shop-photo-img") and "border-radius:16px" in _block(css, ".d-shop-photo")
    # phone: the wide column keeps flowing, its padding comes down; the decorative star is hidden and that is SAID
    phone = css.split("@media (max-width: 640px)", 1)[1]
    assert ".d-hero-box" in phone and "padding:24px" in phone and "min-height:0" in phone
    assert "display:none" in _block(phone, ".d-sparkle")
    assert any("Blend modes" in w and "Small print" in w for w in o["warnings"])
    assert any("Blur effects" in w for w in o["warnings"])
    assert any("decorative shape" in w for w in o["warnings"])
    assert o["images"] == [{"hash": SHA, "name": "shop-photo", "alt": "Shop photo", "node": "1:9"}]
    assert {f["family"] for f in o["fonts"]} == {"Fraunces", "Inter"} and all(f["shipped"] for f in o["fonts"])


def test_free_card_container_units_runs_boolean_vector_mask():
    from app.design import toweb as W
    o = W.frame_to_html(card_doc(), "2:1")
    h, css = o["html"], o["css"]
    box = _block(css, ".d-product-card-box")
    assert "container-type:inline-size" in box and "aspect-ratio:360 / 480" in box and "max-width:360px" in box
    assert "background:#FFFFFF" in box and "border-radius:20px" in box and "box-shadow:0 4px 16px 0 rgba(15, 23, 42, 0.12)" in box
    # the full-size bottom rectangle is the card's backdrop: inset, not a stacked block
    assert "inset:0" in _block(css, ".d-background") and 'class="d-background" aria-hidden="true"' in h
    # children in container units of the card (scales like a picture)
    assert "left:16.667cqw" in _block(css, ".d-product-image") and "border-radius:50%" in _block(css, ".d-product-image")
    assert "font-size:clamp(10px, 7.778cqw, 28px)" in _block(css, ".d-name")
    assert '<p class="d-price"><span class="d-price-r1">Rs 900</span> / kg</p>' in h
    assert "color:#B45309" in _block(css, ".d-price-r1") and "font-weight:700" in _block(css, ".d-price-r1")
    assert '<a class="btn d-add" href="#"><!-- TODO: link --><span class="d-t">Add to cart</span></a>' in h
    # boolean subtract = a mask; a vector = its own path; the mask layer itself is left out and named
    assert '<mask id="dm1"' in h and 'mask="url(#dm1)"' in h and "<svg class=\"d-badge\"" in h
    assert 'd="M12 21L2 10C-1 6 3 0 8 3L12 6L16 3C21 0 25 6 22 10Z"' in h
    assert "d-shine" not in h and any("Masks" in w and "Shine" in w for w in o["warnings"])
    # a narrow composition keeps its shape on a phone (no stacking rule for it)
    phone = css.split("@media", 1)[1] if "@media" in css else ""
    assert "flex-direction:column" not in _block(phone, ".d-product-card-box")
    assert o["html"].count("<h1") == 1


def test_nav_links_instance_override_and_section_headings():
    from app.design import toweb as W
    o = W.frame_to_html(nav_doc(), "3:1")
    h, css = o["html"], o["css"]
    assert '<nav class="d-nav-bar-box">' in h
    assert '<p class="d-logo">Sharma Sweets</p>' in h                              # the brand, not a link
    for t in ("Home", "Menu", "Contact"):
        assert f'href="#"><!-- TODO: link -->{t}</a>' in h
    assert '<a class="btn d-cta" href="#"><!-- TODO: link --><span class="d-label">Call us</span></a>' in h   # the override
    assert "background:#FFB15C" in _block(css, ".d-cta") and "border-radius:22px" in _block(css, ".d-cta")
    phone = css.split("@media (max-width: 640px)", 1)[1]
    assert "flex-direction:column" in _block(phone, ".d-nav-bar-box")                # the wide row stacks
    assert "flex-wrap:wrap" in _block(phone, ".d-links")                             # the narrow row wraps
    # a section on a page that already has its h1 starts at h2
    o2 = W.frame_to_html(hero_doc(), "1:1", heading_top=False, scope="s-home-custom-hero")
    assert "<h1" not in o2["html"] and '<h2 class="d-title">' in o2["html"]
    assert o2["css"].count("\n#s-home-custom-hero .d-title {") == 1
    assert all(ln.startswith(("#s-home-custom-hero", "@media", "}", "  ")) for ln in o2["css"].splitlines() if ln.strip())


def test_gradient_maths_matches_the_editor_export():
    from app.design import toweb as W
    # the same numbers hd-export.js cssGradient gives (top to bottom / a diagonal in a wide box / radial / conic)
    p = {"type": "linear", "stops": [{"pos": 0, "color": "#000000"}, {"pos": 1, "color": "#FFFFFF"}]}
    assert W.gradient(p, 200, 100) == "linear-gradient(180deg, #000000 0%, #FFFFFF 100%)"
    d = W.gradient({**p, "from": [0, 0], "to": [1, 1]}, 200, 100)
    assert d.startswith("linear-gradient(116.57deg, #000000 0%,") and d.endswith("#FFFFFF 100%)")
    assert W.gradient({**p, "type": "radial"}, 100, 100) == "radial-gradient(circle 50px at 50% 50%, #000000 0%, #FFFFFF 100%)"
    assert W.gradient({**p, "type": "angular"}, 100, 100).startswith("conic-gradient(from 90deg at 50% 50%")
    assert W._color("#FF0000", 0.5) == "rgba(255, 0, 0, 0.5)" and W._color("#00ff0080") == "rgba(0, 255, 0, 0.5)"
    x, y = W.poly_points(3, 1, False)[0]
    assert abs(x - 0.5) < 1e-9 and abs(y) < 1e-9


def test_the_code_passes_the_website_builders_own_cleaner_untouched():
    """What Web Studio's cleaner would remove = nothing: no script, no handler, no outside file, CSS scoped."""
    from app.site import build as B
    from app.site import code as CD
    from app.design import toweb as W
    for doc, node in ((hero_doc(), "1:1"), (card_doc(), "2:1"), (nav_doc(), "3:1")):
        o = W.frame_to_html(doc, node, {SHA: "shop"}, scope="s-home-custom-x", heading_top=False, img_mode="hoola")
        h, css, js, problems = B.sanitize_section("s-home-custom-x", {"html": o["html"], "css": o["css"], "js": ""})
        assert problems == [], problems
        assert js == "" and "<script" not in h and not re.search(r"\son\w+=", h) and "javascript:" not in h
        assert not re.search(r"https?://", re.sub(r'href="https://example\.com/menu"', "", h))
        sec, removed = CD.clean("home__custom_x", {"html": "", "css": o["css"], "js": ""}, "html", o["html"])
        assert removed == [] and 'id="s-home-custom-x"' in sec["html"]
        assert all(line.strip().startswith(("#s-home-custom-x", "@media", "}")) or not line.strip()
                   for line in sec["css"].split("\n") if "{" in line)
        if node == "1:1":
            assert 'data-hoola-img="shop"' in h and "/api/design/assets" not in h


def test_refusals_of_the_writer():
    from app.design import toweb as W
    with pytest.raises(W.ToWebError) as e:
        W.frame_to_html(hero_doc(), "1:2")
    assert e.value.status == 400
    with pytest.raises(W.ToWebError) as e:
        W.frame_to_html(hero_doc(), "9:99")
    assert e.value.status == 404
    bad = hero_doc()
    bad["nodes"]["1:2"]["chars"] = '<script>alert(1)</script> & "q"'
    bad["nodes"]["1:1"]["name"] = 'Hero"><img src=x onerror=alert(1)>'
    o = W.frame_to_html(bad, "1:1")
    assert "<script>" not in o["html"] and "&lt;script&gt;alert(1)&lt;/script&gt; &amp; &quot;q&quot;" in o["html"]
    assert not re.search(r"\son\w+=", o["html"]) and "<img src=x" not in o["html"]
    assert W.frame_by_name(all_doc(), "Product card") == "2:1" and W.frame_by_name(all_doc(), "1:1") == "1:1"
    with pytest.raises(W.ToWebError):
        W.frame_by_name(all_doc(), "Nope")


# ------------------------------------------------------------------------------------------- 2. into Web Studio
@pytest.fixture()
def bridge(site_env, monkeypatch, tmp_path):
    monkeypatch.setenv("API_KEY", "kd")
    monkeypatch.setenv("DESIGN_DIR", str(tmp_path / "design"))
    from app.config import get_settings
    get_settings.cache_clear()
    yield site_env
    get_settings.cache_clear()


def _client():
    from app.main import app
    return TestClient(app)


def _file(c, doc, rgba=False):
    """A design file of hers holding `doc`, with a real picture (checked by the editor's own asset store) for its fills."""
    from app.design import assets, store
    from app.design.doc import dumps_nodes
    sha = assets.save_asset(T, png(rgba=rgba))["hash"]
    nodes = json.loads(json.dumps(doc["nodes"]).replace(SHA, sha))
    f = store.create_file(T, "Sweet shop site", dumps_nodes(nodes), len(nodes))
    assert c.get(f"/api/design/files/{f['id']}/doc", headers=H).json()["doc"]["nodes"]["1:1"]["name"] == "Hero"
    return f["id"], sha


def other_tenant():
    from app import accounts
    from app.db import User, session
    with session() as s:
        u = User(email="other@example.com", name="Other Person")
        s.add(u)
        s.flush()
        uid = u.id
    return {"Authorization": f"Bearer {accounts.issue_session(uid)}"}


def test_new_site_from_a_frame(bridge):
    from app.site import build as B
    from app.site import service as S
    c = _client()
    fid, sha = _file(c, all_doc(), rgba=True)
    pv = c.post(f"/api/design/files/{fid}/to-site/preview", headers=H, json={"node": "1:1"})
    assert pv.status_code == 200 and "<h1" in pv.json()["html"] and S.sites(T) == []        # a preview touches no site
    r = c.post(f"/api/design/files/{fid}/to-site", headers=H, json={"node": "1:1", "mode": "new", "name": "Sharma Sweets",
                                                                    "brief": "mithai dukaan ki website"})
    assert r.status_code == 200, r.text
    out = r.json()
    sid = out["site"]
    assert out["url"] == f"/console/web#/site/{sid}" and out["page"] == "home" and out["mode"] == "new"
    assert out["images"] == 1 and any("see-through" in w for w in out["warnings"])
    assert any("Blend modes" in w for w in out["warnings"])
    # the existing Web Studio routes list and read it back, with the section in it
    listed = c.get("/api/sites", headers=H).json()["sites"]
    assert [x["id"] for x in listed] == [sid] and listed[0]["name"] == "Sharma Sweets"
    got = c.get(f"/api/sites/{sid}", headers=H).json()
    home = got["plan"]["pages"][0]
    assert home["slug"] == "home" and home["sections"] == ["Hero"]
    assert all(p["slug"] in ("home",) + B.LEGAL_PAGES for p in got["plan"]["pages"])
    tree = c.get(f"/api/sites/{sid}/code", headers=H).json()
    path = next(f["path"] for g in tree["files"] for f in g["files"] if f["part"] == "html")
    code = c.get(f"/api/sites/{sid}/code", headers=H, params={"path": path}).json()["code"]
    assert "Sweets made fresh every morning" in code and "<h1" in code and 'data-hoola-img="shop-photo"' in code
    # a checked version exists (Web Studio's own save job), the photo is in the SITE's own store
    assert got["version"] == 1 and got["versions"][0]["note"].startswith("From Hoola Design")
    assert got["photos"] == ["shop-photo"]
    page = (B.out_dir(T, sid, 1) / "index.html").read_text()
    assert "Sweets made fresh every morning" in page and "<picture>" in page and "/api/design/assets" not in page
    # the design's own colours / fonts / corners became the site's tokens
    look = json.loads(S._load(sid).look)
    assert look["mine"] is True and look["tokens"]["primary"] == "#F59E0B" and look["tokens"]["head"] == "Fraunces"
    # nothing published: no live address
    from app.site.hosting_models import SiteHost
    from app.db import session
    from sqlalchemy import select
    with session() as s:
        assert s.scalars(select(SiteHost).where(SiteHost.site_id == sid)).first() is None


def test_section_added_to_a_built_site_through_the_studio_path(bridge):
    from app.site import service as S
    from tests.test_life import conv_ctx
    c = _client()
    v = S.new(T, "mithai dukaan ki website", conv_ctx().conversation_id, name="Sharma Sweets",
              answers={"phone": "9876543210", "address": "Main Road, Akot"})
    S.approve_plan(T, v["id"], pages=["contact"])
    S.choose_look(T, v["id"], 0)
    sid = v["id"]
    ver = S.get(T, sid)["version"]
    fid, _sha = _file(c, all_doc())
    r = c.post(f"/api/design/files/{fid}/to-site", headers=H, json={"node": "2:1", "mode": "section", "site": sid, "page": "home"})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["section"] == "home__custom_product_card" and out["url"] == f"/console/web#/site/{sid}"
    g = S.get(T, sid)
    assert g["version"] == ver + 1 and g["versions"][0]["note"].startswith("From Hoola Design")
    assert g["plan"]["pages"][0]["sections"][-1] == "Product card"
    sec = S._sections(S._load(sid))["home__custom_product_card"]
    assert 'id="s-home-custom-product-card"' in sec["html"] and "Kaju katli" in sec["html"] and "<h1" not in sec["html"]
    assert "#s-home-custom-product-card .d-name" in sec["css"]
    # sent again: a second section with its own key, the first one untouched
    r2 = c.post(f"/api/design/files/{fid}/to-site", headers=H, json={"node": "2:1", "mode": "section", "site": sid, "page": "home"})
    assert r2.json()["section"] == "home__custom_product_card_2"
    assert S.get(T, sid)["version"] == ver + 2
    # refusals in plain words: a page she does not have, a legal page, a site not built yet
    assert c.post(f"/api/design/files/{fid}/to-site", headers=H, json={"node": "2:1", "mode": "section", "site": sid,
                                                                       "page": "nope"}).status_code == 404
    assert c.post(f"/api/design/files/{fid}/to-site", headers=H, json={"node": "2:1", "mode": "section", "site": sid,
                                                                       "page": "privacy"}).status_code == 409
    planned = S.new(T, "gym ki website", name="Fit Club")["id"]
    bad = c.post(f"/api/design/files/{fid}/to-site", headers=H, json={"node": "2:1", "mode": "section", "site": planned})
    assert bad.status_code == 409 and "not built yet" in bad.json()["detail"]
    # a text layer is not a frame
    assert c.post(f"/api/design/files/{fid}/to-site", headers=H, json={"node": "2:4", "mode": "new"}).status_code == 400


def test_other_tenant_and_signed_out_are_refused(bridge):
    from app.site import service as S
    c = _client()
    fid, _ = _file(c, all_doc())
    other = other_tenant()
    assert c.post(f"/api/design/files/{fid}/to-site", headers=other, json={"node": "1:1", "mode": "new"}).status_code == 404
    assert c.post(f"/api/design/files/{fid}/to-site/preview", headers=other, json={"node": "1:1"}).status_code == 404
    assert c.post(f"/api/design/files/{fid}/to-site", json={"node": "1:1", "mode": "new"}).status_code == 401
    # a view-only guest has only the share token: no route of this bridge answers it
    tok = c.post(f"/api/design/files/{fid}/share", headers=H, json={"role": "view"}).json()["token"]
    assert c.post(f"/api/design/shared/{tok}/to-site", json={"node": "1:1"}).status_code in (404, 405)
    # her own site cannot be reached from another person's file either: the other tenant's file + her site id
    v = S.new(T, "mithai dukaan ki website", name="Sharma Sweets")
    fo = c.post("/api/design/files", headers=other, json={"name": "Mine"}).json()
    r = c.post(f"/api/design/files/{fo['id']}/to-site", headers=other, json={"node": "0:1", "mode": "section", "site": v["id"]})
    assert r.status_code in (400, 404)
    assert S.sites(T)[0]["id"] == v["id"] and len(S.sites(T)) == 1
    # a trashed file is refused
    c.delete(f"/api/design/files/{fid}", headers=H)
    assert c.post(f"/api/design/files/{fid}/to-site", headers=H, json={"node": "1:1", "mode": "new"}).status_code in (404, 409)


def test_agent_tool_to_site(bridge):
    import asyncio

    from app.agent import design_tools as DT
    from app.agent.tools import Ctx
    c = _client()
    fid, _ = _file(c, all_doc())
    ctx = Ctx(tenant_id=T, conversation_id="c1")
    out = asyncio.run(DT.hoola_design(ctx, action="to_site", file=fid, node="Product card"))
    assert out["status"] == "sent" and out["url"].endswith(f"/console/web#/site/{out['site']}") and "Nothing is published" in out["note"]
    from app.agent.tools import ToolError
    with pytest.raises(ToolError):
        asyncio.run(DT.hoola_design(ctx, action="to_site", file=fid, node="No such frame"))
    assert "to_site" in DT.DESIGN_TOOLS[0]["input_schema"]["properties"]["action"]["enum"]


# ------------------------------------------------------------------------------------------- 3. a real browser
def test_renders_without_sideways_scroll_at_desktop_and_phone(tmp_path):
    """The three frames on one page, opened in real Chromium at 1280 and 390 px: nothing wider than the screen."""
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    probe = subprocess.run([node, "-e", "require('playwright')"], capture_output=True, text=True)
    if probe.returncode:
        pytest.skip("playwright is not available")
    import base64

    from app.design import toweb as W
    uri = "data:image/png;base64," + base64.b64encode(png()).decode()
    parts, css = [], ""
    for doc, n in ((nav_doc(), "3:1"), (hero_doc(), "1:1"), (card_doc(), "2:1")):
        o = W.frame_to_html(doc, n, {SHA: uri})
        parts.append(o["html"])
        css += o["css"]
    page = tmp_path / "page.html"
    page.write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
                    'content="width=device-width,initial-scale=1"><title>t</title><style>body{margin:0;font-family:system-ui}'
                    "img,svg,video,picture{display:block;max-width:100%;height:auto}" + css + "</style></head><body>"
                    + "".join(parts) + "</body></html>")
    script = tmp_path / "walk.cjs"
    script.write_text("""
const {chromium} = require('playwright');
(async () => {
  const b = await chromium.launch(); const out = {};
  for (const w of [1280, 390]) {
    const p = await b.newPage({viewport: {width: w, height: 900}});
    await p.goto('file://' + process.argv[2]);
    out[w] = await p.evaluate(() => {
      const cw = document.documentElement.clientWidth, r = s => document.querySelector(s).getBoundingClientRect();
      return {sw: document.documentElement.scrollWidth, cw,
              title: r('.d-title').width, card: r('.d-product-card-box').width, btn: getComputedStyle(document.querySelector('.d-primary-button')).backgroundColor,
              navDir: getComputedStyle(document.querySelector('.d-nav-bar-box')).flexDirection, star: getComputedStyle(document.querySelector('.d-sparkle')).display};
    });
    await p.screenshot({path: process.argv[3] + '/toweb-' + w + '.png', fullPage: true});
  }
  console.log(JSON.stringify(out)); await b.close();
})();
""")
    shots = os.environ.get("HD_TOWEB_SHOTS") or str(tmp_path)
    run = subprocess.run([node, str(script), str(page), shots], capture_output=True, text=True, timeout=120,
                         cwd=str(tmp_path))
    if run.returncode and "Executable doesn't exist" in run.stderr:
        pytest.skip("no Chromium for playwright here")
    assert run.returncode == 0, run.stderr[-2000:]
    got = json.loads(run.stdout.strip().splitlines()[-1])
    for w in ("1280", "390"):
        assert got[w]["sw"] <= got[w]["cw"], got
        assert got[w]["btn"] == "rgb(245, 158, 11)"                       # the button keeps its own colour
    assert got["1280"]["navDir"] == "row" and got["390"]["navDir"] == "column"
    assert got["1280"]["star"] == "block" and got["390"]["star"] == "none"
    assert got["390"]["card"] <= 360 and got["390"]["title"] <= 390


# ------------------------------------------------------------------------------------------- helpers
def _block(css, sel):
    """The declarations of the first block whose selector is `sel` (or ends with ' ' + sel), on one line."""
    for m in re.finditer(r"([^{}\n]+)\{([^{}]*)\}", css):
        s = m.group(1).strip()
        if s == sel or s.endswith(" " + sel):
            return re.sub(r"\s*\n\s*", "", m.group(2))
    return ""


# ------------------------------------------------------------------------------------------- 4. the editor's dialog
def test_the_client_file_is_a_plain_strict_script_loaded_in_order():
    from pathlib import Path
    design = Path(__file__).resolve().parent.parent / "app" / "static" / "console" / "design"
    text = (design / "hd-bridge-web.js").read_text(encoding="utf-8")
    assert "'use strict';" in text and text.rstrip().endswith("})();") and text.isascii()
    assert "eval(" not in text and "new Function" not in text and "innerHTML" not in text and "insertAdjacentHTML" not in text
    assert "ui.registerMenu('context'" in text and "ui.command({id: 'sendToWeb'" in text and "ui.designSection(" in text
    html = (design / "design.html").read_text(encoding="utf-8")
    assert html.index("hd-ai.js") < html.index("hd-bridge-web.js") < html.index("hd-app.js")
    stamp = re.search(r"hd-ai\.js\?v=([0-9.]+)", html).group(1)
    assert f"hd-bridge-web.js?v={stamp}" in html and f"design-bridge-web.css?v={stamp}" in html
    css = (design / "design-bridge-web.css").read_text(encoding="utf-8")
    assert "text-transform" not in css and not re.search(r"font-size:\s*(?:[0-9]|1[01])(?:\.\d+)?px", css)


def test_the_dialog_in_a_real_browser():
    from pathlib import Path
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    js = Path(__file__).resolve().parent / "web" / "design_bridge_web_test.js"
    env = os.environ.copy()
    sandbox = "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"
    if env.get("HOOLA_CHROMIUM"):
        env["CHROMIUM_EXECUTABLE"] = env["HOOLA_CHROMIUM"]
    elif Path(sandbox).exists():
        env.setdefault("CHROMIUM_EXECUTABLE", sandbox)
    run = subprocess.run([node, str(js)], capture_output=True, text=True, timeout=600, env=env)
    if run.returncode == 77 or "Cannot find module 'playwright'" in run.stderr:
        pytest.skip("no browser here")
    assert run.returncode == 0, (run.stdout[-1500:] + "\n" + run.stderr[-4000:])
    assert "design_bridge_web_test: ok" in run.stdout
