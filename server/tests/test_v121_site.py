"""v0.121 Website Sahayak: 1 lakh brief library -> plan card -> 3 looks (real screenshots) -> section-by-section build with
motion runtime -> checks in real Chromium (+ fix rounds) -> preview (public, signed, CSP) -> changes in her words ->
forms to leads -> export. The model is a fake that writes real sections."""
import io
import json
import re
import zipfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import Event, session
from tests.test_life import conv_ctx

T = "default"


def _events(kind):
    with session() as s:
        return [e.payload for e in s.scalars(select(Event).where(Event.kind == kind).order_by(Event.id)).all()]


# ---------------------------------------------------------------- a fake Opus that writes real, clean sections
def _sid(prompt):
    return re.search(r"SECTION_ID: ([\w-]+)", prompt).group(1)


def good_section(sid, prompt, blank=True):
    typ = sid.split("-", 2)[2] if sid.count("-") >= 2 else "hero"
    h = "h1" if "ONLY <h1>" in prompt else "h2"
    if "contact" in typ:
        inner = ('<form class="hs-form" data-hoola-form><label>Naam <input name="name" required></label>'
                 '<label>Phone <input name="phone" required></label><label>Message <textarea name="message"></textarea></label>'
                 '<input class="hp" name="website" tabindex="-1" autocomplete="off"><p class="hs-consent">Hum sirf aapko jawab '
                 'dene ke liye yeh rakhenge.</p><button type="submit" class="btn btn-primary">Bhejiye</button>'
                 '<p class="hs-form-msg" role="status"></p></form>')
    elif "hero" in typ:
        m = re.search(r'"phone": "(\d{10})"', prompt)
        tel = m.group(1) if m else "9876543210"
        since = '<em class="blank">[year]</em>' if blank else "1995"
        inner = (f'<p class="eyebrow">Since {since}</p>'
                 f'<div class="btns"><a class="btn btn-primary" data-m="magnetic" href="tel:+91{tel}">Call karein</a></div>'
                 '<svg data-m="draw" viewBox="0 0 200 20" aria-hidden="true"><path d="M0 10 Q100 0 200 10" stroke="currentColor" fill="none"/></svg>')
    else:
        inner = ('<div class="grid g3" data-m="stagger"><article class="card"><h3>Kaju katli</h3><p class="muted">Roz taaza.</p></article>'
                 '<article class="card"><h3>Motichoor laddoo</h3><p class="muted">Desi ghee mein.</p></article>'
                 '<article class="card"><h3>Gift box</h3><p class="muted">Tyohar ke liye.</p></article></div>'
                 '<p><span data-m="count" data-to="25" data-suffix="+">25+</span> mithaiyan</p>')
    return {"html": f'<section id="{sid}" class="hs"><div class="wrap"><{h} data-m="split">Sharma Sweets {typ}</{h}>'
                    f'<p class="lead" data-m="reveal">Akot ki purani mithai ki dukaan.</p>{inner}</div></section>',
            "css": f"#{sid} .card h3{{color:var(--c-primary-text)}} .lead{{max-width:50ch}} @media (min-width:768px){{h2{{font-size:2.4rem}}}}",
            "js": "", "notes": "ok"}


