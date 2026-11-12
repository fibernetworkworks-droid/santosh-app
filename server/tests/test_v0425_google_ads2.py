"""v0.425 GOOGLE ADS 2 (ad plan A2): Search + Performance Max on the same Google Ads link as the YouTube ads - drafts in
Hoola, Keyword Planner ideas for her places, Google check (validateOnly), Create PAUSED, Start only on her confirm, the read
covers every campaign type and Search's search terms reach the Ads desk. Google is a mock transport."""
import io
import json
from urllib.parse import urlparse

import httpx
import pytest

from tests import test_v0401_youtube_ads as Y
from tests.test_v0353_social_manager import social  # noqa: F401  (the shared fixture)

T = "default"


def handler(req: httpx.Request) -> httpx.Response:
    path = urlparse(str(req.url)).path
    if path.endswith("geoTargetConstants:suggest"):
        names = json.loads(req.content)["locationNames"]["names"]
        Y.CALLS.append(("geo", names))
        known = {"Akola": "1007768", "Pune": "1007788"}
        return httpx.Response(200, json={"geoTargetConstantSuggestions": [
            {"searchTerm": n, "geoTargetConstant": {"resourceName": f"geoTargetConstants/{known[n]}", "name": n, "status": "ENABLED",
                                                     "targetType": "City"}} for n in names if n in known]})
    if path.endswith(":generateKeywordIdeas"):
        body = json.loads(req.content)
        Y.CALLS.append(("ideas", body))
        return httpx.Response(200, json={"results": [
            {"text": "dental implants akola", "keywordIdeaMetrics": {"avgMonthlySearches": "320", "competition": "MEDIUM",
                                                                     "lowTopOfPageBidMicros": "12000000", "highTopOfPageBidMicros": "45000000"}},
            {"text": "braces cost", "keywordIdeaMetrics": {"avgMonthlySearches": "2900", "competition": "HIGH"}}]})
    if path.endswith("/googleAds:search") and "search_term_view" in json.loads(req.content)["query"]:
        Y.CALLS.append(("terms", json.loads(req.content)["query"]))
        return httpx.Response(200, json={"results": [
            {"searchTermView": {"searchTerm": "free dental checkup"}, "campaign": {"name": "Implants Search"},
             "adGroup": {"name": "Implants"}, "metrics": {"costMicros": "900000000", "impressions": "800", "clicks": "40", "conversions": 0}},
            {"searchTermView": {"searchTerm": "dental implants akola"}, "campaign": {"name": "Implants Search"},
             "adGroup": {"name": "Implants"}, "metrics": {"costMicros": "600000000", "impressions": "500", "clicks": "30", "conversions": 5}}]})
    if path.endswith("/googleAds:search") and "FROM campaign" in json.loads(req.content)["query"] and not Y.STATE.get("not_approved"):
        q = json.loads(req.content)["query"]
        if "video_trueview_views" not in q:
            Y.CALLS.append(("search", q))
            rows = []
            for day in ("2026-10-30", "2026-10-31"):
                rows.append({"segments": {"date": day}, "campaign": {"id": "7", "name": "Implants Search", "status": "ENABLED",
                                                                    "advertisingChannelType": "SEARCH"},
                             "campaignBudget": {"amountMicros": "800000000"},
                             "metrics": {"costMicros": "750000000", "impressions": "2000", "clicks": "70", "conversions": 3}})
            return httpx.Response(200, json={"results": rows})
    return Y.ads_handler(req)


@pytest.fixture
def g2(social, monkeypatch, tmp_path):  # noqa: F811
    gen = Y.ga.__wrapped__(social, monkeypatch, tmp_path)
    D, G = next(gen)
    G.set_http(httpx.Client(transport=httpx.MockTransport(handler)))
    Y._connect(D, G)
    G.choose(T, "1112223333")
    yield D, G
    try:
        next(gen)
    except StopIteration:
        pass


def _photo(w=1600, h=900):
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (w, h), (200, 120, 40)).save(b, "JPEG")
    return b.getvalue()


def _mutates():
    return [c[1] for c in Y.CALLS if c[0] == "mutate"]


def test_search_draft_ideas_check_create_paused_start(g2):
    D, G = g2
    d = G.new_draft(T, kind="search")
    assert d["kind"] == "search" and d["cities"] == ["Akola"] and len(d["headlines"]) >= 3 and d["keywords"]
    assert all(len(h) <= 30 for h in d["headlines"]) and d["final_url"] == "https://sharmadental.example"
    ideas = G.keyword_ideas(T, ["dental implants"], cities=["Akola"])
    assert ideas["ideas"][0]["text"] == "braces cost" and ideas["ideas"][1]["low"] == 12.0 and ideas["currency"] == "INR"
    sent = [c[1] for c in Y.CALLS if c[0] == "ideas"][-1]
    assert sent["geoTargetConstants"] == ["geoTargetConstants/1007768"] and sent["keywordSeed"]["keywords"] == ["dental implants"]
    G.set_draft(T, d["id"], keywords=["dental implants akola", "braces akola"], negatives=["free"], paths=["implants", "akola"])
    assert not [c for c in Y.CALLS if c[0] == "mutate"]                      # nothing reaches Google from a draft
    G.check(T, d["id"])
    chk = _mutates()[-1]
    assert chk["validateOnly"] is True
    G.create(T, d["id"])
    ops = _mutates()[-1]["mutateOperations"]
    camp = next(o["campaignOperation"]["create"] for o in ops if "campaignOperation" in o)
    assert camp["advertisingChannelType"] == "SEARCH" and camp["status"] == "PAUSED" and "targetSpend" in camp
    assert camp["networkSettings"]["targetContentNetwork"] is False
    crit = [o["campaignCriterionOperation"]["create"] for o in ops if "campaignCriterionOperation" in o]
    assert {"geoTargetConstant": "geoTargetConstants/1007768"} in [c.get("location") for c in crit]
    assert any(c.get("negative") and c["keyword"]["text"] == "free" for c in crit)
    kws = [o["adGroupCriterionOperation"]["create"]["keyword"] for o in ops if "adGroupCriterionOperation" in o]
    assert {"text": "braces akola", "matchType": "PHRASE"} in kws
    grp = next(o["adGroupOperation"]["create"] for o in ops if "adGroupOperation" in o)
    assert grp["type"] == "SEARCH_STANDARD"
    rsa = next(o["adGroupAdOperation"]["create"]["ad"] for o in ops if "adGroupAdOperation" in o)
    assert rsa["responsiveSearchAd"]["path1"] == "implants" and rsa["finalUrls"] == ["https://sharmadental.example"]
    with pytest.raises(G.GAdsError):
        G.start(T, d["id"])                                                    # money only with her confirm
    v = G.start(T, d["id"], confirm=True)
    assert v["status"] == "running" and v["kind_label"] == "Search ad"


