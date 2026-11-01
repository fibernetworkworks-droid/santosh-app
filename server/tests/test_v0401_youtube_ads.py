"""v0.401 YOUTUBE ADS (plan Y2): her own Google Ads account through the official Google Ads API (v26 REST). Connect (adwords
sign-in, sealed), pick the ad account, read YouTube campaigns into the Ads desk, shape a Demand Gen video ad from her own
video in Hoola, Google checks it for free (validateOnly), Create = PAUSED in her account, Start only with her confirm,
Pause any time, an ad past its days paused by Hoola. Google is a mock transport."""
import base64
import io
import json
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

from tests import test_v0353_social_manager as P1
from tests.test_v0353_social_manager import social  # noqa: F401  (the shared fixture)

T = "default"
CALLS: list[tuple[str, object]] = []
STATE: dict = {}


def google_handler(req: httpx.Request) -> httpx.Response:
    u = str(req.url)
    if u.startswith("https://oauth2.googleapis.com/token"):
        f = parse_qs(req.content.decode())
        if f.get("grant_type") == ["refresh_token"]:
            return httpx.Response(200, json={"access_token": "GA_ACCESS2", "expires_in": 3600})
        return httpx.Response(200, json={"access_token": "GA_ACCESS", "refresh_token": "GA_REFRESH", "expires_in": 3600,
                                         "scope": "openid email https://www.googleapis.com/auth/adwords"})
    if u.startswith("https://openidconnect.googleapis.com/v1/userinfo"):
        return httpx.Response(200, json={"email": "meghana@example.in"})
    return httpx.Response(404, json={"error": "unhandled " + u})


def ads_handler(req: httpx.Request) -> httpx.Response:
    u = str(req.url)
    path = urlparse(u).path
    assert req.headers.get("developer-token") == STATE.get("devtoken", "DEVTOKEN") and req.headers.get("authorization", "").startswith("Bearer GA_ACCESS")
    if path == "/v26/customers:listAccessibleCustomers":
        return httpx.Response(200, json={"resourceNames": ["customers/1112223333", "customers/9998887777"]})
    if path.endswith("/googleAds:search"):
        q = json.loads(req.content)["query"]
        cid = path.split("/")[3]
        if "FROM customer" in q:
            mgr = cid == "9998887777"
            return httpx.Response(200, json={"results": [{"customer": {"id": cid, "descriptiveName": "MCC" if mgr else "Sharma Dental Ads",
                                                                       "currencyCode": "INR", "manager": mgr, "testAccount": False}}]})
        if STATE.get("not_approved"):
            return httpx.Response(403, json={"error": {"code": 403, "message": "The caller does not have permission", "details": [
                {"errors": [{"errorCode": {"authorizationError": "DEVELOPER_TOKEN_NOT_APPROVED"},
                             "message": "The developer token is only approved for use with test accounts."}]}]}})
        if "video_trueview_views" in q:
            return httpx.Response(400, json={"error": {"code": 400, "message": "Request contains an invalid argument.", "details": [
                {"errors": [{"errorCode": {"queryError": "UNRECOGNIZED_FIELD"}, "message": "Unrecognized field in the query: 'metrics.video_trueview_views'."}]}]}})
        CALLS.append(("search", q))
        return httpx.Response(200, json={"results": [
            {"segments": {"date": "2026-10-30"}, "campaign": {"id": "1", "name": "Diwali Shorts", "status": "ENABLED",
                                                             "advertisingChannelType": "DEMAND_GEN"},
             "campaignBudget": {"amountMicros": "500000000"}, "metrics": {"costMicros": "450000000", "impressions": "12000",
                                                                         "clicks": "90", "conversions": 4, "videoViews": "3000"}},
            {"segments": {"date": "2026-10-31"}, "campaign": {"id": "1", "name": "Diwali Shorts", "status": "ENABLED",
                                                             "advertisingChannelType": "DEMAND_GEN"},
             "campaignBudget": {"amountMicros": "500000000"}, "metrics": {"costMicros": "500000000", "impressions": "15000",
                                                                         "clicks": "110", "conversions": 6, "videoViews": "3500"}}]})
    if path.endswith("/googleAds:mutate"):
        body = json.loads(req.content)
        CALLS.append(("mutate", body))
        if body.get("validateOnly"):
            return httpx.Response(200, json={})
        out = []
        for op in body["mutateOperations"]:
            k = next(iter(op))
            if k == "campaignOperation" and "create" in op[k]:
                out.append({"campaignResult": {"resourceName": "customers/1112223333/campaigns/555"}})
            else:
                out.append({})
        return httpx.Response(200, json={"mutateOperationResponses": out})
    return httpx.Response(404, json={"error": {"message": "unhandled " + path}})


