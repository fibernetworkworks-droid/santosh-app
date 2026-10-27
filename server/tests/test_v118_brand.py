"""v0.118 Brand Sahayak (brand designer): brand kit from her logo -> posters in her colours -> every platform size ->
checks (contrast, fit, blanks, claims, Emblems Act) -> FINAL artwork only on her tap (exact version) -> clean finals,
learning, festival reminders."""
import asyncio
import io
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import Event, session
from tests.test_life import conv_ctx

T = "default"


def _B():
    from app.brand import service as B
    return B


def _events(kind):
    with session() as s:
        return [e.payload for e in s.scalars(select(Event).where(Event.kind == kind).order_by(Event.id)).all()]


def logo_png() -> bytes:
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((10, 10, 390, 390), fill=(13, 71, 161, 255))
    d.rectangle((150, 80, 250, 320), fill=(255, 193, 7, 255))
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


def photo_jpg(w=1600, h=1200) -> bytes:
    from PIL import Image
    im = Image.new("RGB", (w, h), (120, 60, 30))
    b = io.BytesIO()
    im.save(b, "JPEG", exif=b"")
    return b.getvalue()


@pytest.fixture
def setup(env, monkeypatch, tmp_path):
    B = _B()
    monkeypatch.setenv("BRAND_DIR", str(tmp_path / "brand"))
    monkeypatch.setattr(B, "today", lambda tenant: date(2026, 10, 22))
    words = {"headline": "100 Mbps Fiber sirf ₹499", "sub": "Free installation, Akot aur Akola", "offer": "₹499/mo",
             "cta": "Abhi call karein", "date": "15 Nov tak", "layout": "hero", "title": "Fiber offer", "notes": "ok"}
    calls = []

    def fake(system, prompt, max_tokens=1500):
        calls.append(prompt)
        if "CURRENT POSTER" in prompt:
            return {"headline": "300 Mbps sirf ₹799", "offer": "₹799/mo"}
        return dict(words)
    monkeypatch.setattr(B, "_ai_json", fake)
    B.save_kit(T, name="FNW Fiber", tagline="Bharat Fiber partner", state="Maharashtra")
    return B, words, calls


def test_rules_colours_sizes_festivals_emblems():
    from app.brand import rules as R
    assert R.contrast("#000000", "#FFFFFF") == 21.0 and R.readable("#FFFFFF", "#111111")
    assert not R.readable("#FFFFFF", "#FFEB3B")
    pal = R.palette_from_image(logo_png())
    assert any(R._dist(c, "#0D47A1") < 40 for c in pal) and any(R._dist(c, "#FFC107") < 40 for c in pal)
    k = R.kit_colors(pal)
    assert set(k) == {"primary", "secondary", "accent", "dark", "light"} and R.luminance(k["light"]) > 0.8
    assert R.sizes_of("social") == ["insta_post", "story", "fb_post", "insta_square"]
    assert R.sizes_of(["whatsapp", "banner", "A4", "xyz"]) == ["insta_square", "story", "flex_6x3", "a4"]
    assert R.sizes_of(["status", "flyer"]) == ["story", "a4"]
    assert R.sizes_of(None, "festival") == R.SETS["festival"]
    assert R.festival_theme("Diwali (Deepavali)")["motif"] == "diya"
    assert R.festival_theme("Independence Day")["note"].startswith("Rashtriya Dhwaj")
    assert R.protected("Tiranga ke saath Gandhi ji ki photo")
    assert R.protected("Ashoka Chakra wala logo") and not R.protected("Diwali sale 20% off")
    assert R.parse_color("neela") == "#1565C0" and R.parse_color("#abc") == "#AABBCC" and R.parse_color("blah") == ""
    assert R.phone_ok("89565 55723") and not R.phone_ok("12345")


