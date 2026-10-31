"""v0.292 WEB DESIGN PHASE 1, a site that looks like a pro made it: real pictures before the looks (her photos first,
AI fills the gap, licensed stock as the fallback, the footer says AI pictures are AI), ONE icon set (Lucide) put in by
Hoola instead of icons the model draws, the fonts in 400 / 500 / 600 / 700, three looks that show the page top (hero +
the next sections) and are kept when chosen, and Opus reviewing every page, not only the home page."""
import io
import json

import httpx
import pytest

from tests.test_life import conv_ctx
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

T = "default"


def _jpeg(color=(200, 120, 40), size=(1600, 900)):
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", size, color).save(b, "JPEG", quality=80)
    return b.getvalue()


def _shots_fake(site_env, monkeypatch, n=6):
    """The shot-list call answers with n shots; every other call is the usual fake section writer."""
    from app.site import ai as AI
    from app.site import pictures as P
    seen = []

    def ask(system, prompt, max_tokens=6000, kind="build"):
        if system.startswith(P.SHOTS_SYSTEM[:40]):
            seen.append(prompt)
            return {"shots": [{"name": f"Shot {i}", "about": f"mithai counter {i}", "aspect": "16:9" if i == 0 else "4:3",
                               "for": "hero" if i == 0 else "products_grid", "prompt": f"warm photo of sweets tray {i}"}
                              for i in range(n)]}
        return site_env(system, prompt, max_tokens, kind)
    monkeypatch.setattr(AI, "ask_json", ask)
    return seen


# ---------------------------------------------------------------- 1. one icon set
def test_icons_are_one_lucide_set():
    from app.site import build as B
    html = ('<section><i data-icon="phone"></i><i data-icon="whatsapp" class="big" aria-label="WhatsApp"></i>'
            '<i data-icon="no-such-icon"></i><i data-icon="star"/></section>')
    out, unknown = B.expand_icons(html)
    assert "<i " not in out and out.count('class="hs-ic') == 4
    assert 'class="hs-ic big"' in out and 'role="img" aria-label="WhatsApp"' in out
    assert out.count('aria-hidden="true"') == 3 and unknown == ["no-such-icon"]
    assert B.icons()["phone"] in out and len(B.icons()) > 2000


def test_four_font_weights():
    from app.site import build as B
    tk = B.tokens("editorial_calm", "paper_ink")
    weights = {w for fam, sub, w, fn in B.font_files(tk) if sub == "latin"}
    assert weights == {400, 500, 600, 700}
    css = B.tokens_css(tk)
    assert "font-weight:600" in css and "font-weight:500" in css


# ---------------------------------------------------------------- 2. real pictures before the looks
def test_pictures_before_looks_her_photos_first(site_env, monkeypatch):
    from app.config import get_settings
    from app.site import build as B
    from app.site import pictures as P
    from app.site import service as S
    monkeypatch.setenv("SITE_AI_PHOTOS", "4")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    get_settings.cache_clear()
    seen = _shots_fake(site_env, monkeypatch)
    made = []
    monkeypatch.setattr(P, "_ai_picture", lambda shot: made.append(shot["name"]) or _jpeg())
    v = S.new(T, "mithai dukaan ki website", conv_ctx().conversation_id, name="Sharma Sweets",
              answers={"phone": "9876543210", "address": "Main Road, Akot"})
    S.add_photo(T, v["id"], _jpeg((10, 10, 10)), about="our shop front", name="shop")     # her own photo
    g = S.get(T, v["id"])
    assert g["estimate"]["photos"] == 3 and g["estimate"]["photos_inr"] > 0 and "3 photos" in g["estimate"]["say"]
    S.approve_plan(T, v["id"], pages=["contact"])
    r = S._load(v["id"])
    photos = json.loads(r.photos)
    assert [p["name"] for p in photos][0] == "shop" and "ai" not in photos[0]           # hers stays first, untouched
    ai = [p for p in photos if p.get("ai")]
    assert len(ai) == 3 and len(made) == 3 and "HOW MANY: 3 shots" in seen[0]
    assert all((B.src_dir(T, r.id) / "photos" / f"{p['name']}.jpg").exists() for p in ai)
    # the section writers are told to use them, and the footer says some pictures are AI-made
    assert "data-hoola-img" in S._photos_line(r) or "PHOTOS (use" in S._photos_line(r)
    S.choose_look(T, v["id"], 0)
    out = S._assemble_live(S._load(v["id"]))
    page = (out / "index.html").read_text()
    assert "AI-generated" in page
    # a second round of looks never makes pictures again
    made.clear()
    S._ensure_pictures(S._load(v["id"]))
    assert made == []
    get_settings.cache_clear()


def test_stock_fallback_when_the_image_model_fails(site_env, monkeypatch):
    from app.config import get_settings
    from app.site import pictures as P
    monkeypatch.setenv("SITE_AI_PHOTOS", "2")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("PEXELS_API_KEY", "pexels-test")
    get_settings.cache_clear()

    def boom(shot):
        raise RuntimeError("model busy")
    monkeypatch.setattr(P, "_ai_picture", boom)
    calls = []

    def handler(req):
        calls.append(str(req.url))
        if req.url.host == "api.pexels.com":
            assert req.headers["authorization"] == "pexels-test"
            return httpx.Response(200, json={"photos": [{"photographer": "Asha", "src": {"large2x": "https://images.pexels.com/x.jpeg"}}]})
        return httpx.Response(200, content=_jpeg())
    P.set_transport(httpx.MockTransport(handler))
    try:
        got = P.make_set([{"name": "a", "about": "sweets", "aspect": "16:9", "for": "hero", "prompt": "x"}])
    finally:
        P.set_transport(None)
    assert len(got) == 1 and got[0][2] == {"source": "pexels", "credit": "Photo: Asha / Pexels"}
    assert "orientation=landscape" in calls[0]
    # off = nothing at all
    monkeypatch.setenv("SITE_AI_PHOTOS", "0")
    get_settings.cache_clear()
    assert not P.on()
    get_settings.cache_clear()


