"""v0.384 SOCIAL MEDIA MANAGER Phase 6 - more platforms: WhatsApp Business on her own number by Meta's Embedded Signup
(code -> her business token sealed, webhooks subscribed, number registered, her Business inbox channel made) and LinkedIn
(her profile: Sign In with LinkedIn + Share on LinkedIn; text + one photo; escaped text; 60-day token warned). Mock
transport for Meta and LinkedIn."""
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
SENT: list[tuple[str, object]] = []
STATE: dict = {}


def handler(req: httpx.Request) -> httpx.Response:
    u = str(req.url)
    path = urlparse(u).path
    q = parse_qs(urlparse(u).query)
    # ---- LinkedIn
    if u.startswith("https://www.linkedin.com/oauth/v2/accessToken"):
        f = parse_qs(req.content.decode())
        assert f["client_secret"] == ["lisecret"] and f["redirect_uri"] == ["https://hoola.test/api/social/linkedin/callback"]
        return httpx.Response(200, json={"access_token": "LI_TOK", "expires_in": 5184000, "scope": "openid,profile,w_member_social"})
    if u.startswith("https://api.linkedin.com/v2/userinfo"):
        return httpx.Response(200, json={"sub": "abc123", "name": "Meghana Sharma", "picture": "https://media.licdn.example/p.jpg"})
    if u.startswith("https://api.linkedin.com/rest/images"):
        SENT.append(("li_init", json.loads(req.content), dict(req.headers)))
        return httpx.Response(200, json={"value": {"uploadUrl": "https://upload.linkedin.example/u1", "image": "urn:li:image:I1"}})
    if u.startswith("https://upload.linkedin.example/"):
        SENT.append(("li_put", len(req.content), None))
        return httpx.Response(201)
    if u.startswith("https://api.linkedin.com/rest/posts"):
        if STATE.get("li_dead"):
            return httpx.Response(401, json={"message": "Invalid access token"})
        SENT.append(("li_post", json.loads(req.content), dict(req.headers)))
        return httpx.Response(201, headers={"x-restli-id": "urn:li:share:9"})
    # ---- WhatsApp Embedded Signup
    if path == "/v25.0/oauth/access_token" and q.get("code") == ["WACODE"]:
        assert q["client_secret"] == ["fbsecret"] and "redirect_uri" not in q
        return httpx.Response(200, json={"access_token": "WA_BIZ_TOKEN"})
    if req.method == "GET" and path == "/v25.0/109876543210987":
        return httpx.Response(200, json={"display_phone_number": "+91 98765 43210", "verified_name": "Sharma Dental",
                                         "quality_rating": "GREEN", "id": "109876543210987"})
    if req.method == "POST" and path == "/v25.0/209876543210987/subscribed_apps":
        SENT.append(("subscribe", parse_qs(req.content.decode()), None))
        return httpx.Response(200, json={"success": True})
    if req.method == "POST" and path == "/v25.0/109876543210987/register":
        if STATE.get("pin_set"):
            return httpx.Response(400, json={"error": {"message": "two-step verification PIN mismatch", "code": 133005}})
        SENT.append(("register", json.loads(req.content), None))
        return httpx.Response(200, json={"success": True})
    return P1.handler(req)


@pytest.fixture
def pf(social, monkeypatch, tmp_path):
    monkeypatch.setenv("LINKEDIN_CLIENT_ID", "liapp")
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "lisecret")
    monkeypatch.setenv("WA_ES_CONFIG_ID", "WACFG7")
    monkeypatch.setenv("SOCIAL_DIR", str(tmp_path / "social"))
    from app.config import get_settings
    get_settings.cache_clear()
    from app.social import meta as M
    M.set_http(httpx.Client(transport=httpx.MockTransport(handler)))
    SENT.clear()
    STATE.clear()
    D = social
    P1._hire_and_setup(D)
    return D


def _li(D):
    from app.social import linkedin as LI
    url = D.connect_url(T, "linkedin")
    st = parse_qs(urlparse(url).query)
    assert st["scope"] == ["openid profile w_member_social"] and url.startswith("https://www.linkedin.com/oauth/v2/authorization")
    LI.finish("LICODE", st["state"][0])
    return LI


def _jpeg() -> bytes:
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (1080, 1080), (30, 90, 160)).save(b, "JPEG")
    return b.getvalue()