class FakeAI:
    def __init__(self, bad=None):
        self.blank = True
        self.marker = ""
        self.calls = []
        self.bad = bad or set()        # section ids to write badly the first time
        self.change = None

    def __call__(self, system, prompt, max_tokens=6000, kind="build"):
        from app.site import ai as AI
        if system.startswith(AI.CHANGE_SYSTEM[:40]):
            self.calls.append(("change", prompt))
            return self.change or {}
        if system.startswith(AI.FIX_SYSTEM[:40]):
            sid = _sid(prompt)
            self.calls.append(("fix", sid))
            return good_section(sid, "ONLY <h1>" if "hero" in sid else "", self.blank)
        sid = _sid(prompt)
        self.calls.append(("section", sid))
        if sid in self.bad:
            self.bad.discard(sid)
            return {"html": f'<section id="{sid}"><h2>Wide</h2><div style="width:2400px;height:20px;background:#eee"></div>'
                            f'<img src="https://evil.example/x.png"><p style="color:#fafafa">almost invisible text here</p>'
                            f'<script>alert(1)</script><a href="javascript:alert(2)" onclick="x()">x</a></section>',
                    "css": "@import url(https://evil.example/a.css); p{color:#fafafa}", "js": "fetch('https://evil.example')"}
        out = good_section(sid, prompt, self.blank)
        if self.marker:
            out["html"] = out["html"].replace("Akot ki purani", f"{self.marker} Akot ki purani")
        return out


@pytest.fixture
def site_env(env, monkeypatch, tmp_path):
    monkeypatch.setenv("SITE_DIR", str(tmp_path / "sites"))
    monkeypatch.setenv("SITE_WORKER", "false")
    monkeypatch.setenv("SITE_LIGHTHOUSE", "false")
    from app.site import ai as AI
    fake = FakeAI()
    monkeypatch.setattr(AI, "ask_json", fake)
    return fake


# ---------------------------------------------------------------- 1. the library
def test_library_counts_and_understanding(monkeypatch):
    monkeypatch.setenv("SEMANTIC_OFF", "1")
    from app.site import library as L
    from app.site import taxonomy as TX
    assert TX.check() == []
    c = L.counts()
    assert c["fields"] == 1000 and c["briefs"] == 100000 and c["phrases"] == 5000
    assert (c["section_designs"], c["motion_presets"], c["palettes"], c["font_pairs"], c["hero_types"]) == (300, 60, 50, 30, 24)
    for q, field in [("mithai dukaan ki website", "sweet_shop"), ("मिठाई की दुकान", "sweet_shop"), ("resturant menu online", "restaurant"),
                     ("dant doctor", "dentist"), ("CA office website", "chartered_accountant"), ("जिम की वेबसाइट", "gym"),
                     ("vakil sahab", "advocate"), ("fiber internet company", "isp"), ("meri bakary ke liye site", "bakery"),
                     ("paithani saree", "saree_shop"), ("hospital website with booking", "hospital")]:
        assert L.understand(q)["field"] == field, q
    u = L.understand("gym site chahiye booking wala")
    assert u["goal"] == "booking" and len(u["styles"]) == 3 and len(set(u["styles"])) == 3
    assert L.understand("kuch bhi")["ask"]
    # the brief carries the profession's rules
    b = L.brief("advocate")
    assert "Bar Council" in b["text"] and "disclaimer" in b["pages"] and b["pages"][-1] == "privacy"
    assert "NMC" in L.brief("general_physician")["text"]
    d = L.brief("sweet_shop", "catalogue", "festive_traditional")
    assert d["id"] == "sweet_shop.catalogue.festive_traditional" and "refund" in d["pages"]
    assert "Never invent prices" in d["text"]
    # phrases map back to their own card (quality floor)
    ph = L.phrases()[::10]
    ok = sum(1 for p in ph if (L.match(p["text"], 1) or [{}])[0].get("id") == p["field"])
    assert ok / len(ph) >= 0.95


