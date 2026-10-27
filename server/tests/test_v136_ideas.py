"""v0.136 1 crore app ideas: exact count of combinations that make sense, every idea built from its id, her words pick one."""
import random

from fastapi.testclient import TestClient


def test_more_than_one_crore_real_ideas_each_valid_and_rebuildable():
    from app.appmaker import ideas as I
    from app.appmaker import taxonomy as T
    assert I.check() == []
    tot = I.total()
    assert tot >= 1_00_00_000, tot
    c = I.counts()
    assert c["fields"] == 1000 and c["twists"] >= 50 and c["field_goal_pairs"] > 5000
    rnd = random.Random(7)
    seen = set()
    for n in [0, tot - 1] + rnd.sample(range(tot), 1500):
        p = I.nth(n)
        assert I.valid(p) == "", p
        it = I.idea(I.make_id(p))
        assert it["id"] not in seen
        seen.add(it["id"])
        assert all(s in T.SCREENS for s in it["screens_added"])
        assert it["pitch"] and it["line"].startswith("IDEA:")
    try:
        I.nth(tot)
        raise AssertionError("past the end")
    except IndexError:
        pass
    # combinations that make no sense are not ideas
    bad = dict(I.nth(0))
    bad["aud"] = "customer"
    bad["goal"] = "hrms"
    assert I.valid(bad)
    for wrong in ("kirana.shop.customer.kanban.solo.town.mid.direct_sales", "x.y", "kirana.shop.rider.x.solo.town.mid.saas"):
        try:
            I.idea(wrong)
            raise AssertionError(wrong)
        except KeyError:
            pass


def test_her_words_pick_a_precise_idea():
    from app.appmaker import ideas as I
    u = I.understand("kirana dukaan ki app, roz doodh subscription, whatsapp se order")
    assert u["field"] == "kirana" and u["idea"]["twist"] == "daily_subscription"
    assert any(x["twist"] == "whatsapp_first" for x in u["alternatives"])
    assert u["count"] > 1000
    u = I.understand("school erp app parents ko report")
    assert u["idea"]["goal"] == "school_erp" and u["idea"]["twist"] == "parent_view"
    u = I.understand("premium salon ki app, ghar par seva, mumbai")
    i = u["idea"]
    assert i["twist"] == "home_visit" and i["tier"] == "premium" and i["market"] == "metro"
    assert "luxury_noir" in i["styles"]
    u = I.understand("delivery boy ke liye app, kirana, offline chale")
    assert u["idea"]["twist"] == "offline_first" and "delivery_run" in u["idea"]["tabs"]
    assert (u["idea"]["goal"], u["idea"]["aud"]) in (("delivery_driver", "staff"), ("shop", "partner"))
    u = I.understand("kirana delivery boy app", goal="shop")
    assert u["idea"]["aud"] == "partner" and "delivery_run" in u["idea"]["screens_added"]
    # browse one business, page by page, no repeats
    b1 = I.browse("kirana", offset=0, limit=20)
    b2 = I.browse("kirana", offset=20, limit=20)
    assert b1["total"] == b2["total"] > 1000
    assert not {x["id"] for x in b1["items"]} & {x["id"] for x in b2["items"]}
    assert I.understand("")["idea"] is None


def test_idea_shapes_the_real_app_plan(env, monkeypatch):
    monkeypatch.setenv("APP_WORKER", "false")
    from app.appmaker import ideas as I
    from app.appmaker import service as S
    u = I.understand("kirana delivery boy app offline", goal="shop")
    v = S.new("default", "", idea=u["idea"]["id"])
    plan = S.get("default", v["number"])["plan"]
    ids = [x["id"] for x in plan["screens"]]
    assert "delivery_run" in ids and "sync_status" in ids
    assert plan["tabs"][0] == "delivery_run"
    assert plan["idea"]["id"] == u["idea"]["id"]
    import json
    assert "offline_db" in json.dumps(plan["blueprint"])
    assert "Idea:" in v["say"]
    # specific words pick the idea by themselves; plain words keep the plain plan + offer ideas
    v2 = S.new("default", "salon ki app, whatsapp se booking")
    assert v2["idea"]["twist"] == "whatsapp_first"
    v3 = S.new("default", "salon ki app")
    assert "idea" not in v3 and v3["other_ideas"] and v3["ideas_for_this_business"] > 100
    try:
        S.new("default", "", idea="nope")
        raise AssertionError("bad idea accepted")
    except S.AppError:
        pass


def test_api_and_tool(env, monkeypatch):
    import asyncio
    from app.agent.tools import HANDLERS, Ctx
    from app.main import app
    c = TestClient(app)
    h = {"X-API-Key": "test-key"} if False else {}
    r = c.get("/api/apps-ideas", params={"q": "tiffin service app subscription"}, headers=h)
    if r.status_code == 401:
        from app.config import get_settings
        h = {"X-Api-Key": get_settings().api_key}
        r = c.get("/api/apps-ideas", params={"q": "tiffin service app subscription"}, headers=h)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["all_ideas"] >= 1_00_00_000 and d["best"]["twist"] == "daily_subscription"
    one = c.get(f"/api/apps-ideas/{d['best']['id']}", headers=h)
    assert one.status_code == 200 and one.json()["id"] == d["best"]["id"]
    assert c.get("/api/apps-ideas/zz", headers=h).status_code == 404
    out = asyncio.run(HANDLERS["app_dekho"](Ctx("default", ""), what="ideas", q="gym app qr attendance"))
    assert out["best"]["id"].split(".")[3] == "qr_checkin" and out["all_ideas"] >= 1_00_00_000