@pytest.fixture
def ga(social, monkeypatch, tmp_path):
    for k, v in {"GOOGLE_OAUTH_CLIENT_ID": "cid", "GOOGLE_OAUTH_CLIENT_SECRET": "csec", "GOOGLE_ADS_DEVELOPER_TOKEN": "DEVTOKEN",
                 "SOCIAL_DIR": str(tmp_path / "social")}.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.ads import gads as G
    from app.mailbox import accounts as ma
    ma.set_http(httpx.Client(transport=httpx.MockTransport(google_handler)))
    G.set_http(httpx.Client(transport=httpx.MockTransport(ads_handler)))
    CALLS.clear()
    STATE.clear()
    D = social
    P1._hire_and_setup(D)
    D.onboard(T, business="Sharma Dental", city="Akola", sells="Dental implants, braces", website="https://sharmadental.example")
    yield D, G
    ma.set_http(None)
    G.set_http(None)


def _connect(D, G):
    url = G.connect_url(T)
    q = parse_qs(urlparse(url).query)
    assert "https://www.googleapis.com/auth/adwords" in q["scope"][0] and q["access_type"] == ["offline"]
    return G.finish_link("code1", q["state"][0])


def _png() -> bytes:
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (1200, 1200), (40, 90, 200)).save(b, "PNG")
    return b.getvalue()


def _video_row(D, vid="AbCdEfGhIjK"):
    with D.session() as s:
        s.add(D.SocialMedia(tenant_id=T, account="x", platform="youtube", media_id=vid, fmt="reel", caption="Smile makeover in 30 sec",
                            views=4000, posted_at=D.now() - timedelta(days=2)))


def test_not_configured_says_so(social, monkeypatch):
    from app.ads import gads as G
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "")
    from app.config import get_settings
    get_settings.cache_clear()
    assert G.view(T)["configured"] is False
    with pytest.raises(G.GAdsError):
        G.connect_url(T)


def test_no_developer_token_needed_since_sep_2026(ga, monkeypatch):
    """Google sunset developer tokens (9 Sep 2026): access belongs to the Cloud project; the header goes only when set."""
    D, G = ga
    monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "")
    from app.config import get_settings
    get_settings.cache_clear()
    STATE["devtoken"] = None
    assert G.configured() is True
    _connect(D, G)
    assert G.view(T)["account"]["customer_id"] == "1112223333"


def test_connect_lists_accounts_and_skips_the_manager(ga):
    D, G = ga
    r = _connect(D, G)
    assert r["email"] == "meghana@example.in" and set(r["accounts"]) == {"Sharma Dental Ads", "MCC"}
    acc = G.view(T)["account"]
    assert acc["customer_id"] == "1112223333" and acc["currency"] == "INR"          # the only non-manager account is picked
    with pytest.raises(G.GAdsError):
        G.choose(T, "9998887777")                                                    # a manager account cannot run ads
    with pytest.raises(G.GAdsError):
        G.finish_link("code1", "gad_reused")