def test_guard_and_sanitize():
    from app.site import build as Bd
    from app.site.guard import brief_problem, name_problem
    assert brief_problem("SBI jaisi website banao")
    assert brief_problem("flipkart ka clone")
    assert brief_problem("KYC update form for HDFC customers")
    assert brief_problem("tiranga wala hero section")
    assert not brief_problem("amazon jaisa online store mere kapdo ka")
    assert not brief_problem("meri website google par dikhe")
    assert name_problem("sbi-loans.in") and not name_problem("sharmasweets.in")
    h, css, js, probs = Bd.sanitize_section("s-home-hero", {
        "html": '<div><h1 onclick="x()">Hi</h1><img src="https://evil.example/a.png" alt="a"><script>alert(1)</script>'
                '<iframe src="https://x.example"></iframe><a href="javascript:alert(1)">bad</a><a href="tel:+919876543210">ok</a>'
                '<a href="https://wa.me/919876543210">wa</a></div>',
        "css": "@import url('https://evil.example/x.css'); h1{color:red} @media (min-width:768px){.a{top:0}} "
               "body{background:url(https://evil.example/b.png)} @keyframes k{to{opacity:1}}",
        "js": "fetch('/steal')"})
    assert "<script" not in h and "<iframe" not in h and "onclick" not in h and "evil.example" not in h
    assert 'id="s-home-hero"' in h and "javascript:" not in h and 'href="tel:+919876543210"' in h
    assert 'rel="noopener"' in h
    assert "@import" not in css and "evil.example" not in css and "#s-home-hero h1{color:red}" in css
    assert "@media (min-width:768px){#s-home-hero .a{top:0}}" in css and "@keyframes k" in css
    assert js == "" and any("script" in p for p in probs)
    tk = Bd.tokens("bold_modern", "ink_lime", {"primary": "#123456"})
    assert tk["primary"] == "#123456" and tk["on_primary"] in ("#FFFFFF", "#111111")
    css2 = Bd.tokens_css(tk)
    assert "--c-primary:#123456" in css2 and "space-grotesk-latin-700.woff2" in css2


# ---------------------------------------------------------------- 2. the whole flow, real Chromium
def test_full_flow_plan_looks_build_checks_preview(site_env, monkeypatch):
    from app.main import app
    from app.site import service as S
    ctx = conv_ctx()
    c = TestClient(app)
    v = S.new(T, "mithai dukaan ki website, online order WhatsApp par. Phone 98765 43210", ctx.conversation_id,
              name="Sharma Sweets")
    assert v["status"] == "planned" and v["field"] == "sweet_shop" and v["goal"] == "catalogue"
    assert v["number"] == "S-0001" and v["facts"]["phone"] == "9876543210"
    assert any("Address" in q for q in v["questions"]) and len(v["questions"]) <= 3
    plan_slugs = [p["slug"] for p in v["plan"]["pages"]]
    assert plan_slugs[0] == "home" and "privacy" in plan_slugs
    ev = _events("site_board")
    assert ev and ev[-1]["status"] == "planned" and ev[-1]["push"] is True
    v = S.answer(T, v["id"], {"0": "Main Road, Akot"})
    assert v["facts"]["address"] == "Main Road, Akot" and not any("Address" in q for q in v["questions"])
    # her tap on the plan -> 3 looks with real screenshots
    r = c.post(f"/api/sites/{v['id']}/plan", json={"pages": ["products", "contact"]})
    assert r.status_code == 200, r.text
    g = S.get(T, v["id"])
    assert g["status"] == "looks" and len(g["looks"]) == 3
    assert all(lk["shots"].get("390") and lk["shots"].get("1440") for lk in g["looks"])
    assert {p["slug"] for p in g["plan"]["pages"]} <= {"home", "products", "contact", "refund", "privacy"}
    looks_calls = [x for x in site_env.calls if x[0] == "section"]
    assert len(looks_calls) == 3
    # she picks look 1 with look 0's colours -> build, checks, version
    r = c.post(f"/api/sites/{v['id']}/look", json={"index": 1, "colors_from": 0})
    assert r.status_code == 200, r.text
    g = S.get(T, v["id"])
    assert g["status"] == "ready", g.get("error")
    assert g["version"] == 1 and g["board"]["pct"] == 100
    assert g["checks"]["passed"] is True, g["checks"]["blocking"]
    sc = g["scores"]
    assert sc["accessibility"] >= 90 and sc["first_load_kb"] < 1024 and sc["js_kb"] < 120
    # the home hero came from the chosen look (not written again)
    built = [x[1] for x in site_env.calls if x[0] == "section"][3:]
    assert "s-home-hero" not in built and "s-home-products-grid" in built
    # Work Theatre website scene + chat cards
    works = [e for e in _events("work") if e.get("tool") == "website"]
    assert works and works[0]["scene"] == "website" and any(w["phase"] == "done" for w in works)
    assert _events("site_board")[-1]["status"] == "ready" and _events("site_board")[-1]["push"] is True
    # preview: public by token, strict headers, real files
    tok = g["preview"].rsplit("/api/site-preview/", 1)[1].strip("/")
    r = c.get(f"/api/site-preview/{tok}/")
    assert r.status_code == 200 and "Sharma Sweets" in r.text and "hoola-site.js" in r.text
    assert "script-src 'self'" in r.headers["content-security-policy"] and r.headers["x-robots-tag"].startswith("noindex")
    assert 'data-endpoint="' in c.get(f"/api/site-preview/{tok}/contact/").text
    assert c.get(f"/api/site-preview/{tok}/assets/site.css").status_code == 200
    assert c.get(f"/api/site-preview/{tok}/privacy/").text.count("Grievance officer") == 1
    assert c.get(f"/api/site-preview/{tok}/../../../etc/passwd").status_code == 404
    assert c.get("/api/site-preview/wrongtokenwrongtoken/").status_code == 404
    page = c.get(f"/api/site-preview/{tok}/").text
    assert page.count("<h1") == 1 and 'href="tel:+919876543210"' in page and "wa.me/919876543210" in page
    assert "application/ld+json" in page and '"telephone": "+919876543210"' in page
    # screenshots + export
    shot = c.get(f"/api/sites/{v['id']}/shots/v1/home-390.jpg")
    assert shot.status_code == 200 and shot.content[:2] == b"\xff\xd8"
    ex = S.export(T, v["id"])
    from app.mailbox import service as ms
    _n, _m, data = ms.load_files(T, [{"type": "file", "file_id": ex["file_id"]}])[0]
    names = zipfile.ZipFile(io.BytesIO(data)).namelist()
    assert "index.html" in names and "assets/hoola-site.js" in names and "_headers" in names and "privacy/index.html" in names
    assert any(n.startswith("assets/fonts/") for n in names)