def test_kit_from_logo_and_her_colours(setup):
    B, _w, _c = setup
    r = B.set_logo(T, logo_png(), name="logo.png")
    assert r["palette"] and r["kit"]["logo"] and "rang mile" in r["say"]
    assert B.R._dist(r["kit"]["colors"]["primary"], "#0D47A1") < 60 or B.R._dist(r["kit"]["colors"]["primary"], "#FFC107") < 60
    k = B.save_kit(T, colors={"primary": "laal"}, contact={"phone": "89565 55723", "website": "ainewtika.com"},
                   rule="Logo hamesha upar left")
    assert k["colors"]["primary"] == "#D32F2F" and k["colors_set"] and k["rules"] == ["Logo hamesha upar left"]
    r2 = B.set_logo(T, logo_png())                      # her chosen colours stay when the logo changes
    assert r2["kit"]["colors"]["primary"] == "#D32F2F"
    with pytest.raises(B.BrandError):
        B.save_kit(T, colors={"accent": "sunset vibes"})
    with pytest.raises(B.BrandError):
        B.set_logo(T, b"not an image at all", name="logo.png")
    assert B.logo_file(T)[0].exists()


def test_make_proofs_checks_and_final_only_on_her_tap(setup):
    B, words, calls = setup
    B.set_logo(T, logo_png())
    out = B.make(T, "Diwali offer: 100 Mbps fiber Rs 499 per month, 15 Nov tak, free installation", sizes=["social", "a4"])
    v = out["design"]
    assert v["number"] == "B-0001" and v["status"] == "draft" and v["kind"] == "offer"
    assert v["sizes"] == ["insta_post", "story", "fb_post", "insta_square", "a4"]
    folder = Path(B._dir(T, v["id"]))
    assert all((folder / n.rsplit("/", 1)[1]).exists() for n in v["proofs"].values())
    from PIL import Image
    im = Image.open(folder / v["proofs"]["story"].rsplit("/", 1)[1])
    assert im.size == (1080, 1920)
    texts = [c["text"] for c in v["checks"]]
    assert any("Contact" in t for t in texts)                  # no phone / address in the kit yet
    assert any("Print file RGB" in t for t in texts)
    assert _events("brand_design")[-1]["design"]["number"] == "B-0001"
    # proof page has the PROOF mark, the final page doesn't
    with session() as s:
        d = s.get(B.BrandDesign, v["id"])
        kitv, logo, _h = B._kit_for_page(T)
        assert "PROOF" in B._page_for(T, d, "insta_post", True, kitv, logo)
        assert "PROOF" not in B._page_for(T, d, "insta_post", False, kitv, logo)
    # the tool can only send the card
    from app.agent.tools import HANDLERS, Ctx
    ctx = conv_ctx()
    r = asyncio.run(HANDLERS["brand"](Ctx(T, ctx.conversation_id), action="approve", design="B-0001"))
    assert r["status"] == "needs_tap" and "do not say it is approved" in r["note"]
    card = _events("brand_approval")[-1]["design"]
    assert card["approve_hash"] and B.get(T, "B-0001")["status"] == "waiting"
    with pytest.raises(B.BrandError):
        B.decide(T, "B-0001", True, "wrong-hash")
    res = B.decide(T, "B-0001", True, card["approve_hash"])
    fv = res["design"]
    assert fv["status"] == "approved" and set(fv["finals"]) == set(v["sizes"])
    assert "pdf" in fv["finals"]["a4"] and "png" in fv["finals"]["a4"] and "png" in fv["finals"]["insta_post"]
    big = Image.open(folder / fv["finals"]["a4"]["png"].rsplit("/", 1)[1])
    assert big.size[0] >= 2400                                # 300 dpi A4 with bleed
    assert (folder / "final_a4.pdf").read_bytes()[:4] == b"%PDF"
    assert fv["finals"]["insta_post"].get("png_file_id")       # also in her files for sharing
    assert B.kit(T)["learned"]["layouts"]["offer"]["hero"] == 1
    # a change after approval = new version, asks again
    r = B.revise(T, "B-0001", "300 Mbps wala plan dikhao, 799 ka")
    assert r["design"]["version"] == 2 and r["design"]["status"] == "draft"
    assert any("799" in t["text"] for t in r["design"]["checks"])   # 799 was never in her brief -> pointed out