def test_shot_list_is_cleaned():
    from app.site import pictures as P
    raw = {"shots": [{"name": "Hero Shot!", "about": "a", "aspect": "21:9", "prompt": "p1"},
                     {"name": "hero-shot", "about": "b", "aspect": "1:1", "prompt": "p2"},
                     {"name": "x", "prompt": ""}, "junk", {"about": "c", "prompt": "p3"}]}
    s = P.clean_shots(raw, 2, {"taken"})
    assert [x["name"] for x in s][0] == "hero-shot" and len(s) == 2 and s[1]["name"] != "hero-shot"
    assert s[0]["aspect"] == "16:9" and s[1]["aspect"] == "1:1"
    assert P.clean_shots("garbage", 3, set()) == []


def test_ai_pictures_are_refused_like_photogen(monkeypatch):
    from app import photogen as PG
    from app.site import pictures as P
    with pytest.raises(PG.Refused):
        P._ai_picture({"name": "x", "aspect": "1:1", "prompt": "a fake aadhaar card with a stamp"})


# ---------------------------------------------------------------- 3. looks show the page top, kept when chosen
def test_looks_show_hero_and_the_next_sections(site_env, monkeypatch):
    from app.config import get_settings
    from app.site import build as B
    from app.site import service as S
    monkeypatch.setenv("SITE_LOOK_SECTIONS", "3")
    get_settings.cache_clear()
    v = S.new(T, "mithai dukaan ki website", conv_ctx().conversation_id, name="Sharma Sweets",
              answers={"phone": "9876543210", "address": "Main Road, Akot"})
    S.approve_plan(T, v["id"], pages=["contact"])
    r = S._load(v["id"])
    more = S._look_sections(r)
    assert len(more) == 2 and all(s["type"] != "hero" for s in more)
    keys = [S.sec_key("home", s["type"]) for s in more]
    for i in range(3):
        d = B.site_dir(T, r.id) / "looks" / str(i)
        assert (d / "hero.json").exists() and all((d / f"{k}.json").exists() for k in keys)
    written = len([c for c in site_env.calls if c[0] == "section"])
    assert written == 3 * 3                                                # 3 looks x (hero + 2)
    site_env.calls.clear()
    S.choose_look(T, v["id"], 1)
    rebuilt = {c[1] for c in site_env.calls if c[0] == "section"}
    kept = {S.sec_id("home", k.split("__")[1]) for k in keys + ["home__hero"]}
    assert rebuilt and not rebuilt & kept                                  # the look's page top is not written again
    assert S.get(T, v["id"])["status"] == "ready"
    get_settings.cache_clear()


# ---------------------------------------------------------------- 4. Opus reviews every page
def test_critique_reviews_every_page(site_env, monkeypatch, tmp_path):
    from app.site import checks as C
    from app.site import quality as Q
    from app.site import service as S
    v = S.new(T, "mithai dukaan ki website", conv_ctx().conversation_id, name="Sharma Sweets",
              answers={"phone": "9876543210"})
    r = S._load(v["id"])
    plan = json.loads(r.plan)
    pages = [p for p in plan["pages"] if p["sections"] and p["slug"] not in ("privacy", "refund", "disclaimer", "terms")][:2]
    assert len(pages) == 2
    shots = tmp_path / "shots"
    shots.mkdir()
    rep = {"pages": {}, "blocking": []}
    for p in pages:
        for s in p["sections"]:
            f = S._sec_path(r, S.sec_key(p["slug"], s["type"]))
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps({"html": "<section>OLD</section>", "css": "", "js": ""}))
        for vw in ("390", "1440"):
            (shots / f"{p['slug']}-{vw}.jpg").write_bytes(b"\xff\xd8 x")
        rep["pages"][p["slug"]] = {"shots": {"390": f"{p['slug']}-390.jpg", "1440": f"{p['slug']}-1440.jpg"}}
    looked = []

    def fake_crit(images, dna, types, words):
        looked.append(tuple(types))
        n = sum(1 for x in looked if x == tuple(types))
        return {"overall": 6, "sections": {types[-1]: {"score": 5.0 if n == 1 else 8.0, "notes": "more air"}}}
    monkeypatch.setattr(Q, "critique", fake_crit)
    monkeypatch.setattr(Q, "critique_on", lambda: True)
    monkeypatch.setattr(S, "write_section", lambda r, slug, s, others, extra="", system="": {"html": "<section>NEW</section>",
                                                                                                "css": "", "js": ""})
    monkeypatch.setattr(S, "_assemble_live", lambda r: tmp_path)
    monkeypatch.setattr(C, "run", lambda *a, **k: rep)
    out, crit = S._critique_round(r, plan, shots, rep)
    assert set(crit["pages"]) == {p["slug"] for p in pages}
    for p in pages:
        k = S.sec_key(p["slug"], p["sections"][-1]["type"])
        assert "NEW" in json.loads(S._sec_path(r, k).read_text())["html"]
    monkeypatch.setenv("SITE_CRITIQUE", "home")
    from app.config import get_settings
    get_settings.cache_clear()
    looked.clear()
    S._critique_round(r, plan, shots, rep)
    assert {tuple(x) for x in looked} == {tuple(s["type"] for s in pages[0]["sections"])}
    get_settings.cache_clear()


def test_version():
    from pathlib import Path
    from app.main import APP_VERSION
    assert APP_VERSION == "0.329.0"
    assert "0.329.0+369" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