def test_read_youtube_campaigns_into_the_ads_desk(ga):
    D, G = ga
    _connect(D, G)
    r = G.read(T)
    c = r["campaigns"][0]
    assert c["name"] == "Diwali Shorts" and c["spend"] == 950.0 and c["views"] == 6500 and c["cpv"] == 0.15 and c["conversions"] == 10
    assert "metrics.video_views" in CALLS[-1][1]                    # fell back from video_trueview_views
    from app.ads.service import AdsRow
    with D.session() as s:
        rows = s.scalars(D.select(AdsRow).where(AdsRow.tenant_id == T)).all()
    assert len(rows) == 2 and {r.campaign for r in rows} == {"Diwali Shorts"}


def test_draft_checks_then_paused_create_then_start_only_with_confirm(ga):
    D, G = ga
    _connect(D, G)
    _video_row(D)
    d = G.new_draft(T, "AbCdEfGhIjK", daily=300, days=3)
    assert d["headlines"][0] == "Smile makeover in 30 sec" and d["business"] == "Sharma Dental"
    assert d["final_url"] == "https://sharmadental.example" and "Logo chahiye" in " ".join(d["problems"])
    with pytest.raises(G.GAdsError):
        G.check(T, d["id"])                                          # problems first, Google is not even asked
    from app.social import publish as SP
    logo = SP.add_asset(T, _png(), "logo.png")
    d = G.set_draft(T, d["id"], logo_asset=logo["id"], descriptions=["Painless implants. Call or WhatsApp today."])
    assert d["problems"] == []
    assert G.check(T, d["id"])["status"] == "checked"
    body = CALLS[-1][1]
    assert body["validateOnly"] is True
    ops = body["mutateOperations"]
    assert [next(iter(o)) for o in ops][:3] == ["campaignBudgetOperation", "campaignOperation", "adGroupOperation"]
    budget = ops[0]["campaignBudgetOperation"]["create"]
    assert budget["amountMicros"] == "300000000" and budget["explicitlyShared"] is False and budget["resourceName"].endswith("/-1")
    camp = ops[1]["campaignOperation"]["create"]
    assert camp["advertisingChannelType"] == "DEMAND_GEN" and camp["status"] == "PAUSED"
    assert camp["containsEuPoliticalAdvertising"] == "DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING" and "targetSpend" in camp
    ch = ops[2]["adGroupOperation"]["create"]["demandGenAdGroupSettings"]["channelControls"]["selectedChannels"]
    assert ch["youtubeInStream"] and ch["youtubeShorts"] and not ch["gmail"] and not ch["discover"] and not ch["display"]
    crit = [o["adGroupCriterionOperation"]["create"] for o in ops if "adGroupCriterionOperation" in o]
    assert {"geoTargetConstant": "geoTargetConstants/2356"} in [c.get("location") for c in crit]
    assert {c["language"]["languageConstant"] for c in crit if "language" in c} == {"languageConstants/1023", "languageConstants/1000"}
    assets = [o["assetOperation"]["create"] for o in ops if "assetOperation" in o]
    assert base64.b64decode(next(a for a in assets if a["type"] == "IMAGE")["imageAsset"]["data"])[:2] == b"\xff\xd8"
    assert next(a for a in assets if a["type"] == "YOUTUBE_VIDEO")["youtubeVideoAsset"] == {"youtubeVideoId": "AbCdEfGhIjK"}
    ad = ops[-1]["adGroupAdOperation"]["create"]["ad"]
    vr = ad["demandGenVideoResponsiveAd"]
    assert ad["finalUrls"] == ["https://sharmadental.example"] and vr["businessName"] == {"text": "Sharma Dental"}
    assert vr["videos"][0]["asset"].endswith("/-5") and vr["logoImages"][0]["asset"].endswith("/-4") and len(vr["headlines"]) == 3
    v = G.create(T, d["id"])
    assert v["status"] == "created" and v["campaign"] == "customers/1112223333/campaigns/555"
    assert CALLS[-1][1]["validateOnly"] is False
    with pytest.raises(G.GAdsError):
        G.start(T, d["id"])                                          # never without her confirm
    v = G.start(T, d["id"], confirm=True)
    upd = CALLS[-1][1]["mutateOperations"][0]["campaignOperation"]
    assert upd == {"update": {"resourceName": "customers/1112223333/campaigns/555", "status": "ENABLED"}, "updateMask": "status"}
    assert v["status"] == "running" and v["stop_on"]
    with pytest.raises(G.GAdsError):
        G.set_draft(T, d["id"], daily=100)                           # made in Google: change it there
    with D.session() as s:
        s.get(G.GAdsDraft, d["id"]).stop_on = "2000-01-01"
    out = G.daily_watch(T)
    assert out["ended"] == 1 and G.drafts(T)[0]["status"] == "ended"
    assert CALLS[-2][1]["mutateOperations"][0]["campaignOperation"]["update"]["status"] == "PAUSED" or any(
        c[0] == "mutate" and c[1]["mutateOperations"][0].get("campaignOperation", {}).get("update", {}).get("status") == "PAUSED" for c in CALLS)
    assert any("finished its 3 days" in e["text"] for e in D.desk_view(T)["events"])