def test_blocks_blanks_emblems_and_her_edits(setup):
    B, words, _c = setup
    B.save_kit(T, contact={"phone": "89565 55723"})
    words.update({"headline": "Grand opening [date]", "sub": "Naya showroom", "offer": "", "layout": "minimal"})
    v = B.make(T, "Naya showroom khul raha hai", kind="announcement", sizes=["whatsapp"])["design"]
    assert v["blocks"] and "Bharna baaki" in v["blocks"][0]
    with pytest.raises(B.BrandError):
        B.request_approval(T, v["number"])
    with pytest.raises(B.BrandError):
        B.request_approval(T, v["number"], force=True)          # blanks can never go final
    v2 = B.edit(T, v["number"], {"headline": "Grand opening 1 Nov"})["design"]
    assert not v2["blocks"] and v2["version"] == 2
    assert B.request_approval(T, v["number"])["design"]["status"] == "waiting"
    r = B.decide(T, v["number"], False, B.get(T, v["number"])["approve_hash"], "rang phika laga")
    assert r["design"]["status"] == "rejected" and B.kit(T)["learned"]["rejected"][0]["why"] == "rang phika laga"
    with pytest.raises(B.BrandError):
        B.make(T, "Independence Day poster with tiranga and Ashoka Chakra")
    with pytest.raises(B.BrandError):
        B.revise(T, v["number"], "Gandhi ji ki photo laga do")
    with pytest.raises(B.BrandError):
        B.make(T, "Teen patti real money game ka poster")
    rz = B.resize(T, v["number"], ["linkedin", "yt_thumb"])["design"]
    assert rz["sizes"] == ["insta_square", "story", "linkedin", "yt_thumb"] and rz["status"] == "draft"


def test_festival_photo_template_nudge(setup, monkeypatch):
    B, words, calls = setup
    monkeypatch.setattr(B, "_ai_json", lambda *a, **k: {})      # no model: her words + the festival's own greeting
    v = B.make(T, "Diwali ki badhai sab graahakon ko", kind="festival")["design"]
    assert v["kind"] == "festival" and v["festival"]["date"] == "2026-11-08"
    assert v["content"]["greeting"] == "शुभ दीपावली" and v["layout"] == "festival"
    ups = B.upcoming(T, 45)
    assert any(f["theme"] == "diwali" and f["made"] for f in ups)
    # a nudge only for festivals without a poster, once
    monkeypatch.setattr(B, "upcoming", lambda tenant, days=45, all_days=False: [
        {"date": "2026-10-29", "name": "Karwa Chauth", "theme": "karwa", "motif": "moon", "colors": [], "days_left": 7,
         "greet": {}, "made": False}])
    from datetime import datetime as _dt

    class _Now(_dt):
        @classmethod
        def now(cls, tz=None):
            return _dt(2026, 10, 22, 11, 0, tzinfo=tz)
    monkeypatch.setattr(B, "datetime", _Now)
    due = B.due_nudges()
    assert len(due) == 1 and due[0][1]["theme"] == "karwa" and B.due_nudges() == []
    B.send_nudge(*due[0])
    assert "Karwa Chauth" in _events("brand_idea")[-1]["say"]
    # her product photo -> photo layout, EXIF dropped, small photo for print pointed out
    from app import chatfiles
    fid = chatfiles.store(T, "saree.jpg", photo_jpg(600, 450), "image/jpeg")["file_id"]
    p = B.make(T, "Nayi Banarasi saree collection", kind="product", photo_file_id=fid, sizes=["insta_post", "a3"],
               words={"headline": "Nayi Banarasi saree", "sub": "Diwali collection"})["design"]
    assert p["layout"] == "photo"
    assert any("Photo 600x450" in c["text"] for c in p["checks"])
    t = B.copy_design(T, p["number"], template=True)
    assert t["design"]["template"] and B.designs(T, "template")[0]["number"] == p["number"]
    c = B.copy_design(T, p["number"])["design"]
    assert c["number"] != p["number"] and c["layout"] == "photo"
    assert B.delete(T, c["number"])["deleted"] == c["number"]


