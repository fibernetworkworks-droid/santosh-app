"""v0.470 Phase 11 PROOF - the MAPS card.

The card's own honesty is what these tests pin: the geo answer key is COMPUTED from the ask's own coordinates (the set
stores no answer, so no remembered world fact can leak in), a wrong name / wrong order / an outside-radius name fails,
every maps tool in the registry is on the card's list (a new tool cannot quietly go unmeasured), the guards are really
checked (the cap one by running it), and the live row reads the RUPEES that ask actually spent.
"""
from __future__ import annotations

import asyncio

import pytest

from app.quality import mapscard as M
from app.quality.maps_asks import ASKS


def _ask(i: str) -> dict:
    return next(a for a in ASKS if a["id"] == i)


def test_the_set_stores_no_answer_at_all(env):
    """A geo row carries coordinates and nothing else: the key cannot be a number somebody typed from memory."""
    for a in ASKS:
        assert not ({"want", "answer", "expect", "km_want"} & set(a)), f"{a['id']} carries an answer"
    assert {a["kind"] for a in ASKS} == {"geo", "tool", "rule"}


def test_the_key_is_computed_with_the_servers_own_haversine(env):
    from app import maps
    a = _ask("geo_nearest_of_four")
    key = M.key_for(a)
    best = min(a["points"], key=lambda p: maps._km(a["from"], p))
    assert key["want"] == [best["name"]] and key["not"] and len(key["km"]) == 4
    assert M.key_for(_ask("geo_within_radius"))["want"] == ["Godown A", "Godown B"]
    assert M.key_for(_ask("geo_order_of_three"))["order"] == ["Godown B", "Godown D", "Godown C"]
    assert M.key_for(_ask("geo_straight_km"))["km_want"] == round(maps._km(a["from"], _ask("geo_straight_km")["points"][0]), 1)


def test_geo_scoring_passes_the_right_answer_and_fails_the_wrong_one(env):
    n = _ask("geo_nearest_of_four")
    assert M._score_geo(n, "Godown A sabse paas hai, 7 km.")["right"]
    assert not M._score_geo(n, "Godown C sabse paas hai.")["right"]
    w = _ask("geo_within_radius")
    assert M._score_geo(w, "Godown A aur Godown B andar aati hain.")["right"]
    bad = M._score_geo(w, "Godown A, Godown B aur Godown D.")
    assert not bad["right"] and "Godown D" in bad["misses"][0]
    o = _ask("geo_order_of_three")
    assert M._score_geo(o, "Godown B, then Godown D, then Godown C")["right"]
    assert not M._score_geo(o, "Godown C, Godown D, Godown B")["right"]
    k = _ask("geo_straight_km")
    want = M.key_for(k)["km_want"]
    assert M._score_geo(k, f"Takriban {want} km")["right"]
    assert M._score_geo(k, f"About {want * 1.02:.0f} km")["right"], "3% tolerance"
    assert not M._score_geo(k, f"About {want * 0.7:.0f} km")["right"]


def test_every_registered_maps_tool_is_on_the_card(env):
    """The card must drift with the code: a new maps tool that nobody measures is exactly what this catches."""
    from app.agent.maps_tools import MAPS_HANDLERS
    assert set(M.MAPS_TOOLS) == set(MAPS_HANDLERS), "MAPS_TOOLS and the real handler table disagree"
    assert len(M.MAPS_TOOLS) == 20


def test_the_free_card_measures_in_view_registered_reachable_and_guards(env):
    c = M.free_card()
    assert c["asks"] == len(ASKS) and c["right_in_view"] == c["asks"] and c["wrong_loaded"] == 0
    assert c["not_registered"] == [] and c["registered"] == c["tools"]
    assert c["unreachable"] == [], "a tool no ask can reach is unmeasured"
    assert c["guards_ok"] == len(c["guards"]) == 5, c["guards"]
    assert c["inr_all_asks"] > 0 and c["dearest"][0]["inr"] >= c["dearest"][-1]["inr"]
    assert "\n".join(M.lines(c)).startswith("Maps card (free")


def test_the_cap_guard_is_proved_by_running_it_not_by_reading_it(env):
    from app import mapsbill
    assert M._cap_fires() is True
    # and it really refused rather than spending: the refusal is visible, the money is not
    u = mapsbill.usage("__mapscard__")
    assert u["refused"] >= 1 and u["inr"] == 0


