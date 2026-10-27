"""v0.138 The app Hoola designs is the app she asked for.
Bug: an ISP owner asked for "Spotify jaisa music sunne ka app" and got 3 ISP screens: her own business (profile / brand kit /
Kalam / stock) went into every app, the 1,000 business types had no consumer apps (music matched a musical-instruments shop),
an open question was ignored, and a goal passed by the chat model was trusted blindly."""
import os
import re

import pytest

from tests.test_v128_appdesign import FakeAI, good_screen

T = "default"


def _isp_owner():
    from app.db import session
    from app.employee.models import EmployeeProfile
    with session() as s:
        s.add(EmployeeProfile(tenant_id=T, business_name="FNW Fibernetwork Works", business_kind="isp", preset="isp",
                              about="FTTH broadband internet service provider: fiber net connection, wifi plans, Mbps",
                              upi_id="fnw@okaxis"))


def music_screen(sid, prompt):
    return {"html": f'<section id="scr-{sid}" class="scr"><header class="ab"><h1 class="ab-title">Sur</h1></header><div class="body">'
                    f'<p class="t-h2">Recently played</p><div class="rail"><div class="card"><div class="ph"><i data-ic="music"></i></div>'
                    f'<p class="t-title">Raat ki dhun <span class="pill">Demo</span></p><p class="t-small">Playlist · 24 songs</p></div></div>'
                    f'<button class="btn btn-primary" aria-label="Play"><i data-ic="play"></i> Play</button></div></section>',
            "css": "", "spec": {"purpose": "music home", "data": ["songs"], "actions": [], "components": ["rail"]}, "notes": "ok"}


def isp_screen(sid, prompt):
    return {"html": f'<section id="scr-{sid}" class="scr"><header class="ab"><h1 class="ab-title">FNW</h1></header><div class="body">'
                    f'<p class="t-h2">Broadband plans</p><div class="card"><p class="t-title">100 Mbps fiber internet</p>'
                    f'<p class="t-small">Net connection in 24 hours</p></div></div></section>', "css": "", "spec": {}, "notes": ""}


@pytest.fixture
def app_env(env, monkeypatch, tmp_path):
    monkeypatch.setenv("APP_DIR", str(tmp_path / "apps"))
    monkeypatch.setenv("APP_WORKER", "false")
    monkeypatch.setenv("APP_FONTS_FETCH", "false")
    monkeypatch.setenv("APP_FONTS_DIR", str(tmp_path / "fonts"))
    monkeypatch.setenv("SEMANTIC_OFF", "1")
    _isp_owner()
    return monkeypatch


# ---------------------------------------------------------------- 1. her words -> the right KIND of app
def test_product_apps_are_understood_and_businesses_still_work(monkeypatch):
    monkeypatch.setenv("SEMANTIC_OFF", "1")
    from app.appmaker import blueprint as BP
    from app.appmaker import library as L
    from app.appmaker import products as PR
    from app.appmaker import taxonomy as TX
    assert TX.check() == [] and PR.check() == [] and BP.check() == []
    c = L.counts()
    assert c["product_apps"] >= 30 and c["product_screen_types"] >= 90 and c["briefs"] == 160000 and c["goals"] == 10
    for q, goal, like in [("Spotify jaisa music sunne ka app banao", "music_streaming", "spotify"),
                          ("make a spotify like app for listening music", "music_streaming", "spotify"),
                          ("gaane sunne ki app", "music_streaming", ""), ("music streaming app", "music_streaming", ""),
                          ("netflix jaisa video app", "video_streaming", "netflix"), ("uber jaisa cab app", "ride_hailing", "uber"),
                          ("instagram jaisa social app", "social_feed", "instagram"), ("food delivery app like zomato", "food_delivery", "zomato"),
                          ("todo list app", "notes_todo", ""), ("fitness tracker app", "fitness_tracker", ""),
                          ("whatsapp jaisa chat app", "messenger", "whatsapp"), ("ludo game app", "casual_game", "")]:
        u = L.understand(q)
        assert u["goal"] == goal and u["field"] == PR.field_id(goal) and u["like"] == like, (q, u)
        assert len(set(u["styles"])) == 3
    # a business's app still goes to its trade (the product words step aside)
    for q, field, goal in [("music classes ki app", "music_classes", "learning"), ("guitar shop app", "music_instruments", "shop"),
                           ("kirana ki app ghar pe delivery", "kirana", "shop"), ("restaurant app menu order", "restaurant", "food_order"),
                           ("gym app membership wala", "gym", "membership"), ("delivery boy app for my courier", "courier", "delivery_driver")]:
        u = L.understand(q)
        assert u["field"] == field and u["goal"] == goal and not u.get("product"), (q, u)
    b = L.brief("app_music_streaming")
    assert {"now_playing", "playlist", "library", "queue"} <= set(b["screens"]) and b["tabs"] == ["home", "search", "library", "profile"]
    assert "PRODUCT app" in b["text"] and "licensed" in b["text"] and b["product"] == "music_streaming"
    assert not set(b["screens"]) & {"cart", "checkout", "plans_isp", "subscriber_list"}
    bp = BP.make("music_streaming", b["screens"])
    assert "media" in bp["modules"] and not bp["problems"]
    assert PR.refused("dream11 jaisa app") and not PR.refused("ludo game app")


