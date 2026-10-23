"""Feedback Sahayak: language-aware sentiment + aspects, imports (pasted / Play Console / any sheet), sources (inbox, call
notes), themes with trend, fix-first ranking, NPS / CSAT, urgent + spike alerts, suspicious signals (never removed),
reply drafts public only on HER tap (hash, checks, Google API), signed survey link (honeypot, rate limit, no gating),
report files, worker tick, tools + API."""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.feedback.models  # noqa: F401  (tables for the env fixture)
from tests.test_life import conv_ctx

T = "default"

PLAY = ("Package Name,App Version Name,Reviewer Language,Review Submit Date and Time,Star Rating,Review Title,Review Text,"
        "Developer Reply Text,Review Link\n"
        "com.x,1.2,en,{old}T10:00:00Z,1,,App crashes on login every time,,https://play/r1\n"
        "com.x,1.2,hi,{old}T11:00:00Z,2,,payment fail ho jata hai app mein,,https://play/r2\n"
        "com.x,1.3,en,{new}T09:00:00Z,5,Love it,Very helpful and fast,,https://play/r3\n"
        "com.x,1.3,en,{new}T09:30:00Z,1,,app crash after update,,https://play/r4\n"
        ",,,,,,,,\n")


@pytest.fixture
def fb(env, monkeypatch):
    from app.feedback import service as S
    monkeypatch.setattr(S, "_ai_json", lambda *a, **k: {})
    cards = []
    real = S._publish
    monkeypatch.setattr(S, "_publish", lambda t, kind, p, conv="": (cards.append((kind, p)), real(t, kind, p, conv)))
    S.CARDS = cards
    S._RATE.clear()
    return S


def test_rules():
    from app.feedback import rules as R
    a = R.analyse("Khana bahut accha tha lekin delivery late aayi", 4)
    assert {(x["aspect"], x["pol"]) for x in a["aspects"]} == {("taste", "pos"), ("delivery", "neg")} and a["label"] == "mixed"
    assert R.analyse("खाना अच्छा नहीं था")["label"] == "neg" and R.analyse("खाना अच्छा नहीं था")["lang"] == "hi"
    m = R.analyse("jevan chhan hota, pan ushir zala")
    assert m["lang"] == "mr" and ("wait", "neg") in {(x["aspect"], x["pol"]) for x in m["aspects"]}
    u = R.analyse("biryani mein baal mila", 3)
    assert u["urgent"] and u["label"] == "neg" and u["aspects"][0]["aspect"] == "food_safety"
    assert R.analyse("staff was not rude at all, very polite")["label"] == "pos"
    assert R.stars_of("★★★★") == 4 and R.stars_of("FIVE") == 5 and R.stars_of("4/5") == 4 and R.stars_of("9") is None
    n = R.nps([10, 9, 9, 8, 7, 3, 0, 10])
    assert n["nps"] == 25 and n["promoters_pct"] == 50 and n["low_n"]
    assert R.csat([5, 4, 3, 1])["csat"] == 50
    assert R.spike(6, 4) and R.spike(2, 0) is None and R.spike(4, 16) is None
    assert R.reply_problems("Thanks! Call us on 98200 00000", "9820000000") == []
    probs = R.reply_problems("Sorry Ravi, call 9876543210. 20% discount if you remove this review", "9820000000")
    assert len(probs) == 2 and R.reply_problems("x" * 5000)
    assert R.mask("mera number 9876543210, mail a@b.co") == "mera number [phone], mail [email]"