def test_tools_roles_api(setup):
    B, words, _c = setup
    from app.agent import tools as tl
    from app.agent.tools import HANDLERS, Ctx, ToolError
    from app.employee import roles
    from app import voice
    ctx = conv_ctx()

    def run(tool, **a):
        return asyncio.run(HANDLERS[tool](Ctx(T, ctx.conversation_id), **a))
    assert any(t["name"] == "brand" for t in tl.TOOLS)
    r = run("brand", action="make", brief="Diwali offer 499", sizes=["whatsapp"])
    assert r["design"]["number"] and "proofs" not in r["design"]
    assert run("brand_dekho", what="design", design=r["design"]["number"])["status"] == "draft"
    assert run("brand_dekho", what="sizes")["sizes"]["story"].startswith("Story")
    assert run("brand", action="kit", name="FNW", colors={"accent": "#FF9800"})["kit"]["colors"]["accent"] == "#FF9800"
    with pytest.raises(ToolError):
        asyncio.run(HANDLERS["brand"](Ctx(T, ctx.conversation_id, actor="staff:x"), action="kit", name="X"))
    with pytest.raises(ToolError):
        run("brand", action="revise", design="B-9999", instruction="x")
    assert roles.duty_of("brand") == "brand_design" and roles.kind_of("brand_dekho") == "read"
    assert roles.PRESETS["brand"]["role"] == "brand_designer"
    assert "brand" in voice.VOICE_TOOL_NAMES
    from app import main
    with TestClient(main.app) as c:
        assert "brand" in c.get("/healthz").json()["features"]
        lg = c.post("/api/brand/logo", files={"file": ("logo.png", logo_png(), "image/png")}).json()
        assert lg["palette"]
        assert c.get("/api/brand/logo").status_code == 200
        k = c.put("/api/brand/kit", json={"contact": {"phone": "89565 55723"}}).json()
        assert k["contact"]["phone"] == "89565 55723"
        assert c.put("/api/brand/kit", json={"font": "comic"}).status_code == 400
        d = c.post("/api/brand/designs", json={"brief": "Diwali offer 499", "sizes": ["story"]}).json()["design"]
        img = c.get(d["proofs"]["story"])
        assert img.status_code == 200 and img.headers["content-type"] == "image/jpeg"
        assert c.get(f"/api/brand/files/{d['id']}/..%2Fsecret").status_code in (400, 404)
        assert c.get(f"/api/brand/files/{d['id']}/final_story.png").status_code == 400   # nothing final yet
        a = c.post(f"/api/brand/designs/{d['id']}/approve", json={}).json()
        h = a["design"]["approve_hash"]
        assert c.post(f"/api/brand/designs/{d['id']}/decide", json={"yes": True, "hash": "x"}).status_code == 400
        f = c.post(f"/api/brand/designs/{d['id']}/decide", json={"yes": True, "hash": h}).json()["design"]
        assert f["status"] == "approved"
        png = c.get(f["finals"]["story"]["png"])
        assert png.status_code == 200 and png.content[:4] == b"\x89PNG"
        allv = c.get("/api/brand").json()
        assert allv["kit"]["name"] == "FNW" and allv["designs"] and "story" in allv["sizes"]
        assert c.get("/api/brand/festivals?days=45").json()["festivals"]
        assert c.post(f"/api/brand/designs/{d['id']}/nope", json={}).status_code == 400