def test_caps_and_banned_words(ga, monkeypatch):
    D, G = ga
    _connect(D, G)
    d = G.new_draft(T, "AbCdEfGhIjK", daily=5000)
    assert any("Roz ka budget" in p for p in d["problems"])
    d = G.set_draft(T, d["id"], daily=200, headlines=["Satta matka khelo", "Paisa double"])
    assert any("satta" in p.lower() or "jua" in p.lower() for p in d["problems"])
    d = G.set_draft(T, d["id"], headlines=["Best SIP mutual fund tips"])
    assert any("SEBI" in p for p in d["problems"])


def test_not_approved_token_is_said_plainly(ga):
    D, G = ga
    _connect(D, G)
    STATE["not_approved"] = True
    with pytest.raises(G.GAdsError) as e:
        G.read(T)
    assert "test accounts" in str(e.value) and "Basic access" in str(e.value) and "Google Cloud project" in str(e.value)


def test_routes(ga):
    D, G = ga
    from app import main
    with TestClient(main.app) as c:
        assert c.get("/api/social/ytads").json()["account"] is None
        url = c.get("/api/social/ytads/connect").json()["url"]
        st = parse_qs(urlparse(url).query)["state"][0]
        page = c.get("/auth/google/callback", params={"code": "c1", "state": st})
        assert page.status_code == 200 and "meghana@example.in" in page.text
        v = c.get("/api/social/ytads").json()
        assert v["account"]["customer_id"] == "1112223333"
        _video_row(D)
        did = c.post("/api/social/ytads/drafts", json={"video_id": "AbCdEfGhIjK"}).json()["id"]
        assert c.post(f"/api/social/ytads/drafts/{did}/create").status_code == 400          # logo missing
        assert c.post(f"/api/social/ytads/drafts/{did}/start", json={}).status_code == 400
        assert c.post(f"/api/social/ytads/drafts/{did}/burn").status_code == 404
        assert c.post("/api/social/ytads/read").json()["campaigns"][0]["name"] == "Diwali Shorts"


def test_console_phone_privacy_wired():
    root = P1.ROOT
    js = (root / "server/app/static/console/employees.js").read_text()
    assert "/api/social/ytads" in js and "Check with Google (free)" in js and "Create in Google (paused)" in js and "data-ytact" in js
    dart = (root / "lib/ui/employees_screen.dart").read_text()
    assert "class YtAdsScreen" in dart and "Start this YouTube ad?" in dart
    pv = (root / "server/app/static/privacy.html").read_text()
    assert "Google Ads (YouTube ads)" in pv and "always PAUSED" in pv