def test_ingest_themes_fix_first(fb):
    S = fb
    S.save_settings(T, business="Annapurna Kitchen", phone="9820000000", avg_order_value=400, orders_per_year=6)
    r = S.add_text(T, "- Delivery 1 ghanta late aayi, khana thanda tha 2*\n- Delivery boy rude tha, delivery bahut late 1*\n"
                      "- Biryani mein baal mila! 1*\n- Swaad lajawab, paisa vasool 5*\n- khana mast tha ★★★★★")
    assert r["added"] == 5
    assert S.add_text(T, "- Swaad lajawab, paisa vasool 5*")["added"] == 0              # same review is not counted twice
    assert any(k == "feedback_alert" and p["kind"] == "urgent" for k, p in S.CARDS)      # baal = told at once
    old, new = (datetime.now(timezone.utc) - timedelta(days=45)).date(), (datetime.now(timezone.utc) - timedelta(days=1)).date()
    imp = S.import_file(T, "reviews_202610.csv", PLAY.format(old=old, new=new).encode())
    assert imp["source"] == "play" and imp["added"] == 4 and imp["columns"]["stars"] == "star rating"
    th = S.themes(T, 30)
    keys = {t["key"]: t for t in th["negative"]}
    assert keys["delivery:neg"]["count"] == 2 and keys["delivery:neg"]["people"] == 2 and keys["delivery:neg"]["rupees"] == 2 * 400 * 6
    assert keys["app:neg"]["count"] == 1 and keys["app:neg"]["prev"] == 2 and keys["app:neg"]["trend"]["pct"] == -50
    assert any(t["key"] == "taste:pos" for t in th["positive"])
    assert "[phone]" not in str(keys) and keys["delivery:neg"]["examples"]
    ff = S.fix_first(T, 30)
    assert ff["fix"][0]["key"] == "food_safety:neg" and "Sehat" in ff["fix"][0]["reasons"][0]
    assert ff["fix"][1]["key"] == "delivery:neg" and "Pehle theek karein" in ff["say"]
    sc = S.scores(T, 30)
    assert sc["csat"]["n"] == 7 and sc["by_source"]["play"]["n"] == 2
    # her "theek kiya" date -> before / after
    from app.db import session
    from app.feedback.models import FbItem
    with session() as s:
        for row in s.query(FbItem).filter(FbItem.source == "text").all():
            row.at = datetime.now(timezone.utc) - timedelta(days=3)
    S.theme_note(T, "delivery:neg", fixed_on="aaj", label="Delivery der")
    t2 = {t["key"]: t for t in S.themes(T, 30)["negative"]}["delivery:neg"]
    assert t2["label"] == "Delivery der" and t2["fixed"]["before"] == 2 and t2["fixed"]["after"] == 0
    with pytest.raises(S.FeedbackError):
        S.theme_note(T, "bad key")
    # other complaints with no known aspect are grouped by shared words
    S.add_text(T, "- AC kaam nahi kar raha tha hall mein 2*\n- hall ka AC band tha, garmi 2*")
    others = [t for t in S.themes(T, 30)["negative"] if t["key"].startswith("other_") or t["aspect"] == "ambience"]
    assert others and others[0]["count"] == 2


def test_reply_only_on_her_tap(fb, monkeypatch):
    from app.agent.feedback_tools import FEEDBACK_HANDLERS as HANDLERS
    from app.feedback import gbp
    S = fb
    S.save_settings(T, business="Annapurna Kitchen", phone="9820000000", sign_off="- Team Annapurna")
    S.add_text(T, "Delivery bahut late aayi aur khana thanda", source="zomato", stars=2, author="Ravi Kumar")
    it = S.items(T, source="zomato")[0]
    ctx = conv_ctx()
    out = asyncio.run(HANDLERS["feedback"](ctx, action="reply_draft", item_id=it["id"]))
    assert out["status"] == "needs_tap" and out["where"] == "copy" and "Ravi" in out["text"] and "9820000000" in out["text"]
    assert "Team Annapurna" in out["text"] and not out["problems"]
    rid, h = out["reply_id"], out["hash"]
    with pytest.raises(S.FeedbackError):
        S.reply_decide(T, rid, True, "wrong")                                        # stale card
    with pytest.raises(S.FeedbackError):
        S.reply_decide(T, rid, True, h, "Sorry, call our manager on 9123456789")      # customer-looking number blocked
    d = S.reply_decide(T, rid, True, h)
    assert d["status"] == "approved" and "Daal diya" in d["say"]
    assert S.reply_done(T, rid)["status"] == "posted" and S.items(T, source="zomato")[0]["replied"]
    # a Google review with her Business Profile joined: her tap posts through the official API
    sent = []
    monkeypatch.setattr(S, "_google_on", lambda t: True)
    monkeypatch.setattr(gbp, "put_reply", lambda t, name, text: sent.append((name, text)) or {})
    from app.db import session
    with session() as s:
        g, new = S._add(s, T, "google", "google:r9", "Staff bahut polite, great place", 5, None, "Meera",
                        meta={"name": "accounts/1/locations/2/reviews/r9"})
        gid = g.id
    card = S.reply_draft(T, gid)
    assert card["where"] == "google_api"
    assert S.reply_decide(T, card["reply_id"], True, card["hash"])["status"] == "posted"
    assert sent and sent[0][0].endswith("/reviews/r9")
    with pytest.raises(S.FeedbackError):
        S.reply_draft(T, gid)                                                        # already answered on the platform


