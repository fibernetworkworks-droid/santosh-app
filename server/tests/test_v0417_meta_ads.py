"""v0.417 META ADS (ad plan A1): Facebook Login instead of a pasted token, Facebook / Instagram ad drafts -> Meta check
-> created PAUSED on her tap -> Start only with a confirm, end time set so Meta itself stops it, auto-pause after the days."""
from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

T = "default"


@pytest.fixture()
def M(env, monkeypatch):
    from app.ads import metaads
    from app.ads import service as A
    from app.config import get_settings
    st = get_settings()
    monkeypatch.setattr(st, "meta_app_id", "123456")
    monkeypatch.setattr(st, "meta_app_secret", "s3cret")
    monkeypatch.setattr(st, "public_base_url", "https://hoola.example.com")
    metaads.ensure_tables()
    calls: list[tuple[str, str, dict]] = []

    def graph(method, path, token, params=None):
        p = dict(params or {})
        calls.append((method, path, p))
        if path == "oauth/access_token":
            return {"access_token": "EAAlong" + "x" * 40, "expires_in": 5184000} if p.get("grant_type") else {"access_token": "EAAshort"}
        if path == "me/permissions":
            return {"data": [{"permission": "ads_management", "status": "granted"}, {"permission": "ads_read", "status": "granted"}]}
        if path == "me/adaccounts":
            return {"data": [{"account_id": "998877", "name": "Asha Store", "currency": "INR", "account_status": 1},
                             {"account_id": "556677", "name": "Old closed", "currency": "INR", "account_status": 2}]}
        if path == "me/accounts":
            return {"data": [{"id": "5551112223", "name": "Asha Store Akola",
                              "instagram_business_account": {"id": "1784000111", "username": "ashastore"}}]}
        if path == "search":
            return {"data": [{"key": "1035921", "name": "Akola"}]} if "Akola" in p.get("q", "") else {"data": []}
        if path.endswith("/adimages"):
            return {"images": {"bytes": {"hash": "abc123hash"}}}
        if path.endswith("/campaigns"):
            return {"success": True} if "execution_options" in p else {"id": "120000001"}
        if path.endswith("/adsets"):
            return {"id": "120000002"}
        if path.endswith("/adcreatives"):
            return {"id": "120000003"}
        if path.endswith("/ads"):
            return {"id": "120000004"}
        return {"success": True}
    monkeypatch.setattr(A, "_graph", graph)
    metaads.calls = calls
    return metaads


def _link(M):
    url = M.connect_url(T)
    assert "redirect_uri=https%3A%2F%2Fhoola.example.com%2Fapi%2Fads%2Fmeta%2Fcallback" in url
    assert "ads_management" in url and "ads_read" in url
    state = url.split("state=")[1].split("&")[0]
    return M.finish_link("code1", state)


def _asset(tmp_path):
    from app.db import session
    from app.social.publish import SocialAsset
    f = tmp_path / "ad.jpg"
    f.write_bytes(b"\xff\xd8\xff" + b"0" * 200)
    with session() as s:
        a = SocialAsset(tenant_id=T, kind="image", path=str(f), width=1080, height=1080)
        s.add(a)
        s.flush()
        return a.id


def test_login_replaces_the_pasted_token(M):
    from app.ads import service as A
    v = _link(M)
    assert v["chosen"] and v["pages"] == ["Asha Store Akola"]
    st = A.settings(T)["meta"]
    assert st["ready"] and st["via"] == "login" and st["account"] == "act_998877" and st["currency"] == "INR"
    assert "EAAlong" not in json.dumps(st) and "EAAlong" not in json.dumps(M.view(T))   # sealed, never shown
    assert M.view(T)["account"]["page"] == "5551112223"
    with pytest.raises(M.MetaAdsError):
        M.choose(T, account="act_556677")                       # a closed account is refused
    with pytest.raises(M.MetaAdsError):                         # a state is used once
        M.finish_link("code1", "mad_nope")
    # the existing Ads desk works on this login unchanged: the token and account it reads are the same
    acct, tok = A._token(T)
    assert acct == "act_998877" and tok.startswith("EAAlong")