# ---------------------------------------------------------------- 2. the bug: ISP owner asks for a Spotify-like app
def test_isp_owner_gets_a_music_app_not_her_isp(app_env):
    from app.appmaker import ai as AI
    from app.appmaker import service as S
    calls = []

    def fake(system, prompt, max_tokens=7000):
        sid = re.search(r"SCREEN_ID: scr-([\w-]+)", prompt).group(1)
        calls.append(prompt)
        return isp_screen(sid, prompt) if len(calls) == 1 else music_screen(sid, prompt)   # 1st try = the old bug
    app_env.setattr(AI, "ask_json", fake)
    # the chat model even passes her own trade's archetype + her business name
    v = S.new(T, "Spotify jaisa music sunne ka app banao", goal="isp_ops", name="FNW Fibernetwork Works")
    assert v["goal"] == "music_streaming" and v["field"] == "app_music_streaming"
    sc = v["plan"]["scope"]
    assert sc["product"] == "music_streaming" and sc["like"] == "spotify" and not sc["own_business"]
    assert sc["not_for"] == "FNW Fibernetwork Works"
    assert not v["name"] and "FNW" not in str(v["facts"]) and "upi_id" not in v["facts"]
    ids = [x["id"] for x in v["plan"]["screens"]]
    assert {"now_playing", "playlist", "library"} <= set(ids) and not any(x in ids for x in ("olt_list", "subscriber_list", "cart"))
    assert "music" in v["say"].lower() and "FNW Fibernetwork Works ki details nahi daali" in v["say"]
    assert any("naam" in q.lower() for q in v["questions"]) and not any("call / whatsapp" in q.lower() for q in v["questions"])
    r = S._load(v["id"])
    scr = S.write_screen(r, "home")
    assert len(calls) == 2 and "Recently played" in scr["html"] and "Broadband" not in scr["html"] and not scr.get("off_topic")
    p = calls[0]
    assert p.startswith("SHE ASKED FOR") and "Spotify jaisa music sunne ka app banao" in p and "Music streaming app" in p
    assert "never its name, logo" in p and "NOT for the owner's own business" in p
    assert "FNW" not in p.split("SHE ASKED FOR")[1].split("NOT for the owner's own business")[1]
    assert "broadband" not in p.lower() and "fnw@okaxis" not in p
    assert "YOUR LAST TRY WAS WRONG" in calls[1] and "broadband" in calls[1].lower()
    assert S.relevance(r, "home", isp_screen("home", "")["html"]) and not S.relevance(r, "home", scr["html"])
    assert S.STATS["off_topic"] >= 1 and S.STATS["not_her_business"] >= 1


# ---------------------------------------------------------------- 3. her own business still gets her facts; unsure = ask first
def test_own_business_keeps_her_facts_and_unclear_asks(app_env):
    from app.appmaker import ai as AI
    from app.appmaker import service as S
    app_env.setattr(AI, "ask_json", FakeAI())
    v = S.new(T, "meri dukaan ki app, customers ke liye")          # no trade words: her own trade decides
    assert v["plan"]["scope"]["own_business"] and v["field"] in ("isp", "fiber_franchise")
    assert v["facts"].get("name") == "FNW Fibernetwork Works" and v["facts"].get("upi_id") == "fnw@okaxis"
    v2 = S.new(T, "mere ISP ka customer app, bill aur complaint")
    assert v2["plan"]["scope"]["own_business"] and v2["facts"].get("name") == "FNW Fibernetwork Works"
    v3 = S.new(T, "salon ki app banao")                              # another trade, not hers: her ISP stays out
    assert v3["field"] == "salon" and not v3["plan"]["scope"]["own_business"] and "name" not in v3["facts"]
    avoid = S._j(S._load(v3["id"]).plan, {})["scope"]["avoid"]
    assert "salon" not in str(avoid).lower() and "broadband" in avoid and "FNW Fibernetwork Works" in avoid
    # a product word and a business both fit -> one question before anything is built
    with pytest.raises(S.AppError) as e:
        S.new(T, "photo app")
    assert "Pakka karne ke liye" in str(e.value) and " ya " in str(e.value) and S.STATS["asked_first"] >= 1
    assert S.new(T, "photo app", answers={"sure": True})["status"] == "planned"      # she said: go ahead with the first
    with pytest.raises(S.AppError) as e2:
        S.new(T, "dream11 jaisa fantasy app")
    assert "Online Gaming Act" in str(e2.value)
    # a business goal the chat model passes is still used when it fits her words / the trade
    v4 = S.new(T, "kirana ki app ghar pe delivery", goal="catalogue")
    assert v4["goal"] == "catalogue"
    v5 = S.new(T, "kirana ki app ghar pe delivery", goal="isp_ops")
    assert v5["goal"] == "shop"


# ---------------------------------------------------------------- 4. the 3 looks are of the right app (real Chromium)
def test_looks_are_music_not_isp(app_env):
    pytest.importorskip("playwright")
    from app.appmaker import ai as AI
    from app.appmaker import service as S
    seen = []

    def fake(system, prompt, max_tokens=7000):
        sid = re.search(r"SCREEN_ID: scr-([\w-]+)", prompt).group(1)
        seen.append("WRONG" in prompt)
        return isp_screen(sid, prompt) if "WRONG" not in prompt else music_screen(sid, prompt)
    app_env.setattr(AI, "ask_json", fake)
    v = S.new(T, "gaane sunne ka app chahiye, jaise Spotify")
    r = S._load(v["id"])
    S._make_looks(r)
    r = S._load(v["id"])
    looks = S._j(r.looks, [])
    assert len(looks) == 3
    for i in range(3):
        home = (S.K.app_dir(T, r.id) / "looks" / str(i) / "home.json").read_text()
        assert "Recently played" in home and "Broadband" not in home
    assert seen.count(True) == 3
