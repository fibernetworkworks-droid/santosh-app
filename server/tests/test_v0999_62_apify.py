"""v0.999.62 APIFY LANE - Apify scrapers as a leads source on her token, offline (httpx.MockTransport)."""
import asyncio
import json

import httpx
import pytest

from tests.test_bazar import bz  # noqa: F401

from app.leads import apify as AP
from app.leads import rules as R
from app.leads import service as S

T = "apify-tenant"
SEEN = []


def _env(monkeypatch, token="tok_secret_123", ack="apify"):
    monkeypatch.setenv("APIFY_TOKEN", token)
    monkeypatch.setenv("APIFY_TERMS_ACK", ack)
    monkeypatch.setenv("APIFY_MAX_USD_PER_RUN", "3")
    from app.config import get_settings
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _clean(env):
    SEEN.clear()
    yield
    AP._transport = None
    from app.config import get_settings
    get_settings.cache_clear()


IG_ITEMS = [
    {"username": "puneBakes", "fullName": "Pune Bakes", "isBusinessAccount": True, "businessCategoryName": "Bakery",
     "businessPhoneNumber": "+91 98220 12345", "externalUrl": "https://punebakes.in", "followersCount": 4200},
    {"username": "riya.personal", "fullName": "Riya", "isBusinessAccount": False, "followersCount": 300},
    {"username": "secretcakes", "fullName": "Secret", "isPrivate": True, "isBusinessAccount": True},
    {"username": "cakehouse", "fullName": "Cake House", "publicEmail": "hi@cakehouse.in"},
]


def _mock(items=IG_ITEMS, status="SUCCEEDED", usd=0.42, start_status=201):
    def handler(req: httpx.Request):
        SEEN.append((req.method, req.url.path, dict(req.url.params), req.headers.get("authorization"),
                     req.content.decode() if req.content else ""))
        if req.method == "POST" and req.url.path.endswith("/runs"):
            return httpx.Response(start_status, json={"data": {"id": "run1", "defaultDatasetId": "ds1",
                                                               "status": "RUNNING"}})
        if req.url.path.endswith("/actor-runs/run1"):
            return httpx.Response(200, json={"data": {"id": "run1", "status": status, "usageTotalUsd": usd,
                                                      "defaultDatasetId": "ds1"}})
        if req.url.path.endswith("/datasets/ds1/items"):
            return httpx.Response(200, json=items)
        return httpx.Response(404, json={})
    AP._transport = httpx.MockTransport(handler)


def test_rule_text_moved_in_claude_md():
    from pathlib import Path
    flat = " ".join((Path(__file__).resolve().parents[2] / "CLAUDE.md").read_text().split())
    assert "AMENDED BY THE OWNER'S EXPLICIT ASK of 20 Nov 2026" in flat and "business profiles only" in flat
    assert "APIFY" in R.LANES and R.LANE_BUILT["APIFY"] == "P6" and "profile_url" in R.KEY_TYPES


def test_gate_refuses_until_token_terms_and_her_optin(monkeypatch):
    _env(monkeypatch, token="")
    with pytest.raises(S.LeadsError, match="APIFY_TOKEN"):
        asyncio.run(S.run_apify(T, "bakeries", "instagram", "bakery", "Pune"))
    _env(monkeypatch, ack="")
    with pytest.raises(S.LeadsError, match="APIFY_TERMS_ACK"):
        asyncio.run(S.run_apify(T, "bakeries", "instagram", "bakery", "Pune"))
    _env(monkeypatch)
    with pytest.raises(S.LeadsError, match="OFF"):
        asyncio.run(S.run_apify(T, "bakeries", "instagram", "bakery", "Pune"))
    assert SEEN == []          # not a single Apify call before the gate opens