def test_draft_check_create_paused_start_needs_confirm(M, tmp_path):
    _link(M)
    d = M.new_draft(T, "whatsapp", text="Asha Store Akola: saree sale. WhatsApp par message kijiye.", headline="Saree sale",
                    cities=["Akola"], daily=400, days=3)
    assert d["page_id"] == "5551112223" and any("photo" in p for p in d["problems"])
    with pytest.raises(M.MetaAdsError):
        M.create(T, d["id"])                                     # problems block Create
    d = M.set_draft(T, d["id"], image_asset=_asset(tmp_path))
    assert d["problems"] == []
    posts_before = [c for c in M.calls if c[0] == "POST"]
    assert not posts_before                                      # a draft never reaches Meta
    c = M.check(T, d["id"])
    assert c["status"] == "checked"
    chk = [x for x in M.calls if x[1].endswith("/campaigns")][-1]
    assert json.loads(chk[2]["execution_options"]) == ["validate_only"]
    r = M.create(T, d["id"])
    assert r["status"] == "created" and r["campaign_id"] == "120000001" and r["ad_id"] == "120000004"
    made = {x[1].split("/")[-1]: x[2] for x in M.calls if x[0] == "POST" and x[1].startswith("act_")}
    assert made["campaigns"]["status"] == "PAUSED" and made["ads"]["status"] == "PAUSED" and made["adsets"]["status"] == "PAUSED"
    assert json.loads(made["campaigns"]["special_ad_categories"]) == []
    assert made["campaigns"]["objective"] == "OUTCOME_ENGAGEMENT"
    assert made["adsets"]["destination_type"] == "WHATSAPP" and made["adsets"]["daily_budget"] == 40000     # paise
    tg = json.loads(made["adsets"]["targeting"])
    assert tg["geo_locations"]["cities"][0] == {"key": "1035921", "radius": 25, "distance_unit": "kilometer"}
    spec = json.loads(made["adcreatives"]["object_story_spec"])
    assert spec["link_data"]["call_to_action"] == {"type": "WHATSAPP_MESSAGE", "value": {"app_destination": "WHATSAPP"}}
    assert spec["link_data"]["image_hash"] == "abc123hash" and spec["instagram_user_id"] == "1784000111"
    with pytest.raises(M.MetaAdsError):
        M.set_draft(T, d["id"], text="x")                        # made in Meta: edits go to Ads Manager
    n = len(M.calls)
    with pytest.raises(M.MetaAdsError):
        M.start(T, d["id"])                                      # no confirm = nothing sent
    assert len(M.calls) == n
    s = M.start(T, d["id"], confirm=True)
    assert s["status"] == "running" and s["stop_on"]
    tail = M.calls[n:]
    assert "end_time" in tail[0][2] and tail[0][1] == "120000002"            # Meta itself stops it after her days
    assert [x[1] for x in tail[1:]] == ["120000004", "120000002", "120000001"]   # the campaign goes live last
    assert all(x[2] == {"status": "ACTIVE"} for x in tail[1:])


def test_money_ads_refused_and_cap(M):
    _link(M)
    d = M.new_draft(T, "website", text="Guaranteed returns on your mutual fund investment", link="https://asha.in",
                    daily=99999)
    probs = " ".join(d["problems"])
    assert "Hoola aisa ad nahi banata" in probs and "SEBI" in probs and "seema" in probs


def test_failed_half_build_is_named(M, tmp_path, monkeypatch):
    from app.ads import service as A
    _link(M)
    d = M.new_draft(T, "messenger", text="Message us", image_asset=_asset(tmp_path))
    real = A._graph

    def boom(method, path, token, params=None):
        if path.endswith("/adsets"):
            raise A.AdsError("Meta: Invalid parameter")
        return real(method, path, token, params)
    monkeypatch.setattr(A, "_graph", boom)
    with pytest.raises(M.MetaAdsError) as e:
        M.create(T, d["id"])
    assert "PAUSED campaign" in str(e.value)
    v = [x for x in M.drafts(T) if x["id"] == d["id"]][0]
    assert v["status"] == "failed" and v["campaign_id"] == "120000001"


def test_boost_and_daily_watch(M, monkeypatch):
    from app.ads.metaads import MetaAdDraft
    from app.db import session
    _link(M)
    d = M.new_draft(T, "boost", post_id="9876543210", daily=200, days=2)
    assert d["post_id"] == "5551112223_9876543210" and d["problems"] == []
    r = M.create(T, d["id"])
    cr = [x for x in M.calls if x[1].endswith("/adcreatives")][-1][2]
    assert cr["object_story_id"] == "5551112223_9876543210"
    assert not [x for x in M.calls if x[1].endswith("/adimages")]
    with session() as s:
        row = s.get(MetaAdDraft, r["id"])
        row.status, row.stop_on = "running", (date.today() - timedelta(days=3)).isoformat()
    out = M.daily_watch(T)
    assert out["ended"] == 1 and M.drafts(T)[0]["status"] == "ended"
    assert M.calls[-1] == ("POST", "120000001", {"status": "PAUSED"})


def test_api_and_tool(M):
    from fastapi.testclient import TestClient

    from app import main
    with TestClient(main.app) as c:
        assert c.get("/api/ads/metaads").json()["account"] is None
        url = c.get("/api/ads/meta/connect").json()["url"]
        state = url.split("state=")[1].split("&")[0]
        page = c.get(f"/api/ads/meta/callback?code=abc&state={state}")
        assert page.status_code == 200 and "Asha Store" in page.text
        v = c.get("/api/ads/metaads").json()
        assert v["account"]["account"] == "act_998877" and v["account"]["via"] == "login"
        did = c.post("/api/ads/metaads/drafts", json={"goal": "whatsapp", "text": "Hi"}).json()["id"]
        assert c.post(f"/api/ads/metaads/drafts/{did}/create").status_code == 400          # photo missing
        assert c.post(f"/api/ads/metaads/drafts/{did}/start", json={}).status_code == 400
        assert c.post(f"/api/ads/metaads/drafts/{did}/burn").status_code == 404
        bad = c.get("/api/ads/meta/callback?code=abc&state=mad_old")
        assert bad.status_code == 400
    from app.agent import ads_tools
    names = [t["name"] for t in ads_tools.ADS_TOOLS]
    assert "ads" in names
    acts = ads_tools.ADS_TOOLS[0]["input_schema"]["properties"]["action"]["enum"]
    assert "meta_draft" in acts and "meta_draft" in ads_tools._OWNER_ONLY
