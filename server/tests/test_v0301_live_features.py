"""v0.301 WEB DESIGN PHASE 3, live features: a booking form with her REAL free slots (the visitor asks, she confirms),
a map / YouTube video that load only on a tap (frame-src allows only those two), Pay-by-UPI buttons to HER UPI ID
with a QR code (WhatsApp order without one), a second language under /<lang>/ with a switch (Opus translates, a
broken translation is dropped, edits reach it), and the launch bug where a live site lost every photo."""
import json

import pytest
from fastapi.testclient import TestClient

from tests.test_life import conv_ctx
from tests.test_v121_site import site_env  # noqa: F401  (fixture)
from tests.test_v122_hosting import host_env  # noqa: F401  (fixture)

T = "default"


def _icon(n):
    return f'<svg class="hs-ic" data-n="{n}"></svg>'


# ---------------------------------------------------------------- 1. placeholders -> the real things
def test_placeholders_become_real_things():
    from app.site import build as B
    from app.site import live as LV
    site = {"language": "hinglish", "facts": {"name": "Sharma Sweets", "address": "Main Road, Akot", "phone": "9876543210",
                                              "upi": "sharmasweets@okicici"}}
    html = ('<section><div data-hoola-map></div><div data-hoola-video="https://youtu.be/dQw4w9WgXcQ" data-title="Hamari rasoi"></div>'
            '<div data-hoola-video="https://evil.example/x"></div><div data-hoola-booking></div>'
            '<a class="btn" data-hoola-pay="499" data-for="Kaju katli 1 kg">Pay ₹499</a></section>')
    out, problems = LV.expand(html, site, "https://api.example/api/site-forms/site_1", _icon)
    assert 'data-hs-map="https://www.google.com/maps?q=Sharma%20Sweets%20Main%20Road%2C%20Akot' in out and "<iframe" not in out
    assert "Map dekhiye" in out and 'href="https://maps.google.com/?q=' in out
    assert 'data-hs-yt="dQw4w9WgXcQ"' in out and "Hamari rasoi" in out
    assert "[YouTube video link]" in out and "video: not a YouTube link" in problems
    assert 'data-hoola-book data-endpoint="https://api.example/api/site-forms/site_1"' in out and 'name="slot"' not in out
    assert 'href="upi://pay?pa=sharmasweets%40okicici&amp;pn=Sharma%20Sweets&amp;cu=INR&amp;am=499&amp;tn=Kaju%20katli%201%20kg"' in out
    assert 'class="hs-qr" src="data:image/svg+xml;base64,' in out
    # no UPI ID: the pay button becomes a WhatsApp order; no address: the map asks for it
    site2 = {"language": "en", "facts": {"name": "X", "phone": "9876543210"}}
    out2, p2 = LV.expand('<a data-hoola-pay="99">Pay</a><div data-hoola-map></div>', site2, "", _icon)
    assert "upi://" not in out2 and "wa.me/919876543210" in out2 and "Order on WhatsApp" in out2
    assert "[address]" in out2 and "map: no address in her facts" in p2
    assert LV.youtube_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10") == "dQw4w9WgXcQ"
    assert LV.youtube_id("https://youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert not LV.vpa_ok("not a vpa") and LV.vpa_ok("ravi.k-1@ybl")
    csp = B.security_headers()["Content-Security-Policy"]
    assert "frame-src https://www.google.com https://maps.google.com https://www.youtube-nocookie.com;" in csp
    # a model-written upi: link is still refused by the sanitizer (only Hoola makes one)
    h, _c, _j, probs = B.sanitize_section("s-x", {"html": '<section><a href="upi://pay?pa=evil@x">x</a></section>'})
    assert "upi://" not in h


# ---------------------------------------------------------------- 2. booking: her real slots, her answer
def _site_with_booking(site_env):
    from app.site import service as S
    v = S.new(T, "salon ki website booking wala", conv_ctx().conversation_id, name="Glow Salon",
              answers={"phone": "9876543210", "address": "Station Road"})
    return v["id"]


def test_booking_real_slots_request_then_her_answer(site_env):
    from app.main import app
    from app.site import service as S
    from app.site.models import SiteLead
    from app.db import session
    sid = _site_with_booking(site_env)
    c = TestClient(app)
    r = c.get(f"/api/site-forms/{sid}/slots")
    assert r.status_code == 200 and r.headers["access-control-allow-origin"] == "*"
    slots = r.json()["slots"]
    assert len(slots) >= 3 and all(s["slot"] and s["label"] for s in slots)
    assert c.options(f"/api/site-forms/{sid}/book").status_code == 204
    pick = slots[0]["slot"]
    bad = c.post(f"/api/site-forms/{sid}/book", json={"slot": "2020-01-01T10:00:00+00:00", "name": "Ravi", "phone": "9822012345"})
    assert bad.status_code == 400
    ok = c.post(f"/api/site-forms/{sid}/book", json={"slot": pick, "name": "Ravi", "phone": "9822012345", "message": "haircut"})
    assert ok.status_code == 200 and ok.json() == {"ok": True}                  # the visitor never sees her lead id
    assert pick not in [s["slot"] for s in c.get(f"/api/site-forms/{sid}/slots").json()["slots"]]   # kept aside
    again = c.post(f"/api/site-forms/{sid}/book", json={"slot": pick, "name": "Asha", "phone": "9822012346"})
    assert again.status_code == 400
    with session() as s:
        lead = s.query(SiteLead).filter_by(site_id=sid, kind="booking").one()
        lid = lead.id
        assert lead.status == "new" and lead.slot == pick
    out = c.post(f"/api/sites-bookings/{lid}/decide", json={"yes": False}).json()
    assert out["status"] == "declined" and "wa.me/919822012345" in out["whatsapp"]
    assert pick in [s["slot"] for s in c.get(f"/api/site-forms/{sid}/slots").json()["slots"]]      # free again
    assert c.post(f"/api/sites-bookings/{lid}/decide", json={"yes": True}).status_code == 400     # answered once
    # an ordinary enquiry stays an enquiry
    c.post(f"/api/site-forms/{sid}", json={"name": "Meena", "phone": "9822012347", "message": "rate?"})
    with session() as s:
        assert s.query(SiteLead).filter_by(site_id=sid, kind="enquiry").count() == 1
    with pytest.raises(S.SiteError):
        S.answer(T, sid, {"upi": "1234 my pin"})
    S.answer(T, sid, {"upi": "glowsalon@okaxis"})
    assert json.loads(S._load(sid).facts)["upi"] == "glowsalon@okaxis"


# ---------------------------------------------------------------- 3. the launch bug: a live site kept every photo
def test_launched_site_keeps_its_photos(host_env):
    import io

    from PIL import Image

    from app.site import hosting as H
    from app.site import service as S
    from tests.test_v122_hosting import _ready_site
    g, _ = _ready_site()
    b = io.BytesIO()
    Image.new("RGB", (1600, 900), (200, 120, 40)).save(b, "JPEG")
    S.add_photo(T, g["id"], b.getvalue(), about="shop front", name="shop")
    r = S._load(g["id"])
    k = "home__hero"
    sec = S._sections(r)[k]
    S._put_sec(r, k, {**sec, "html": sec["html"].replace("</section>", '<img data-hoola-img="shop" alt="shop front"></section>', 1)})
    card = H.launch_request(T, g["id"])
    H.launch(T, g["id"], card["hash"])
    live = (H.hosted_root() / card["hosts"][0] / "index.html").read_text()
    assert "<picture>" in live and "assets/img/shop-" in live
    assert any((H.hosted_root() / card["hosts"][0] / "assets" / "img").glob("shop-*.jpg"))


# ---------------------------------------------------------------- 4. a second language
def test_second_language_switch_and_translations(site_env, monkeypatch):
    from app.site import ai as AI
    from app.site import build as B
    from app.site import lang as LG
    from app.site import service as S
    from app.site import edit as E
    calls = []

    def ask(system, prompt, max_tokens=6000, kind="build"):
        if system.startswith(LG.TRANSLATE_SYSTEM[:40]):
            src = prompt.split("SECTION HTML:\n", 1)[1]
            calls.append(src[:60])
            if "BREAKME" in src:
                return {"html": "<section><p>टूटा</p></section>"}
            return {"html": src.replace("Akot ki purani mithai ki dukaan.", "अकोट की पुरानी मिठाई की दुकान।")}
        if system.startswith("Translate these website page titles"):
            return {"pages": {"home": {"title": "होम", "nav": "होम"}, "contact": {"title": "संपर्क", "nav": "संपर्क"}}}
        return site_env(system, prompt, max_tokens, kind)
    monkeypatch.setattr(AI, "ask_json", ask)
    v = S.new(T, "mithai dukaan ki website", conv_ctx().conversation_id, name="Sharma Sweets",
              answers={"phone": "9876543210", "address": "Main Road, Akot"})
    S.approve_plan(T, v["id"], pages=["contact"])
    S.choose_look(T, v["id"], 0)
    sid = v["id"]
    ver = S.get(T, sid)["version"]
    with pytest.raises(S.SiteError):
        S.set_language(T, sid, "fr")
    S.set_language(T, sid, "hi")
    g = S.get(T, sid)
    assert g["languages"][1] == "hi" and g["version"] == ver + 1 and g["status"] == "ready"
    out = B.out_dir(T, sid, g["version"])
    home, hi = (out / "index.html").read_text(), (out / "hi" / "index.html").read_text()
    assert 'class="hs-lang" href="hi/" hreflang="hi"' in home and 'lang="hi"' in hi
    assert "अकोट की पुरानी मिठाई की दुकान।" in hi and "Akot ki purani mithai ki dukaan." in home
    assert 'class="hs-lang" href="../"' in hi and ">संपर्क<" in hi                     # back switch + translated menu
    assert (out / "hi" / "contact" / "index.html").exists()
    n = len(calls)
    # her own-hand edit: only that section is translated again
    r = S._load(sid)
    k = "home__hero"
    h = S._sections(r)[k]["html"]
    first_p = next(x for x in range(1, 40) if _has(h, x) and E.describe(h, str(x))["tag"] == "p")
    S.edit_element(T, sid, k, str(first_p), "text", "BREAKME naya line")
    assert len(calls) == n + 1
    hi2 = (B.out_dir(T, sid, S.get(T, sid)["version"]) / "hi" / "index.html").read_text()
    assert "BREAKME naya line" in hi2 and "टूटा" not in hi2           # a broken translation is dropped, the source stays
    assert LG.STATS["kept_source"] >= 1
    S.set_language(T, sid, "")
    assert not (B.out_dir(T, sid, S.get(T, sid)["version"]) / "hi").exists()


def _has(html, e):
    from app.site import edit as E
    try:
        E.describe(html, str(e))
        return True
    except Exception:
        return False


def test_version():
    from pathlib import Path
    from app.main import APP_VERSION
    assert APP_VERSION == "0.310.0"
    assert "0.310.0+350" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