def test_checks_catch_problems_and_fix_rounds(site_env, monkeypatch):
    from app.site import service as S
    ctx = conv_ctx()
    site_env.bad = {"s-home-products-grid"}
    v = S.new(T, "bakery ki website", ctx.conversation_id, name="Akot Bakery", answers={"phone": "9876543210",
                                                                                         "address": "Station Road"})
    S.approve_plan(T, v["id"], pages=["contact"])
    S.choose_look(T, v["id"], 0)
    g = S.get(T, v["id"])
    assert g["status"] == "ready"
    fixes = [x[1] for x in site_env.calls if x[0] == "fix"]
    assert "s-home-products-grid" in fixes           # the wide / low-contrast section was rewritten
    assert g["checks"]["passed"] is True, g["checks"]["blocking"]
    sec = json.loads(next((p for p in (S.B.src_dir(T, v["id"]) / "sections").glob("home__products_grid.json"))).read_text())
    assert "evil.example" not in sec["html"] and "<script" not in sec["html"]


def test_change_rebuilds_only_what_she_asked_and_queue_and_stop(site_env):
    from app.site import service as S
    ctx = conv_ctx()
    v = S.new(T, "salon ki website booking ke saath", ctx.conversation_id, name="Glow Salon",
              answers={"phone": "9876543210", "address": "Akola"})
    S.approve_plan(T, v["id"], pages=["services", "contact"])
    S.choose_look(T, v["id"], 2)
    before = len([x for x in site_env.calls if x[0] == "section"])
    site_env.change = {"say": "Hero mein naya offer daal raha hoon", "sections": [{"key": "home__hero", "instruction": "add Diwali offer"}],
                       "tokens": {"primary": "#7A1E2C"}, "facts": {"phone": "9123456789"}}
    out = S.change(T, v["id"], "hero mein Diwali offer daalo, rang maroon, naya number 91234 56789", ctx.conversation_id)
    assert "offer" in out["say"]
    after = [x[1] for x in site_env.calls if x[0] == "section"][before:]
    assert after == ["s-home-hero"]
    g = S.get(T, v["id"])
    assert g["version"] == 2 and g["status"] == "ready"
    css = (S.B.out_dir(T, v["id"], 2) / "assets" / "site.css").read_text()
    assert "--c-primary:#7A1E2C" in css
    home = (S.B.out_dir(T, v["id"], 2) / "index.html").read_text()
    assert "9123456789" in home and "9876543210" not in home
    # asked while building -> queued
    from app.site.models import Site
    with session() as s:
        s.get(Site, v["id"]).status = "building"
    q = S.change(T, v["id"], "footer mein Instagram link")
    assert "queue" in q["say"]
    with session() as s:
        row = s.get(Site, v["id"])
        assert json.loads(row.queued) == ["footer mein Instagram link"]
        row.status = "ready"
    st = S.stop(T, v["id"])
    assert "Rok" in st["say"]