def test_a_price_comes_from_mapsbill_never_from_a_number_here(env, monkeypatch):
    from app import mapsbill
    one = M.price_of("maps_address_check")
    assert one["skus"] == [mapsbill.SKU_ADDRESS_ENT] and one["inr"] == round(mapsbill.price_inr(mapsbill.SKU_ADDRESS_ENT), 4)
    assert one["assumed"] == [mapsbill.SKU_ADDRESS_ENT], "the tier is a guess and the card says so"
    assert M.price_of("maps_kharcha")["inr"] == 0 and M.price_of("gbp_locations")["inr"] == 0
    # the matrix is billed per element, so the nearest-of-N answer must cost more than one request
    assert M.price_of("maps_nearest")["inr"] > M.price_of("maps_pata")["inr"]
    monkeypatch.setenv("MAPS_PRICE_LIST", "global")
    from app.config import get_settings
    get_settings.cache_clear()
    assert M.price_of("maps_address_check")["inr"] > one["inr"], "the global list is dearer; the card follows mapsbill"


def test_rule_scoring_reads_the_reply_for_each_guard(env):
    r = M._score_rule(_ask("rule_lead_list"), "Yeh list nahi de sakta - Google ke terms is tarah ki list banane se mana karte hain.", [])
    assert r["right"]
    assert not M._score_rule(_ask("rule_lead_list"), "Ji, 200 shops ki Excel bana di.", [])["right"]
    assert M._score_rule(_ask("rule_map_picture"), "Map ka link daal diya: https://www.google.com/maps/search/?api=1&query=x", [])["right"]
    assert not M._score_rule(_ask("rule_map_picture"), "Screenshot PDF mein chipka diya.", [])["right"]
    assert M._score_rule(_ask("rule_plan_only"), "Kram taiyaar hai - assign nahi kiya, aapki haan ke baad.", [])["right"]
    assert not M._score_rule(_ask("rule_plan_only"), "Driver ko assign kar diya.", [])["right"]
    assert M._score_rule(_ask("rule_solar_unknown"), "Google ke paas is chhat ka data nahi hai.", ["solar_check"])["right"]
    assert not M._score_rule(_ask("rule_solar_unknown"), "Takriban 18 panel lag jaayenge.", [])["right"]


def test_a_live_row_carries_the_rupees_that_ask_spent(env, monkeypatch):
    """The point of Phase 11: every answer's own cost, read from mapsbill around the real turn."""
    from app import mapsbill
    from app.agent import santosh
    from app.quality import run as R

    async def fake_turn(conv, text, tenant_id="", **kw):
        mapsbill.charge(tenant_id, mapsbill.SKU_NEARBY_PRO, 1)      # the turn spends, like a real maps answer
        return "Sai Medical 1.2 km par hai."
    monkeypatch.setattr(santosh, "run_turn", fake_turn)
    monkeypatch.setattr(R, "_calls_of", lambda conv: [{"tool": "maps_nearby"}])
    monkeypatch.setitem(mapsbill._FREE_INDIA, mapsbill.SKU_NEARBY_PRO, 0)   # past the free allowance: real rupees
    row = asyncio.run(M._one(_ask("tool_category_near"), R.TENANT))
    assert row["right"] and row["maps_tools"] == ["maps_nearby"]
    assert row["inr"] == round(mapsbill.price_inr(mapsbill.SKU_NEARBY_PRO, 1), 4) > 0
    card = asyncio.run(M.live_card([_ask("tool_category_near")], tenant=R.TENANT))
    assert card["right"] == 1 and card["tool_right"] == 1 and card["inr"] > 0 and card["inr_per_answer"] > 0
    assert "RIGHT 1/1" in M.lines(card)[0] and "Rs" in M.lines(card)[0]


def test_a_dead_turn_is_an_error_row_with_its_cost_never_a_pass(env, monkeypatch):
    from app.agent import santosh

    async def boom(conv, text, tenant_id="", **kw):
        raise RuntimeError("model refused")
    monkeypatch.setattr(santosh, "run_turn", boom)
    card = asyncio.run(M.live_card(M.pick(limit=3), tenant="__quality__"))
    assert card["errors"] == 3 and card["right"] == 0 and card["answered"] == 0
    assert all("error" in r for r in card["rows"])
    assert "ERROR" in "\n".join(M.lines(card))


def test_pick_save_and_the_route(env):
    assert [a["id"] for a in M.pick(kind="rule")] == [a["id"] for a in ASKS if a["kind"] == "rule"]
    assert len(M.pick(limit=2)) == 2 and M.pick(only="tool_cost")[0]["id"] == "tool_cost"
    card = M.save(M.free_card(M.pick(limit=2)), "test")
    assert card["file"].startswith("mapscard-free-") and any(c["file"] == card["file"] for c in M.saved())
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.quality.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None))
    body = TestClient(app).get("/api/quality/maps").json()
    assert body["free"]["asks"] == len(ASKS) and body["lines"] and body["cards"]