def test_survey_link_public(fb):
    from app.feedback import api
    S = fb
    S.save_settings(T, business="Annapurna", review_link="https://g.page/r/abc/review", language="hinglish")
    v = S.survey_new(T, "nps", "Diwali feedback")
    tok = v["token"]
    assert v["link"].endswith("/api/feedback/s/" + tok) and "wa.me" in v["whatsapp"] and "SAB" in v["say"]
    app_ = FastAPI()
    app_.include_router(api.make_router(lambda: None, lambda: T))
    with TestClient(app_) as cl:
        assert cl.get("/api/feedback/s/" + tok[:-2] + "xx").status_code == 404           # tampered link
        page = cl.get("/api/feedback/s/" + tok)
        assert page.status_code == 200 and "recommend" in page.text and "default-src 'none'" in page.headers["content-security-policy"]
        assert cl.post("/api/feedback/s/" + tok, data={"score": "3", "website": "http://spam"}).status_code == 200
        assert S.scores(T, 30)["nps"]["n"] == 0                                          # honeypot answer not kept
        low = cl.post("/api/feedback/s/" + tok, data={"score": "2", "text": "Bill mein zyada paise lag gaye"}, headers={"x-real-ip": "1.1.1.1"})
        high = cl.post("/api/feedback/s/" + tok, data={"score": "10", "text": "badhiya"}, headers={"x-real-ip": "1.1.1.2"})
        assert low.status_code == high.status_code == 200
        assert "g.page/r/abc/review" in low.text and "g.page/r/abc/review" in high.text      # same for everyone: no gating
        assert cl.post("/api/feedback/s/" + tok, data={"score": "55"}, headers={"x-real-ip": "1.1.1.3"}).status_code == 400
        for _ in range(6):
            last = cl.post("/api/feedback/s/" + tok, data={"score": "9"}, headers={"x-real-ip": "1.1.1.9"})
        assert last.status_code == 429
        n = S.scores(T, 30)["nps"]
        assert n["n"] == 7 and n["detractors_pct"] == 14
        assert any(t["key"] == "billing:neg" for t in S.themes(T, 30)["negative"])
        S.survey_close(T, v["id"])
        assert cl.get("/api/feedback/s/" + tok).status_code == 410
        assert cl.post("/api/feedback/surveys", json={"kind": "csat"}).json()["kind"] == "csat"


def test_flags_sources_report_tools_api(fb, monkeypatch):
    from app.agent.feedback_tools import FEEDBACK_HANDLERS as HANDLERS
    from app.agent.tools import Ctx, ToolError
    from app.db import session
    from app.employee.models import BizContact, BizMessage
    from app.feedback import api
    from app.telecall.service import TeleCall, TeleLead
    S = fb
    same = "Best restaurant in the city, amazing food and great staff, must visit"
    S.add_text(T, same, source="google", stars=5, author="A One")
    S.add_text(T, same + "!", source="google", stars=5, author="B Two")
    S.add_text(T, "Got 20% discount for review, nice place", source="google", stars=5, author="C Three")
    fl = S.flagged(T)
    kinds = {f["kind"] for x in fl["items"] for f in x["flags"]}
    assert {"copy", "incentive"} <= kinds and fl["strong"] == 3 and "hatana Hoola ka kaam nahi" in fl["say"]
    assert len(S.items(T, source="google")) == 3                                        # nothing removed
    with session() as s:
        c = BizContact(tenant_id=T, wa_id="919811111111", name="Sunita")
        s.add(c)
        s.flush()
        s.add(BizMessage(tenant_id=T, contact_id=c.id, direction="in", by="customer", text="Kal ka order galat item aaya, bahut pareshani hui"))
        s.add(BizMessage(tenant_id=T, contact_id=c.id, direction="in", by="customer", text="ok thik hai kal milte hai"))
        lead = TeleLead(tenant_id=T, name="Rakesh", phone="9822222222")
        s.add(lead)
        s.flush()
        s.add(TeleCall(tenant_id=T, lead_id=lead.id, outcome="complaint", summary="Bola service bahut slow hai, 3 din se koi nahi aaya"))
    assert S.sync_inbox(T)["added"] == 1 and S.sync_inbox(T)["added"] == 0
    assert S.sync_calls(T)["added"] == 1
    assert S.items(T, source="whatsapp")[0]["themes"] == ["wrong_item:neg"]
    rep = S.report_file(T, 30)
    names = [f["name"] for f in rep["files"]]
    assert names[0].endswith(".xlsx") and names[1].endswith(".pdf")
    # worker: daily check + monthly report once
    from app.feedback.models import FbSettings
    with session() as s:
        S._st(s, T).report_day = 1
    at = datetime.now(timezone.utc).replace(hour=6, minute=0)                           # 11:30 am IST
    first = S.tick(at)
    assert first["checked"] == 1 and first["reports"] == 1
    assert S.tick(at) == {"checked": 0, "reports": 0}
    with session() as s:
        assert s.get(FbSettings, T).last_report
    # tools
    ctx = conv_ctx()
    run = lambda tool, **a: asyncio.run(HANDLERS[tool](ctx, **a))      # noqa: E731
    assert "say" in run("feedback_dekho", what="summary")
    assert run("feedback", action="add", text="Packing leak ho gayi, daal gir gayi", stars=2)["added"] == 1
    assert run("feedback_dekho", what="items", theme="packaging:neg")["items"]
    staff = Ctx(T, ctx.conversation_id, actor="staff:x")
    with pytest.raises(ToolError):
        asyncio.run(HANDLERS["feedback"](staff, action="settings", business="X"))
    with pytest.raises(ToolError):
        asyncio.run(HANDLERS["feedback"](ctx, action="import"))
    # API
    app_ = FastAPI()
    app_.include_router(api.make_router(lambda: None, lambda: T))
    with TestClient(app_) as cl:
        d = cl.get("/api/feedback").json()
        assert d["total"] >= 6 and "fix_first" in d and d["google"]["connected"] is False
        up = cl.post("/api/feedback/import", files={"file": ("swiggy_reviews.csv", b"Order ID,Rating,Review\n1,1,cold food\n2,4,tasty\n", "text/csv")})
        assert up.status_code == 200 and up.json()["source"] == "swiggy" and up.json()["added"] == 2, up.text
        bad = cl.post("/api/feedback/import", files={"file": ("x.csv", b"a,b\n1,2\n", "text/csv")})
        assert bad.status_code == 400
        assert cl.post("/api/feedback/sync", json={"what": "nope"}).status_code == 400
        assert cl.put("/api/feedback/settings", json={"language": "xx"}).status_code == 400
        assert cl.put("/api/feedback/settings", json={"period_days": 14}).json()["period_days"] == 14
        it = cl.get("/api/feedback/items", params={"source": "swiggy"}).json()["items"][0]
        card = cl.post(f"/api/feedback/items/{it['id']}/reply", json={}).json()
        assert cl.post(f"/api/feedback/replies/{card['reply_id']}/decide", json={"yes": False}).json()["status"] == "rejected"
        assert cl.get("/api/feedback/google/link").status_code == 400                    # server has no Google sign-in set up
        assert cl.delete(f"/api/feedback/items/{it['id']}").status_code == 200