def test_search_limits_and_unknown_city(g2):
    D, G = g2
    d = G.new_draft(T, kind="search")
    v = G.set_draft(T, d["id"], headlines=["Only one headline that is far too long for google search"], keywords=[])
    probs = " ".join(v["problems"])
    assert "3 to 15 headlines" in probs and "30 characters" in probs and "keywords" in probs
    G.set_draft(T, d["id"], headlines=["Sharma Dental", "Implants Akola", "Braces Akola"], keywords=["implants"],
                cities=["Atlantis"])
    with pytest.raises(G.GAdsError) as e:
        G.check(T, d["id"])
    assert "Atlantis" in str(e.value)


def test_pmax_crops_photos_and_builds_one_asset_group(g2):
    from PIL import Image

    from app.social import publish as SP
    D, G = g2
    d = G.new_draft(T, kind="pmax")
    assert any("picture" in p for p in d["problems"]) and any("logo" in p for p in d["problems"])
    logo = SP.add_asset(T, Y._png(), "logo.png")
    pic = SP.add_asset(T, _photo(), "shop.jpg")
    v = G.set_draft(T, d["id"], logo_asset=logo["id"], images=[pic["id"]],
                    descriptions=["Implants, braces and smile makeovers in Akola by Dr Sharma.", "Book a visit today."])
    assert v["problems"] == [], v["problems"]
    G.create(T, d["id"])
    ops = _mutates()[-1]["mutateOperations"]
    camp = next(o["campaignOperation"]["create"] for o in ops if "campaignOperation" in o)
    assert camp["advertisingChannelType"] == "PERFORMANCE_MAX" and camp["status"] == "PAUSED" and "maximizeConversions" in camp
    assert sum(1 for o in ops if "assetGroupOperation" in o) == 1
    fields = [o["assetGroupAssetOperation"]["create"]["fieldType"] for o in ops if "assetGroupAssetOperation" in o]
    for f in ("HEADLINE", "LONG_HEADLINE", "DESCRIPTION", "BUSINESS_NAME", "LOGO", "MARKETING_IMAGE", "SQUARE_MARKETING_IMAGE"):
        assert f in fields
    imgs = {}
    for o in ops:
        a = (o.get("assetOperation") or {}).get("create") or {}
        if "imageAsset" in a:
            import base64
            imgs[a["name"].split(" ")[3] if "photo" in a["name"] else "logo"] = Image.open(io.BytesIO(base64.b64decode(a["imageAsset"]["data"]))).size
    assert imgs["wide"] == (1200, 628) and imgs["square"] == (1200, 1200)
    # every asset op comes before the asset group asset op that links it (Google's order)
    seen = set()
    for o in ops:
        if "assetOperation" in o:
            seen.add(o["assetOperation"]["create"]["resourceName"])
        if "assetGroupAssetOperation" in o:
            assert o["assetGroupAssetOperation"]["create"]["asset"] in seen


def test_read_every_type_and_search_terms_reach_the_ads_desk(g2):
    from app.ads import service as A
    D, G = g2
    r = G.read(T)
    q = [c[1] for c in Y.CALLS if c[0] == "search"][-1]
    assert "'SEARCH'" in q and "'PERFORMANCE_MAX'" in q and "REMOVED" in q
    assert r["campaigns"][0]["name"] == "Implants Search" and r["terms"] == 2
    rep = A.analyse(T, days=30, platform="google")
    assert not rep.get("empty")
    with A.session() as s:
        terms = s.scalars(A.select(A.AdsRow).where(A.AdsRow.tenant_id == T, A.AdsRow.kind == "term")).all()
        assert {t.term for t in terms} == {"free dental checkup", "dental implants akola"}


def test_routes_and_tool(g2):
    from fastapi.testclient import TestClient

    from app import main
    from app.agent import ads_tools
    D, G = g2
    with TestClient(main.app) as c:
        did = c.post("/api/social/ytads/drafts", json={"kind": "search"}).json()["id"]
        assert c.get("/api/social/ytads").json()["kinds"]["pmax"] == "Performance Max"
        r = c.post("/api/social/ytads/ideas", json={"seeds": ["braces"], "cities": ["Pune"]}).json()
        assert r["ideas"]
        assert c.post(f"/api/social/ytads/drafts/{did}/start", json={}).status_code == 400
    acts = ads_tools.ADS_TOOLS[0]["input_schema"]["properties"]["action"]["enum"]
    assert "google_draft" in acts and "google_ideas" in acts and "google_draft" in ads_tools._OWNER_ONLY