# ---------------------------------------------------------------- LinkedIn
def test_linkedin_connects_her_profile_once(pf):
    D = pf
    LI = _li(D)
    a = next(x for x in D.accounts(T) if x["platform"] == "linkedin")
    assert a["name"] == "Meghana Sharma" and a["status"] == "ok" and a["can_post"] and a["can_reply"] is None
    with pytest.raises(D.SocialError):
        LI.finish("LICODE", "soc_li_reused")
    assert D.desk_view(T)["connect"]["linkedin"] is True
    assert D._sync_all(T) == []                                          # nothing Meta-readable on LinkedIn: skipped quietly


def test_linkedin_text_is_escaped_and_three_hashtags():
    from app.social.linkedin import text_of
    t = text_of("Smile (free check-up) @clinic_* today!\n#one #two", ["#akola", "dentist", "#smile", "#extra"])
    assert "\\(free check-up\\)" in t and "\\@clinic\\_\\*" in t and t.count("\\#") == 3 and "#extra" not in t
    assert "#one" not in t                                               # the caption's own hashtag line is replaced


def test_post_goes_to_linkedin_with_photo(pf):
    D = pf
    _li(D)
    from app.social import publish as SP
    a = SP.add_asset(T, _jpeg(), "p.jpg")
    with D.session() as s:
        p = D.SocialPost(tenant_id=T, slot="2026-11-08T12:00", platforms="linkedin", fmt="image", hook="Tip",
                         caption="3 tips for strong teeth (doctor's advice)", hashtags=json.dumps(["#dental", "#akola"]),
                         status="draft", media=json.dumps([a["id"]]))
        s.add(p)
        s.flush()
        pid = p.id
    r = SP.publish_post(T, pid, by_tap=True)
    assert r["status"] == "published" and r["results"]["linkedin"]["id"] == "urn:li:share:9"
    assert r["results"]["linkedin"]["link"] == "https://www.linkedin.com/feed/update/urn:li:share:9/"
    init = next(x for x in SENT if x[0] == "li_init")
    assert init[1]["initializeUploadRequest"]["owner"] == "urn:li:person:abc123" and init[2]["linkedin-version"] == "202510"
    assert next(x for x in SENT if x[0] == "li_put")[1] > 1000
    post = next(x for x in SENT if x[0] == "li_post")
    body, hdr = post[1], post[2]
    assert body["author"] == "urn:li:person:abc123" and body["content"]["media"]["id"] == "urn:li:image:I1"
    assert "\\(doctor's advice\\)" in body["commentary"] and hdr["x-restli-protocol-version"] == "2.0.0"


def test_linkedin_problems_and_dead_token(pf):
    D = pf
    _li(D)
    from app.social import publish as SP
    with D.session() as s:
        reel = D.SocialPost(tenant_id=T, slot="2026-11-08T12:00", platforms="instagram,linkedin", fmt="reel", caption="x", status="draft")
        text = D.SocialPost(tenant_id=T, slot="2026-11-08T12:00", platforms="linkedin", fmt="image", caption="Only words today", status="draft")
        s.add_all([reel, text])
        s.flush()
        assert "LinkedIn takes only text + photo" in " ".join(SP.problems(reel))
        tid = text.id
    STATE["li_dead"] = True
    r = SP.publish_post(T, tid, by_tap=True)
    assert r["status"] == "failed"
    assert next(x for x in D.accounts(T) if x["platform"] == "linkedin")["status"] == "expired"


def test_linkedin_tick_on_a_post_and_planner(pf):
    D = pf
    D.finish_link("instagram", "IGCODE", P1._state_from(D.connect_url(T, "instagram")), background=False)
    _li(D)
    plan = D._rules_plan(D._plan_inputs(T))
    assert any("linkedin" in p["platforms"] for p in plan["posts"])
    assert all("linkedin" not in p["platforms"] for p in plan["posts"] if p["format"] in ("reel", "story"))
    pid = D.calendar(T)[0]["id"]
    D.set_post(T, pid, status="approved")
    D.set_post(T, pid, platforms=["instagram", "linkedin", "tiktok"])
    p = next(x for x in D.calendar(T) if x["id"] == pid)
    assert p["platforms"] == ["instagram", "linkedin"] and p["status"] == "draft"          # a change needs her OK again
    with pytest.raises(D.SocialError):
        D.set_post(T, pid, platforms=["tiktok"])


def test_linkedin_login_end_is_warned_once(pf):
    D = pf
    _li(D)
    with D.session() as s:
        a = s.scalars(D.select(D.SocialAccount).where(D.SocialAccount.platform == "linkedin")).first()
        a.expires_at = D.now() + timedelta(days=3)
    D.watch(T)
    D.watch(T)
    warn = [e for e in D.desk_view(T)["events"] if "Linkedin login" in e["text"]]
    assert len(warn) == 1