def test_google_reviews_sync(fb, monkeypatch):
    import httpx

    from app import accounts as acc
    from app.db import now, session
    from app.feedback import gbp
    from app.feedback.models import FbGoogle
    S = fb
    monkeypatch.setenv("SECRET_KEY", "x" * 40)
    from app.config import get_settings
    get_settings.cache_clear()
    with session() as s:
        s.add(FbGoogle(tenant_id=T, address="me@x.in", access_token_enc=acc.encrypt("tok"), refresh_token_enc=acc.encrypt("ref"),
                       expiry=now() + timedelta(hours=1), location="accounts/1/locations/2", status="ok"))
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append((req.method, str(req.url)))
        assert req.headers["authorization"] == "Bearer tok"
        if req.method == "PUT":
            return httpx.Response(200, json={"comment": "ok"})
        page = req.url.params.get("pageToken")
        if not page:
            return httpx.Response(200, json={"nextPageToken": "p2", "reviews": [
                {"name": "accounts/1/locations/2/reviews/a1", "reviewId": "a1", "reviewer": {"displayName": "Priya S"}, "starRating": "ONE",
                 "comment": "(Translated by Google) Rude staff\n\n(Original)\nStaff bahut badtameez tha", "createTime": "2026-10-20T10:00:00Z"}]})
        return httpx.Response(200, json={"reviews": [
            {"name": "accounts/1/locations/2/reviews/a2", "reviewId": "a2", "reviewer": {"isAnonymous": True}, "starRating": "FIVE",
             "createTime": "2026-10-21T10:00:00Z", "reviewReply": {"comment": "Thanks!"}}]})
    gbp.set_http(httpx.Client(transport=httpx.MockTransport(handler)))
    try:
        out = S.sync_google(T)
        assert out["added"] == 2 and S.sync_google(T)["added"] == 0
        g = S.items(T, source="google")
        rude = next(x for x in g if x["stars"] == 1)
        assert rude["text"] == "Staff bahut badtameez tha" and rude["themes"] == ["staff:neg"] and not rude["replied"]
        assert next(x for x in g if x["stars"] == 5)["replied"]
        card = S.reply_draft(T, rude["id"])
        assert card["where"] == "google_api"
        assert S.reply_decide(T, card["reply_id"], True, card["hash"])["status"] == "posted"
        assert seen[-1][0] == "PUT" and seen[-1][1].endswith("/v4/accounts/1/locations/2/reviews/a1/reply")
        assert gbp.status(T)["last_sync"]
    finally:
        gbp.set_http(None)
