"""v0.772 HOOLA INTERACTIVE, the whole product (owner: "GO - BUILD IT INTO CONSOLE END TO END" after the approved
twelve-page design): what the pages stand on. Every rule here is one the page promises her in words."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.interactive import hub as H
from app.interactive import studio as S

T = "t1"
DRAFT = {"title": "Rate", "closing": "", "scenes": [
    {"say": "Akola mein aaj cement ka rate 380 rupaye hai.", "look": {"kind": "big_number", "value": "380", "label": "per bag"}},
    {"say": "Offer 10 November tak.", "look": {"kind": "title", "text": "Offer"}}]}


@pytest.fixture()
def hub(env, monkeypatch, tmp_path):
    monkeypatch.setenv("INTERACTIVE_PAGE", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setattr(S, "_root", lambda: tmp_path)
    monkeypatch.setattr(S, "_brain", lambda system, prompt: json.loads(json.dumps(DRAFT)))
    S._JOBS.clear()
    yield tmp_path
    S._JOBS.clear()


def _p(ask="Cement rate 380 rupaye, offer 10 November tak, Akola"):
    return S.draft(T, ask)


def test_her_brand_starts_every_video_and_its_colour_reaches_the_film(hub):
    H.brand_set(T, {"name": "Sharma Traders", "closing": "Station Road", "color": "#0f8f80"})
    with pytest.raises(S.StudioError):
        H.brand_set(T, {"color": "teal"})                                  # a colour the film cannot draw is refused
    p = _p()
    spec, _ = S.spec_for(T, p, silent=True)
    assert spec["brand"]["color"] == "#0F8F80"                             # drawn into the composition, not just stored
    made = H.batch(T, ["Kal dukaan band rahegi."])[0]
    assert made["brand"] == "Sharma Traders" and made["closing"] == "Station Road"


def test_a_template_only_ever_takes_her_values(hub):
    tpl = next(t for t in H.templates(T) if t["id"] == "tp_offer")
    assert tpl["variables"] == ["shop", "festival", "item", "price", "last_date"] and not tpl["mine"]
    with pytest.raises(S.StudioError) as e:
        H.template_use(T, "tp_offer", {"shop": "Sharma Traders", "festival": "Diwali", "item": "Cement"})
    assert "price" in str(e.value) and "last date" in str(e.value)        # the missing blanks are NAMED, never filled in
    p = H.template_use(T, "tp_offer", {"shop": "Sharma Traders", "festival": "Diwali", "item": "Cement",
                                         "price": "Rs 380", "last_date": "10 November"})
    assert "Rs 380" in p["scenes"][1]["say"] and p["scenes"][1]["look"]["new"] == "Rs 380"
    assert not S.problems(p) and not H.VAR.search(json.dumps(p["scenes"])) and p["closing"] == "Sharma Traders"
    for t in H.BUILTIN:                                                     # no starter template states a price or a date
        assert not S._digits(json.dumps(t["scenes"])), t["id"]


def test_her_own_video_becomes_a_template_and_many_names(hub):
    p = _p()
    S.save(T, p["id"], {"scenes": [{"say": "{name} ji, aapka order taiyaar hai.", "look": {"kind": "none"}}]})
    t = H.template_save(T, p["id"], "Order ready")
    assert t["mine"] and t["variables"] == ["name"]
    made = H.personalise(T, p["id"], ["Sunita", "Rahul", "sunita", " "])
    assert [m["scenes"][0]["say"] for m in made] == ["Sunita ji, aapka order taiyaar hai.", "Rahul ji, aapka order taiyaar hai."]
    with pytest.raises(S.StudioError):
        H.personalise(T, made[0]["id"], ["A"])                              # that draft no longer says {name}
    with pytest.raises(S.StudioError):
        H.personalise(T, p["id"], [f"n{i}" for i in range(H.MAX_BATCH + 1)])
    assert H.template_remove(T, t["id"]) and all(not x["mine"] for x in H.templates(T))


def test_a_batch_cuts_scenes_by_code_and_never_rewrites_her_words(hub):
    made = H.batch(T, ["Aaj ka rate 380 hai. Kal 390 hoga! Jaldi aaiye", "", "Dukaan band."])
    assert len(made) == 2 and [s["say"] for s in made[0]["scenes"]] == ["Aaj ka rate 380 hai.", "Kal 390 hoga!", "Jaldi aaiye"]
    with pytest.raises(S.StudioError):
        H.batch(T, ["x"] * (H.MAX_BATCH + 1))
    with pytest.raises(S.StudioError):
        H.batch(T, [" ", ""])


def test_a_translation_is_checked_by_code_not_trusted(hub):
    p = _p()
    H.glossary_add(T, "Akola")                                             # keep as written
    H.glossary_add(T, "offer", mode="as", to="sawlat", lang="mr")
    good = {"lines": ["Akola madhe aaj cement cha dar 380 rupaye aahe.", "per bag", "sawlat 10 November paryant.", "sawlat"]}
    out = H.translate(T, p["id"], "mr", think=lambda s, pr: good)
    assert out["lang"] == "mr" and out["from"] == p["id"] and [n["flag"] for n in out["tr"]] == ["", ""]
    assert out["scenes"][0]["look"]["value"] == "380" and out["tr"][0]["src"].startswith("Akola mein")
    bad = {"lines": ["Nagpur madhe aaj cement cha dar 390 rupaye aahe.", "per bag", "offer 10 November paryant.", "sawlat"]}
    out2 = H.translate(T, p["id"], "mr", think=lambda s, pr: bad)
    assert out2["tr"][0]["flag"] == "A number changed - check this line"   # 380 became 390: flagged, never silent
    assert out2["tr"][1]["flag"] == "'offer' should be 'sawlat'"
    kept = {"lines": ["Aaj cement cha dar 380 rupaye aahe.", "per bag", "sawlat 10 November paryant.", "sawlat"]}
    assert H.translate(T, p["id"], "mr", think=lambda s, pr: kept)["tr"][0]["flag"] == "'Akola' must stay as written"
    with pytest.raises(S.StudioError):
        H.translate(T, p["id"], "mr", think=lambda s, pr: {"lines": ["only one"]})   # a missing line is never guessed
    with pytest.raises(S.StudioError):
        H.translate(T, p["id"], "hi", think=lambda s, pr: good)                      # already in that language


def test_trash_keeps_the_video_and_restore_brings_it_back(hub):
    p = _p()
    f = S.video_path(T, p["id"])
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(b"mp4")
    S._set_status(T, p["id"], status="ready", video={"duration": 30, "made": S._now_iso()})
    assert H.trash(T, p["id"]) and f.is_file() and not S.listing(T)["projects"]
    assert H.overview(T)["trash"][0]["id"] == p["id"]
    back = H.restore(T, p["id"])
    assert back["status"] == "ready" and S.listing(T)["projects"][0]["id"] == p["id"]
    H.trash(T, p["id"])
    d = S._load(T)
    d["trash"][0]["trashed_ts"] = 1.0                                       # 30 days are over
    S._store(T, d)
    assert H.overview(T)["trash"] == [] and not f.is_file()
    q = _p()
    H.trash(T, q["id"])
    assert H.empty_trash(T) == 1
    with pytest.raises(S.StudioError):
        H.restore(T, q["id"])


def test_usage_is_read_from_the_videos_and_status_says_what_is_not_connected(hub):
    a, b = _p(), H.duplicate(T, _p()["id"])
    assert b["title"].endswith("(copy)") and b["status"] == "draft"
    S._set_status(T, a["id"], status="ready", video={"duration": 90, "made": S._now_iso()})
    S._set_status(T, b["id"], status="ready", video={"duration": 30, "made": "2020-01-01T00:00:00"})
    u = H.usage(T)
    assert u["videos"] == 1 and u["minutes"] == 1.5 and u["stored"] == 2    # last year's video is not this month's
    c = H.status()["connected"]
    assert c["photo_avatar"] and c["templates"] and c["translate_words"]
    assert not any(c[k] for k in ("twin", "ai_face", "voice_clone", "dub_outside_video", "live_stream", "api"))


def test_a_brain_needs_real_facts_and_only_web_links(hub):
    with pytest.raises(S.StudioError):
        H.brain_save(T, {"name": "Helper", "knows": "too short"})
    b = H.brain_save(T, {"name": "Shop helper", "knows": "Sharma Traders, Akola. Open 9 am to 9 pm, closed Sunday.",
                         "links": ["https://sharmatraders.in/rates", "javascript:alert(1)", "file:///etc/passwd"]})
    assert b["links"] == ["https://sharmatraders.in/rates"]
    again = H.brain_save(T, {"id": b["id"], "name": "Shop helper 2", "knows": b["knows"]})
    assert again["id"] == b["id"] and len(H.overview(T)["brains"]) == 1
    assert H.brain_remove(T, b["id"]) and H.overview(T)["brains"] == []


def test_the_hub_routes_are_locked_switched_and_tenant_scoped(hub, monkeypatch):
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    ov = c.get("/api/interactive/hub/overview").json()
    assert {"projects", "avatars", "templates", "glossary", "trash", "brains", "usage", "status", "brand"} <= set(ov)
    assert c.put("/api/interactive/hub/brand", json={"name": "Sharma Traders", "color": "#5B45E0"}).json()["color"] == "#5B45E0"
    assert c.put("/api/interactive/hub/brand", json={"color": "red"}).status_code == 422
    p = c.post("/api/interactive/studio/draft", json={"ask": "Cement rate 380, offer 10 November tak"}).json()
    assert p["brand"] == "Sharma Traders"                                   # the Brand page is the default
    r = c.post("/api/interactive/hub/template/use", json={"id": "tp_rate", "values": {"shop": "S", "item": "Cement"}})
    assert r.status_code == 422 and "rate" in r.json()["detail"]
    made = c.post("/api/interactive/hub/batch", json={"scripts": ["Ek. Do."]}).json()["made"]
    assert len(made) == 1 and len(made[0]["scenes"]) == 2
    assert c.post("/api/interactive/hub/trash", json={"id": p["id"]}).json()["ok"]
    assert c.post("/api/interactive/hub/restore", json={"id": p["id"]}).json()["id"] == p["id"]
    assert c.post("/api/interactive/hub/duplicate", json={"id": "nope"}).status_code == 404
    assert c.get("/api/interactive/hub/voice?lang=hi").status_code == 503   # the voice engine is not set up: said, 503
    monkeypatch.setenv("INTERACTIVE_PAGE", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    assert c.get("/api/interactive/hub/overview").status_code == 403


def test_the_page_is_wired_and_says_what_is_not_built():
    root = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
    js, html, css = (root / "interactive.js").read_text(), (root / "v2.html").read_text(), (root / "v2.css").read_text()
    for page in ("home", "avatars", "voices", "studio", "templates", "brand", "translate", "live", "apps", "projects", "developers", "settings"):
        assert f"['{page}'," in js and f"    {page}()" in js, page             # twelve rail items, twelve drawn pages
    assert html.count('rel="stylesheet" href="/static/console/') == 1 and "#hiRoot .hi-rail" in css   # one stylesheet, the console rule
    assert "/api/interactive/hub" in js and "Not connected on this server yet" in js
    assert "sample" not in js.lower()                                       # no sample data ships in the real page
    main = (root.parents[1] / "main.py").read_text()
    assert "make_hub_router" in main
