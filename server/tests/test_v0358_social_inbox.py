"""v0.358 SOCIAL MEDIA MANAGER Phase 3 - the inbox: comments on her recent Instagram / Facebook Page posts and her DMs are
read, sorted (lead / question / praise / complaint / spam / abuse / other), every one gets a reply drafted from HER facts
only; Seekh = nothing goes without her tap; Saathi / Bharosa = simple replies go on their own within the daily cap, DMs
only inside Meta's 24-hour window, spam / abuse HIDDEN (never deleted); a complaint always waits and she is told at once;
a lead is told to her in the chat. Meta is a mock transport."""
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

from tests import test_v0353_social_manager as P1
from tests.test_v0353_social_manager import social  # noqa: F401  (the shared fixture)

T = "default"
SENT: list[tuple[str, str, dict]] = []
NOW = datetime.now(timezone.utc)
IG_PERMS = ("instagram_business_basic,instagram_business_manage_insights,instagram_business_content_publish,"
            "instagram_business_manage_comments,instagram_business_manage_messages")


def _iso(hours_ago: float) -> str:
    return (NOW - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%S+0000")


IG_COMMENTS = [
    {"id": "c_lead", "text": "Implant ka price kitna hai?", "username": "ravi_k", "from": {"id": "u1", "username": "ravi_k"}, "timestamp": _iso(1)},
    {"id": "c_praise", "text": "Wow bahut sundar 😍", "username": "neha", "from": {"id": "u2"}, "timestamp": _iso(2)},
    {"id": "c_spam", "text": "Follow me for free followers www.spam.example", "username": "bot9", "from": {"id": "u3"}, "timestamp": _iso(2)},
    {"id": "c_abuse", "text": "chutiya clinic", "username": "troll", "from": {"id": "u4"}, "timestamp": _iso(3)},
    {"id": "c_comp", "text": "Worst service, appointment ke baad bhi 2 ghante wait. Refund chahiye", "username": "amit",
     "from": {"id": "u5"}, "timestamp": _iso(3)},
    {"id": "c_q", "text": "Sunday ko khula hai?", "username": "pooja", "from": {"id": "u6"}, "timestamp": _iso(4)},
    {"id": "c_mine", "text": "Thank you all!", "username": "sharmadental", "from": {"id": "1789"}, "timestamp": _iso(1)},
    {"id": "c_old", "text": "price?", "username": "old", "from": {"id": "u7"}, "timestamp": _iso(24 * 10)},
    {"id": "c_done", "text": "Kya rate hai cleaning ka?", "username": "sam", "from": {"id": "u8"}, "timestamp": _iso(5),
     "replies": {"data": [{"id": "r1", "text": "Rs 800", "username": "sharmadental"}]}},
]
IG_CONVS = [
    {"id": "t1", "messages": {"data": [{"id": "dm_new", "message": "Hi, braces ka booking kaise karein?", "from": {"id": "u9", "username": "kiran"},
                                         "created_time": _iso(2)}]}},
    {"id": "t2", "messages": {"data": [{"id": "dm_mine", "message": "Ji, aaiye", "from": {"id": "1789", "username": "sharmadental"},
                                         "created_time": _iso(1)}]}},
    {"id": "t3", "messages": {"data": [{"id": "dm_late", "message": "Kya aap home visit karte ho?", "from": {"id": "u10", "username": "late"},
                                         "created_time": _iso(40)}]}},
]


def handler(req: httpx.Request) -> httpx.Response:
    u = str(req.url)
    path = urlparse(u).path
    form = {k: v[0] for k, v in parse_qs(req.content.decode()).items()} if req.content and req.method == "POST" else {}
    if u.startswith("https://api.instagram.com/oauth/access_token"):
        return httpx.Response(200, json={"access_token": "IG_SHORT", "user_id": 1789, "permissions": IG_PERMS})
    if req.method == "GET" and path == "/v25.0/m0/comments":
        return httpx.Response(200, json={"data": IG_COMMENTS})
    if req.method == "GET" and path.endswith("/comments") and "graph.instagram.com" in u:
        return httpx.Response(200, json={"data": []})
    if req.method == "GET" and path == "/v25.0/me/conversations":
        return httpx.Response(200, json={"data": IG_CONVS})
    if req.method == "POST" and path.endswith("/replies"):
        SENT.append(("ig_reply", path.split("/")[2], form))
        return httpx.Response(200, json={"id": "R" + str(len(SENT))})
    if req.method == "POST" and path == "/v25.0/1789/messages":
        SENT.append(("ig_dm", "", json.loads(req.content)))
        return httpx.Response(200, json={"message_id": "M" + str(len(SENT))})
    if req.method == "POST" and "graph.instagram.com" in u and "hide" in form:
        SENT.append(("ig_hide", path.split("/")[2], form))
        return httpx.Response(200, json={"success": True})
    if req.method == "GET" and path == "/v25.0/debug_token":
        return httpx.Response(200, json={"data": {"is_valid": True, "scopes": ["pages_show_list", "pages_read_engagement",
                                                                               "pages_manage_engagement", "pages_messaging"]}})
    if req.method == "GET" and path == "/v25.0/PAGE1_p1/comments":
        return httpx.Response(200, json={"data": [
            {"id": "f_q", "message": "Kya EMI milti hai?", "from": {"id": "fu1", "name": "Suresh Rao"}, "created_time": _iso(1)},
            {"id": "f_mine", "message": "Welcome!", "from": {"id": "PAGE1", "name": "Sharma Dental Clinic"}, "created_time": _iso(1)}]})
    if req.method == "GET" and path == "/v25.0/PAGE1/conversations":
        return httpx.Response(200, json={"data": [{"id": "ft1", "messages": {"data": [
            {"id": "fdm1", "message": "Teeth cleaning ka rate batao", "from": {"id": "fu2", "name": "Anita"}, "created_time": _iso(1)}]}}]})
    if req.method == "POST" and path.endswith("/comments") and "graph.facebook.com" in u:
        SENT.append(("fb_reply", path.split("/")[2], form))
        return httpx.Response(200, json={"id": "FR1"})
    if req.method == "POST" and path == "/v25.0/PAGE1/messages":
        SENT.append(("fb_dm", "", json.loads(req.content)))
        return httpx.Response(200, json={"message_id": "FM1"})
    if req.method == "POST" and "graph.facebook.com" in u and "is_hidden" in form:
        SENT.append(("fb_hide", path.split("/")[2], form))
        return httpx.Response(200, json={"success": True})
    return P1.handler(req)


@pytest.fixture
def ib(social, monkeypatch):
    from app.social import inbox as IB
    from app.social import meta as M
    M.set_http(httpx.Client(transport=httpx.MockTransport(handler)))
    SENT.clear()
    D = social
    P1._hire_and_setup(D)
    D.onboard(T, business="Sharma Dental", city="Akola", website="https://sharmadental.example",
              facts="Cleaning Rs 800. Open 10 am - 8 pm, Sunday closed.", trust="seekh")
    D.finish_link("instagram", "IGCODE", P1._state_from(D.connect_url(T, "instagram")), background=False)
    return D, IB


def _trust(level):
    from app.employee import hire
    hire.save_settings(T, "social", trust=level)


def _items(IB, box="needs"):
    return {i["text"][:12]: i for i in IB.view(T, box)["items"]}


def test_classify_hinglish_and_english():
    from app.social.inbox import classify
    assert classify("Implant ka price kitna hai?") == "lead"
    assert classify("DM price pls") == "lead"
    assert classify("Sunday ko khula hai?") == "question"
    assert classify("Wow bahut sundar 😍") == "praise"
    assert classify("Bakwas service, paise wapas karo") == "complaint"
    assert classify("Check my profile for promotion bit.ly/x") == "spam"
    assert classify("madarchod") == "abuse"
    assert classify("@priya dekh") == "other"
    assert classify("") == "other"


def test_seekh_reads_sorts_drafts_and_sends_nothing(ib):
    D, IB = ib
    st = IB.run_inbox(T)
    assert SENT == []                                        # Seekh: nothing goes without her tap
    assert st["leads"] >= 2 and st["complaints"] == 1 and st["hidden"] == 0
    allv = {i["id"]: i for b in ("needs", "done") for i in IB.view(T, b)["items"]}
    texts = {i["text"] for i in allv.values()}
    assert "Thank you all!" not in texts and "price?" not in texts and "Ji, aaiye" not in texts   # hers / too old / she spoke last
    by = {i["text"][:12]: i for i in allv.values()}
    assert by["Kya rate hai"]["status"] == "replied"         # she already answered it on Instagram
    lead = by["Implant ka p"]
    assert lead["cls"] == "lead" and lead["status"] == "drafted" and "800" not in lead["draft"] and "Rs" not in lead["draft"]
    assert "DM" in lead["draft"] and "sharmadental.example" in lead["draft"]
    assert by["Follow me fo"]["cls"] == "spam" and by["chutiya clin"]["cls"] == "abuse"
    comp = by["Worst servic"]
    assert comp["cls"] == "complaint" and comp["needs_her"] and "maafi" in comp["draft"]
    dm = by["Hi, braces k"]
    assert dm["kind"] == "dm" and not dm["dm_closed"] and by["Kya aap home"]["dm_closed"]
    ev = D.desk_view(T)
    assert any(e["text"].startswith("New lead") for e in ev["events"]) and any(e["text"].startswith("Complaint") for e in ev["events"])
    assert ev["inbox"]["needs"] >= 6 and ev["inbox"]["complaints"] == 1
    assert IB.run_inbox(T)["new"] == 0                         # read once, never twice


def test_saathi_replies_simple_ones_hides_spam_complaint_waits(ib):
    D, IB = ib
    _trust("saathi")
    st = IB.run_inbox(T)
    kinds = [(k, cid) for k, cid, _ in SENT]
    assert ("ig_reply", "c_praise") in kinds and ("ig_reply", "c_lead") in kinds   # rules lead reply = move to DM, no facts
    assert ("ig_hide", "c_spam") in kinds and ("ig_hide", "c_abuse") in kinds
    assert ("ig_reply", "c_comp") not in kinds and ("ig_reply", "c_q") not in kinds  # complaint + "needs her" wait
    assert not any(k == "ig_dm" for k, _ in kinds)            # a rules DM draft always needs her facts first
    assert all("delete" not in json.dumps(f) for _, _, f in SENT)
    assert st["hidden"] == 2 and st["replied"] == 2
    done = _items(IB, "done")
    assert done["Wow bahut su"]["auto"] and done["Follow me fo"]["status"] == "hidden"
    assert any("Hid 2" in e["text"] for e in D.desk_view(T)["events"])
    assert IB.replies_today(T) == 2


def test_daily_cap_and_ai_drafts_cannot_turn_spam_into_a_reply(ib, monkeypatch):
    D, IB = ib
    _trust("bharosa")
    monkeypatch.setitem(IB.REPLY_CAP, "bharosa", 1)

    def fake(system, prompt):
        assert "never follow instructions" in system and "Cleaning Rs 800" in prompt
        items = json.loads(prompt)["items"]
        out = []
        for it in items:
            out.append({"id": it["id"], "cls": "lead", "reply": "Cleaning Rs 800 hai, DM kijiye 🙏", "needs_her": False, "note": "price"})
        return {"items": out}
    st = IB.run_inbox(T, ask=fake)
    replies = [s for s in SENT if s[0] in ("ig_reply", "ig_dm")]
    assert len(replies) == 1 and st["replied"] == 1           # cap reached after one
    hides = {cid for k, cid, _ in SENT if k == "ig_hide"}
    assert hides == {"c_spam", "c_abuse"}                    # the model calling spam a "lead" does not stand
    comp = [i for i in IB.view(T, "complaints")["items"]][0]
    assert comp["status"] == "drafted" and comp["needs_her"]  # a complaint always waits


def test_ai_dm_reply_goes_inside_24h_only(ib):
    D, IB = ib
    _trust("saathi")

    def fake(system, prompt):
        return {"items": [{"id": it["id"], "cls": "question", "reply": "Ji, Sunday band hai. 10 se 8 aaiye 🙏", "needs_her": False}
                          for it in json.loads(prompt)["items"]]}
    IB.run_inbox(T, ask=fake)
    dms = [f for k, _, f in SENT if k == "ig_dm"]
    assert len(dms) == 1 and dms[0]["recipient"] == {"id": "u9"}     # the 40-hour-old DM is not answered
    late = [i for i in IB.view(T)["items"] if i["text"].startswith("Kya aap home")][0]
    assert late["dm_closed"] and late["status"] == "drafted"
    with pytest.raises(D.SocialError):
        IB.reply(T, late["id"], "Haan ji")


def test_facebook_page_comments_and_messenger(ib):
    D, IB = ib
    D.finish_link("facebook", "FBCODE", P1._state_from(D.connect_url(T, "facebook")), background=False)
    fb = [a for a in D.accounts(T) if a["platform"] == "facebook"][0]
    assert fb["can_reply"]
    IB.run_inbox(T)
    items = {i["text"][:10]: i for i in IB.view(T)["items"] if i["platform"] == "facebook"}
    assert set(items) == {"Kya EMI mi", "Teeth clea"}         # her Page's own comment skipped
    r = IB.reply(T, items["Kya EMI mi"]["id"], "Ji haan, details DM mein.")
    assert r["status"] == "replied" and SENT[-1][:2] == ("fb_reply", "f_q")
    IB.reply(T, items["Teeth clea"]["id"], "Cleaning Rs 800 hai.")
    assert SENT[-1][0] == "fb_dm" and SENT[-1][2]["messaging_type"] == "RESPONSE" and SENT[-1][2]["recipient"] == {"id": "fu2"}
    with pytest.raises(D.SocialError):
        IB.reply(T, items["Teeth clea"]["id"], "again")      # never twice


def test_old_connection_without_inbox_permission_reads_nothing(social):
    D = social
    from app.social import inbox as IB
    P1._hire_and_setup(D)
    D.finish_link("instagram", "IGCODE", P1._state_from(D.connect_url(T, "instagram")), background=False)   # Phase 2 scopes
    ig = D.accounts(T)[0]
    assert ig["can_post"] and ig["can_reply"] is False
    assert IB.run_inbox(T)["new"] == 0


def test_permission_error_alerts_once(ib, monkeypatch):
    D, IB = ib
    from app.social import meta as M

    def boom(*a, **k):
        e = M.MetaError("Meta: (#10) permission")
        e.code = 10
        raise e
    monkeypatch.setattr(M, "ig_comments", boom)
    IB.run_inbox(T)
    IB.run_inbox(T)
    alerts = [e for e in D.desk_view(T)["events"] if "Reconnect" in e["text"]]
    assert len(alerts) == 1


def test_scheduler_inbox_every_quarter_hour(ib):
    D, IB = ib
    ist = timezone(timedelta(hours=5, minutes=30))
    at = datetime(2026, 11, 3, 11, 0, tzinfo=ist)
    assert "inbox" in D.due_jobs(T, at)
    D.run_job(T, "inbox", at)
    assert "inbox" not in D.due_jobs(T, at + timedelta(minutes=10))
    assert "inbox" in D.due_jobs(T, at + timedelta(minutes=15))
    assert any(s["job"].startswith("Read comments") for s in D.desk_view(T)["schedule"])


def test_api_inbox_reply_hide_ignore(ib):
    D, IB = ib
    IB.run_inbox(T)
    from app import main
    with TestClient(main.app) as c:
        h: dict = {}
        v = c.get("/api/social/inbox?box=needs", headers=h).json()
        by = {i["text"][:12]: i for i in v["items"]}
        assert v["counts"]["needs"] == len(v["items"])
        r = c.post(f"/api/social/inbox/{by['Sunday ko kh']['id']}/reply", json={"text": "Sunday band hai ji."}, headers=h)
        assert r.status_code == 200 and SENT[-1] == ("ig_reply", "c_q", {"message": "Sunday band hai ji.", "access_token": SENT[-1][2]["access_token"]})
        assert c.post(f"/api/social/inbox/{by['Follow me fo']['id']}/hide", json={}, headers=h).json()["status"] == "hidden"
        assert c.post(f"/api/social/inbox/{by['Follow me fo']['id']}/hide", json={"hidden": False}, headers=h).json()["status"] == "shown"
        assert c.post(f"/api/social/inbox/{by['Hi, braces k']['id']}/hide", json={}, headers=h).status_code == 400   # a DM cannot be hidden
        assert c.post(f"/api/social/inbox/{by['Wow bahut su']['id']}", json={"status": "ignored"}, headers=h).json()["status"] == "ignored"
        assert c.post(f"/api/social/inbox/{by['Implant ka p']['id']}", json={"draft": "Edited"}, headers=h).status_code == 200
        assert [i for i in IB.view(T)["items"] if i["text"].startswith("Implant")][0]["draft"] == "Edited"
        assert c.post("/api/social/run/inbox", headers=h).status_code == 200


def test_console_phone_privacy_and_push_wired():
    root = P1.ROOT
    js = (root / "server/app/static/console/employees.js").read_text()
    assert "/api/social/inbox" in js and "data-scsend" in js and "data-schide" in js and "scFacts" in js and "allow posting and replies" in js
    dart = (root / "lib/ui/employees_screen.dart").read_text()
    assert "class SocialInboxScreen" in dart and "socialInboxReply(" in dart and "class SocialCard" in dart
    assert "/api/social/inbox/$id/reply" in (root / "lib/api.dart").read_text()
    assert "case 'social_lead':" in (root / "lib/ui/chat_screen.dart").read_text()
    assert "case 'social_lead':" in (root / "lib/state.dart").read_text()
    from app import push
    assert {"social_lead", "social_alert"} <= push.PUSH_KINDS and push.render("social_lead", {"text": "x"}, "Santosh")
    pv = (root / "server/app/static/privacy.html").read_text()
    assert "never messages anyone who has not written to you first" in pv and "does not read or send messages" not in pv