# ---------------------------------------------------------------- WhatsApp Embedded Signup
def _wa_state(D) -> str:
    url = D.connect_url(T, "whatsapp")
    assert url.startswith("https://hoola.test/api/social/whatsapp/start?s=soc_wh_")
    return parse_qs(urlparse(url).query)["s"][0]


def test_whatsapp_embedded_signup_makes_her_inbox_channel(pf):
    D = pf
    from app.employee import inbox as biz
    from app.social import wabiz
    st = _wa_state(D)
    page = wabiz.start_page(st)
    assert "WACFG7" in page and "connect.facebook.net/en_US/sdk.js" in page and st in page
    assert "WA_EMBEDDED_SIGNUP" in wabiz.ES_JS and "response_type: 'code'" in wabiz.ES_JS and "facebook" in wabiz.ES_JS
    r = wabiz.finish(st, "WACODE", "209876543210987", "109876543210987")
    assert r["number"] == "+91 98765 43210" and r["registered"]
    assert any(x[0] == "subscribe" for x in SENT)
    reg = next(x for x in SENT if x[0] == "register")[1]
    assert reg["messaging_product"] == "whatsapp" and len(reg["pin"]) == 6 and reg["pin"].isdigit()
    ch = biz.channels(T)
    assert ch == [{"phone_number_id": "109876543210987", "display_number": "919876543210", "own_token": True}]
    from app.employee.inbox import _channel_auth
    assert _channel_auth(T, "109876543210987") == ("109876543210987", "WA_BIZ_TOKEN")
    a = next(x for x in D.accounts(T) if x["platform"] == "whatsapp")
    assert a["name"] == "Sharma Dental" and a["can_reply"] is None
    with pytest.raises(D.SocialError):
        wabiz.finish(st, "WACODE", "209876543210987", "109876543210987")                    # the state works once
    D.disconnect(T, a["id"])
    assert biz.channels(T) == []


def test_whatsapp_pin_problem_still_connects_with_a_note(pf):
    D = pf
    from app.social import wabiz
    STATE["pin_set"] = True
    r = wabiz.finish(_wa_state(D), "WACODE", "209876543210987", "109876543210987")
    assert r["registered"] is False
    assert any("two-step PIN" in e["text"] for e in D.desk_view(T)["events"])
    with pytest.raises(D.SocialError):
        wabiz.finish(_wa_state(D), "WACODE", "", "")                   # signup not finished on Meta's side


def test_whatsapp_and_linkedin_routes(pf):
    D = pf
    from app import main
    with TestClient(main.app) as c:
        url = c.get("/api/social/connect/whatsapp").json()["url"]
        st = parse_qs(urlparse(url).query)["s"][0]
        page = c.get(f"/api/social/whatsapp/start?s={st}")
        assert page.status_code == 200 and "Continue with Facebook" in page.text
        assert "purana" in c.get("/api/social/whatsapp/start?s=nope").text
        assert c.get("/api/social/whatsapp/es.js").headers["content-type"].startswith("application/javascript")
        assert c.post("/api/social/whatsapp/finish", json={"state": "bad", "code": "WACODE"}).status_code == 400
        ok = c.post("/api/social/whatsapp/finish", json={"state": st, "code": "WACODE", "waba_id": "209876543210987", "phone_number_id": "109876543210987"})
        assert ok.status_code == 200 and ok.json()["number"] == "+91 98765 43210"
        li = c.get("/api/social/connect/linkedin").json()["url"]
        lst = parse_qs(urlparse(li).query)["state"][0]
        cb = c.get(f"/api/social/linkedin/callback?code=LICODE&state={lst}")
        assert cb.status_code == 200 and "Meghana Sharma" in cb.text
        assert "nahi juda" in c.get("/api/social/linkedin/callback?error=user_cancelled_login").text
        v = c.get("/api/social/desk").json()
        assert {k: v["connect"][k] for k in ("instagram", "facebook", "linkedin", "whatsapp")} == {"instagram": True, "facebook": True, "linkedin": True, "whatsapp": True}
        assert {a["platform"] for a in v["accounts"]} == {"whatsapp", "linkedin"}


def test_console_phone_privacy_wired():
    root = P1.ROOT
    js = (root / "server/app/static/console/employees.js").read_text()
    assert "whatsapp: 'WhatsApp Business'" in js and "data-scli" in js and "'linkedin', 'whatsapp'" in js
    dart = (root / "lib/ui/employees_screen.dart").read_text()
    assert "'whatsapp': 'WhatsApp Business'" in dart and "Also on LinkedIn" in dart
    pv = (root / "server/app/static/privacy.html").read_text()
    assert "never WhatsApp Web" in pv and "LinkedIn ends it after about 60 days" in pv