def test_login_inputs_refused(monkeypatch):
    _env(monkeypatch)
    monkeypatch.setenv("APIFY_ACTOR_LINKEDIN", "someone/linkedin-people")
    monkeypatch.setenv("APIFY_INPUT_LINKEDIN", json.dumps({"query": "{query}", "cookie": "li_at=xyz"}))
    from app.config import get_settings
    get_settings.cache_clear()
    with pytest.raises(AP.ApifyError, match="never gives a scraper a login"):
        AP.build_input(AP.platform("linkedin"), "dentists", "Pune", [], 10)


def test_instagram_run_keeps_business_refuses_personal_and_private(monkeypatch):
    _env(monkeypatch)
    S.set_apify_optin(T, True)
    _mock()
    out = asyncio.run(S.run_apify(T, "bakeries in Pune", "instagram", "bakery", "Pune", max_rows=50))
    assert out["ok"] and out["kept"] == 2 and out["refused"] == 2
    assert out["refused_because"] == {"personal profile (no business signal)": 1, "private account": 1}
    assert out["cost"]["usd"] == 0.42
    post = [x for x in SEEN if x[0] == "POST"][0]
    assert post[1] == "/v2/acts/apify~instagram-scraper/runs" and post[2]["maxTotalChargeUsd"] == "3.0"
    assert post[3] == "Bearer tok_secret_123" and "tok_secret_123" not in post[1] + json.dumps(post[2])
    body = json.loads(post[4])
    assert body["search"] == "bakery Pune" and body["searchType"] == "user"
    rows = S.rows(T)
    items = rows["rows"] if isinstance(rows, dict) else rows
    names = {r["name"] for r in items}
    assert names == {"Pune Bakes", "Cake House"}
    pb = next(r for r in items if r["name"] == "Pune Bakes")
    assert pb["source_lane"] == "APIFY" and pb["source_url"] == "https://www.instagram.com/puneBakes/"
    assert pb["socials"]["instagram_followers"] == 4200 and pb["phone"]
    again = asyncio.run(S.run_apify(T, "again", "instagram", "bakery", "Pune", max_rows=50))
    assert again["kept"] == 0                                    # same profiles = duplicates


def test_long_run_pauses_then_collects(monkeypatch):
    _env(monkeypatch)
    S.set_apify_optin(T, True)
    _mock(status="RUNNING")
    out = asyncio.run(S.run_apify(T, "pages", "facebook", urls=["https://www.facebook.com/punebakes"], wait_s=0))
    assert out["still_running"] and out["run"]["status"] == "PAUSED"
    rid = out["run"]["id"]
    _mock(items=[{"title": "Pune Bakes", "pageUrl": "https://www.facebook.com/punebakes",
                  "phone": "+91 98220 12345", "categories": ["Bakery"]}])
    done = asyncio.run(S.apify_collect(T, rid, wait_s=0))
    assert done["ok"] and done["kept"] == 1 and S.run_card(rid)["status"] == "DONE"


def test_facebook_needs_links_and_maps_needs_query(monkeypatch):
    _env(monkeypatch)
    with pytest.raises(AP.ApifyError, match="needs links"):
        AP.build_input(AP.platform("facebook"), "bakery", "Pune", [], 10)
    inp = AP.build_input(AP.platform("maps"), "dentist", "Pune", [], 20)
    assert inp["searchStringsArray"] == ["dentist"] and inp["locationQuery"] == "Pune"
    assert inp["maxCrawledPlacesPerSearch"] == 20


def test_out_of_credit_is_said(monkeypatch):
    _env(monkeypatch)
    S.set_apify_optin(T, True)
    _mock(start_status=402)
    out = asyncio.run(S.run_apify(T, "x", "tiktok", "bakery", "Pune"))
    assert out["ok"] is False and "out of credit" in out["error"]
    assert len([x for x in SEEN if x[0] == "POST"]) == 1        # never retried


def test_tool_actions_wired():
    from app.agent.tools import TOOLS
    spec = next(t for t in TOOLS if t["name"] == "leads_run")
    enum = spec["input_schema"]["properties"]["action"]["enum"]
    assert {"apify", "apify_optin", "apify_collect"} <= set(enum)