def test_forms_leads_cors_and_tools(site_env):
    from app.main import app
    from app.site import service as S
    from app.agent.tools import Ctx, ToolError, dispatch
    import asyncio
    ctx = conv_ctx()
    c = TestClient(app)
    out = asyncio.run(dispatch("website", {"action": "new", "brief": "CA office website", "name": "Rao & Co",
                                           "answers": {"phone": "9876543210", "address": "Pune"}}, ctx))
    assert out["field_label"] == "Chartered accountant"
    sid = out["id"]
    staff = Ctx(T, ctx.conversation_id, actor="staff:x")
    with pytest.raises(ToolError):
        asyncio.run(dispatch("website", {"action": "plan_ok", "site": sid}, staff))
    r = c.options(f"/api/site-forms/{sid}")
    assert r.status_code == 204 and r.headers["access-control-allow-origin"] == "*"
    r = c.post(f"/api/site-forms/{sid}", json={"name": "Asha", "phone": "98220 12345", "message": "GST return chahiye"})
    assert r.status_code == 200 and r.json()["ok"] and r.headers["access-control-allow-origin"] == "*"
    leads = S.leads(T, sid)
    assert leads[0]["phone"] == "9822012345" and leads[0]["message"] == "GST return chahiye"
    assert _events("site_lead")[-1]["name"] == "Asha"
    from app.telecall.service import TeleLead  # the lead also lands in the call list
    with session() as s:
        assert s.scalars(select(TeleLead).where(TeleLead.phone == "9822012345")).first() is not None
    # honeypot: accepted silently, nothing stored
    c.post(f"/api/site-forms/{sid}", json={"name": "bot", "phone": "9000000000", "website": "spam.example"})
    assert len(S.leads(T, sid)) == 1
    assert c.post(f"/api/site-forms/{sid}", json={"name": "x"}).status_code == 400
    for _ in range(6):
        r = c.post(f"/api/site-forms/{sid}", json={"name": "y", "phone": "9822012399"})
    assert r.status_code == 400
    # reading tools
    lib = asyncio.run(dispatch("website_dekho", {"what": "understand", "q": "tuition classes ki site"}, ctx))
    assert lib["field"] == "tuition_classes"
    sites = asyncio.run(dispatch("website_dekho", {"what": "sites"}, ctx))
    assert sites["sites"][0]["number"] == "S-0001"
    # look-alike refused
    with pytest.raises(ToolError):
        asyncio.run(dispatch("website", {"action": "new", "brief": "SBI jaisi website banao"}, ctx))
