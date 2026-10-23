"""Community Sahayak (samudaay): rules, member register, approved welcome, FAQ-only answers + questions to her, early
warnings, moderation only on her tap (with reason log), weekly report, Telegram adapter (webhook secret, sealed token), Hoola
Mandali adapter, tools + API."""
import asyncio
from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.samudaay.models  # noqa: F401  (tables for init_db)
from tests.test_life import conv_ctx

T = "default"
TOKEN = "123456789:" + "A" * 35


class Fake:
    platform = "fake"
    caps = {"send", "delete", "mute", "unmute", "remove", "ban", "unban", "join"}

    def __init__(self):
        self.calls = []

    def send(self, comm, text, reply_to=""):
        self.calls.append(("send", text, reply_to))
        return str(len(self.calls))

    def delete(self, comm, msg_ref):
        self.calls.append(("delete", msg_ref))

    def mute(self, comm, user_ref, until):
        self.calls.append(("mute", user_ref))

    def unmute(self, comm, user_ref):
        self.calls.append(("unmute", user_ref))

    def remove(self, comm, user_ref):
        self.calls.append(("remove", user_ref))

    def ban(self, comm, user_ref):
        self.calls.append(("ban", user_ref))

    def unban(self, comm, user_ref):
        self.calls.append(("unban", user_ref))

    def join_answer(self, comm, user_ref, yes):
        self.calls.append(("join", user_ref, yes))


@pytest.fixture
def sam(env, monkeypatch):
    from app.samudaay import adapters as A
    from app.samudaay import service as S
    ev = []
    monkeypatch.setattr(S, "_publish", lambda t, k, p: ev.append((k, p)))
    monkeypatch.setattr(S, "_ai_json", lambda *a, **k: {})
    monkeypatch.setattr(S, "WELCOME_GAP_S", 60)
    fake = Fake()
    A.register("fake", fake)
    yield S, fake, ev
    A.register("fake", None)
    A.set_telegram_transport(None)


def make_comm(S, name="Yoga Batch Akola", **kw):
    from app.db import session
    from app.samudaay.models import SamCommunity
    with session() as s:
        c = SamCommunity(tenant_id=T, platform="fake", chat_id="-100" + str(abs(hash(name)) % 10**6), name=name, **kw)
        s.add(c)
        s.flush()
        return c.id


def join(S, cid, ref, name, src="link", at=None):
    from app.db import now
    return S.ingest(T, cid, {"type": "join", "user": {"ref": ref, "name": name, "username": ""}, "source": src, "at": at or now()})


def say(S, cid, ref, name, text, msg="", at=None, links=None, fwd=False):
    from app.db import now
    return S.ingest(T, cid, {"type": "message", "user": {"ref": ref, "name": name, "username": ""}, "msg_ref": msg or str(abs(hash(text)) % 99999),
                             "text": text, "links": links or [], "forwarded": fwd, "at": at or now()})


def kinds(ev, k):
    return [p for kk, p in ev if kk == k]


def test_rules():
    from app.samudaay import rules as R
    assert R.abuse("tu chutiya hai")["kind"] == "abuse" and R.abuse("tu chuuuutiya hai")["severity"] == "medium"
    assert R.abuse("zavadya kuthla") and R.abuse("ghar aake maar dunga")["kind"] == "threat"
    assert R.abuse("तुझे जान से मार दूंगा")["kind"] == "threat"
    assert R.abuse("class kab hai? subah 7 baje?") is None and R.abuse("Pass the class assignment") is None
    assert R.abuse("tu chutiya hai", ignore={"chutiya"}) is None
    s = R.scam("Ghar baithe daily earning ₹5000, join karo bit.ly/abc12")
    assert s["kind"] == "scam" and s["severity"] == "high"
    assert R.scam("SBI KYC update karo sbi-kyc-update.xyz/login")["severity"] == "high"
    assert R.scam("Notes yahan hain: https://mysite.in/notes", allowed={"mysite.in"}) is None
    assert R.scam("dekho https://example.com/x") is None
    assert R.scam("dekho https://example.com/x", new_member=True, links_policy="none")
    assert "aadhaar" in R.personal_data("mera aadhaar 2345 6789 0124 hai") or R.personal_data("otp is 482913")
    assert R.rumour("Ye message 10 groups mein forward karo warna nuksaan")["kind"] == "misinfo"
    assert R.is_question("Class kitne baje hai") and R.is_question("fees kitni hai?") and not R.is_question("ok thanks")
    f, sc = R.best_faq("class kitne baje hai?", [{"question": "Class ka time kya hai", "keywords": ["timing"]},
                                                 {"question": "Fees kitni hai", "keywords": []}])
    assert f["question"].startswith("Class") and sc >= R.AUTO_ANSWER
    assert R.best_faq("parking hai kya?", [{"question": "Fees kitni hai"}])[0] is None
    assert R.mood("bahut kharab service, refund nahi mila") < 0 and R.mood("thank you, badhiya class") > 0
    assert R.topic("net bahut slow hai, wifi band") == "internet"
    assert "{name}" in R.DEFAULT_WELCOME["marathi"] and R.template_problems("Hi {phone}")
    assert R.health({"members": 100, "active": 30, "joins": 5, "leaves": 1})["score"] >= 75


def test_welcome_faq_and_questions(sam):
    S, fake, ev = sam
    cid = make_comm(S, rules="izzat se baat, spam nahi")
    join(S, cid, "u1", "Asha")
    assert fake.calls == []                                                           # no approved message -> nothing goes out
    d = S.draft_template(T, comm=cid)
    assert kinds(ev, "samudaay_template") and "Asha" in d["preview"]
    with pytest.raises(S.SamError):
        S.approve_template(T, d["id"], d["hash"])                                     # not a tap
    with pytest.raises(S.SamError):
        S.approve_template(T, d["id"], "x" * 64, by_tap=True)
    S.approve_template(T, d["id"], d["hash"], by_tap=True)
    join(S, cid, "u2", "Ravi")
    assert fake.calls[-1][0] == "send" and "Asha, Ravi" in fake.calls[-1][1] and "izzat se baat" in fake.calls[-1][1]
    n = len(fake.calls)
    join(S, cid, "u3", "Meena")                                                       # inside the 60 s gap: waits for tick
    assert len(fake.calls) == n
    from app.db import session
    from app.samudaay.models import SamCommunity, SamMember
    with session() as s:
        s.get(SamCommunity, cid).last_welcome_at = None
    S.tick()
    assert "Meena" in fake.calls[-1][1]
    with session() as s:
        assert s.query(SamMember).filter_by(user_ref="u3").one().welcomed
    # FAQ answers only from her approved FAQ
    S.add_faq(T, "Class ka time kya hai", "Roz subah 7 se 8 baje, Sunday chhutti.", comm=cid)
    r = say(S, cid, "u2", "Ravi", "class kitne baje hai?", msg="11")
    assert r["answer"]["by"] == "faq" and fake.calls[-1] == ("send", "Roz subah 7 se 8 baje, Sunday chhutti.", "11")
    r = say(S, cid, "u3", "Meena", "Parking ki suvidha hai kya?", msg="12")
    assert r["answer"]["by"] == "asked_owner" and kinds(ev, "samudaay_question")[-1]["text"].startswith("Parking")
    n = len(fake.calls)
    r2 = say(S, cid, "u1", "Asha", "parking ki suvidha hai kya", msg="13")
    assert r2["answer"]["by"] == "counted" and len(fake.calls) == n                   # no guess, no second ping
    qid = r["answer"]["question_id"]
    assert S.questions(T)[0]["count"] == 2
    a = S.answer_question(T, qid, "Haan, gate ke paas 2-wheeler parking hai.")
    assert a["sent"] and fake.calls[-1] == ("send", "Haan, gate ke paas 2-wheeler parking hai.", "12")
    r3 = say(S, cid, "u4", "Kiran", "Parking ki suvidha hai?", msg="14")
    assert r3["answer"]["by"] == "faq"                                                # learned from her answer
    assert S.report(T, cid)["now"]["faq_answers"] == 2


def test_moderation_only_on_her_tap(sam):
    S, fake, ev = sam
    cid = make_comm(S)
    join(S, cid, "s1", "Spammer Sam")
    join(S, cid, "a1", "Admin Anil")
    S.set_roles(T, "Admin Anil", ["admin"], cid)
    r = say(S, cid, "s1", "Spammer Sam", "Ghar baithe daily earning ₹3000! Join: bit.ly/xyz12 pay to earn@ybl", msg="50")
    assert "scam" in r["alerts"]
    al = kinds(ev, "samudaay_alert")[-1]
    assert al["severity"] == "high" and {"delete_post", "ban"} <= {x["kind"] for x in al["suggest"]}
    assert fake.calls == []                                                            # nothing removed by itself
    from app.agent.samudaay_tools import SAMUDAAY_HANDLERS as H
    from app.agent.tools import Ctx, ToolError
    ctx = conv_ctx()
    run = lambda tool, c=ctx, **a: asyncio.run(H[tool](c, **a))     # noqa: E731
    card = run("samudaay", action="moderate", kind="remove", member="Spammer Sam", reason="scam link")
    assert card["needs_tap"] and card["status"] == "pending" and fake.calls == []
    with pytest.raises(S.SamError):
        S.decide(T, card["id"], True, card["hash"])                                   # not a tap -> refused
    assert fake.calls == []
    with pytest.raises(ToolError):
        run("samudaay", action="moderate", kind="ban", member="Admin Anil", reason="x")   # admins are never targets
    noreason = S.request_action(T, "mute", cid, member="Spammer Sam")
    with pytest.raises(S.SamError, match="Wajah"):
        S.decide(T, noreason["id"], True, noreason["hash"], by_tap=True)
    done = S.decide(T, card["id"], True, card["hash"], by_tap=True)
    assert done["status"] == "done" and fake.calls == [("remove", "s1")]
    assert S.members(T, cid, "removed")[0]["name"] == "Spammer Sam"
    assert S.reason_log(T)[0]["note"] == "scam link"
    # one tap on the alert card
    say(S, cid, "x1", "Troll", "tu chutiya hai, bhosdike", msg="60")
    al2 = kinds(ev, "samudaay_alert")[-1]
    assert al2["kind"] == "abuse"
    S.alert_act(T, al2["id"], "delete_post", by_tap=True)
    assert fake.calls[-1] == ("delete", "60") and S.alerts(T, status="handled")
    # announcement card -> rejected -> nothing sent
    ann = run("samudaay", action="announce", text="Kal class 6 baje hogi.")
    S.decide(T, ann["id"], False, by_tap=True)
    assert all(c[0] != "send" for c in fake.calls)
    ann2 = run("samudaay", action="announce", text="Kal class 6 baje hogi.")
    S.decide(T, ann2["id"], True, ann2["hash"], by_tap=True)
    assert fake.calls[-1] == ("send", "Kal class 6 baje hogi.", "")
    with pytest.raises(ToolError, match="Bot token"):
        run("samudaay", action="announce", text="token " + TOKEN)
    staff = Ctx(T, ctx.conversation_id, actor="staff:x")
    with pytest.raises(ToolError):
        run("samudaay", c=staff, action="faq", question="q", answer="a")
    assert run("samudaay", c=staff, action="moderate", kind="warn", member="Troll")["needs_tap"]
    # dismiss teaches the group
    say(S, cid, "x2", "Neha", "humari website dekho https://yogaakola.in/batch", msg="70", links=[])
    S.save_community(T, cid, links_policy="none")
    say(S, cid, "x2", "Neha", "naya link https://yogaakola.in/fees", msg="71")
    a3 = kinds(ev, "samudaay_alert")[-1]
    S.dismiss_alert(T, a3["id"], allow_site=True)
    assert "yogaakola.in" in S.communities(T)[0]["links_allowed"]
    assert not say(S, cid, "x2", "Neha", "aur https://yogaakola.in/time", msg="72")["alerts"]
    assert run("samudaay_dekho", what="rules")["legal"]


def test_trends_report_and_retention(sam):
    S, fake, ev = sam
    from app.db import now, session
    from app.samudaay.models import SamPost
    cid = make_comm(S, name="Akot Fiber Users")
    t0 = now()
    for i in range(12):
        join(S, cid, f"m{i}", f"User {i}", at=t0 - timedelta(days=9))
    for i in range(10):
        say(S, cid, f"m{i}", f"User {i}", f"badhiya service thanks ({i} saal se)", at=t0 - timedelta(days=3, minutes=i))
    for i in range(6):
        say(S, cid, f"m{i}", f"User {i}", f"net bahut slow hai, kharab service, complaint ghar {i}", at=t0 - timedelta(minutes=30 + i))
    for i in range(6, 10):
        S.ingest(T, cid, {"type": "leave", "user": {"ref": f"m{i}", "name": f"User {i}"}, "at": t0})
    made = S.scan_trends(T, cid)
    got = {a["kind"] for a in kinds(ev, "samudaay_alert")}
    assert {"negativity", "leaving", "complaints"} <= got and len(made) == 3
    assert len(S.scan_trends(T, cid)) == 3 and len(kinds(ev, "samudaay_alert")) == len(got)   # same day: no repeat cards
    rp = S.report(T, cid, 7)
    assert rp["now"]["leaves"] == 4 and rp["health"]["score"] < 75 and rp["tips"]
    # weekly card on her report day
    from app.samudaay.models import SamCommunity
    local = now().astimezone(S._tz(T))
    with session() as s:
        c = s.get(SamCommunity, cid)
        c.report_day, c.report_time = local.weekday(), (local - timedelta(minutes=5)).strftime("%H:%M")
    if local.hour * 60 + local.minute >= 5:
        S.tick()
        assert kinds(ev, "samudaay_week") and kinds(ev, "samudaay_week")[0]["community"] == "Akot Fiber Users"
    with session() as s:
        s.add(SamPost(tenant_id=T, community_id=cid, member_id="m1", text="purani baat", at=now() - timedelta(days=100)))
    assert S.tick()["trimmed"] == 1
    r = S.register_file(T, cid)
    assert r["file"]["name"].endswith(".xlsx")
    mid = next(m["id"] for m in S.members(T, cid) if m["name"] == "User 1")
    S.forget_member(T, "User 1", cid)
    with session() as s:
        assert all(p.text == "" for p in s.query(SamPost).filter_by(member_id=mid))
    assert all(m["name"] != "User 1" for m in S.members(T, cid))


def test_telegram_adapter(sam, monkeypatch):
    S, fake, ev = sam
    from app.samudaay import adapters as A
    calls = []

    def tp(token, method, params):
        calls.append((method, params))
        if method == "getMe":
            return {"id": 999, "is_bot": True, "username": "yoga_helper_bot"}
        if method == "sendMessage":
            return {"message_id": 5000 + len(calls)}
        return True
    A.set_telegram_transport(tp)
    with pytest.raises(S.SamError, match="PUBLIC_BASE_URL"):
        S.connect_telegram(T, TOKEN)
    monkeypatch.setattr(S, "_base_url", lambda: "https://hoola.example.in")
    with pytest.raises(S.SamError):
        S.connect_telegram(T, "not-a-token")
    v = S.connect_telegram(T, TOKEN)
    wh = next(p for m, p in calls if m == "setWebhook")
    assert v["username"] == "yoga_helper_bot" and wh["url"].startswith("https://hoola.example.in/api/samudaay/hook/telegram/")
    assert "chat_member" in wh["allowed_updates"] and "chat_join_request" in wh["allowed_updates"]
    secret, hook = wh["secret_token"], wh["url"].rsplit("/", 1)[1]
    from app.db import session
    from app.samudaay.models import SamBot
    with session() as s:
        b = s.query(SamBot).one()
        assert TOKEN not in b.token_enc and secret not in b.secret_hash               # sealed / hashed only
    from app.samudaay.api import make_router
    api = FastAPI()
    api.include_router(make_router(lambda: None, lambda: T))
    cl = TestClient(api)
    url = f"/api/samudaay/hook/telegram/{hook}"
    chat = {"id": -100777, "type": "supergroup", "title": "Yoga Akola"}
    added = {"update_id": 1, "my_chat_member": {"chat": chat, "date": 1761200000, "new_chat_member": {"status": "administrator"},
                                                "old_chat_member": {"status": "left"}}}
    assert cl.post(url, json=added, headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"}).status_code == 403
    assert cl.post(url, json=added).status_code == 403
    H = {"X-Telegram-Bot-Api-Secret-Token": secret}
    assert cl.post(url, json=added, headers=H).status_code == 200
    comm = S.communities(T)[0]
    assert comm["platform"] == "telegram" and comm["name"] == "Yoga Akola" and kinds(ev, "samudaay_info")
    joined = {"update_id": 2, "chat_member": {"chat": chat, "date": 1761200100, "from": {"id": 42},
                                              "old_chat_member": {"status": "left", "user": {"id": 42}},
                                              "new_chat_member": {"status": "member", "user": {"id": 42, "first_name": "Sunita"}},
                                              "invite_link": {"name": "Instagram bio"}}}
    cl.post(url, json=joined, headers=H)
    m = S.members(T)[0]
    assert m["name"] == "Sunita" and m["source"] == "Instagram bio"
    assert cl.post(url, json=joined, headers=H).json()["dup"]                            # same update twice -> once
    msg = {"update_id": 3, "message": {"message_id": 77, "date": 1761200200, "chat": chat, "from": {"id": 42, "first_name": "Sunita"},
                                       "text": "KYC update karo warna account band: click here",
                                       "entities": [{"type": "text_link", "offset": 0, "length": 3, "url": "http://sbi-secure.top/kyc"}]}}
    cl.post(url, json=msg, headers=H)
    al = kinds(ev, "samudaay_alert")[-1]
    assert al["kind"] == "scam" and "sbi-secure.top" in al["evidence"]["links"]           # hidden text_link caught
    r = cl.post(f"/api/samudaay/alerts/{al['id']}/act", json={"kind": "ban", "reason": "phishing link"})
    assert r.status_code == 200 and r.json()["status"] == "done", r.text
    assert ("banChatMember", {"chat_id": "-100777", "user_id": 42, "revoke_messages": False}) in calls
    jr = {"update_id": 4, "chat_join_request": {"chat": chat, "from": {"id": 55, "first_name": "Crypto Profit King"}, "date": 1761200300,
                                                "bio": "Daily earning guaranteed return 200%"}}
    cl.post(url, json=jr, headers=H)
    card = kinds(ev, "samudaay_join")[-1]
    assert card["flags"] and not any(m == "approveChatJoinRequest" for m, _ in calls)
    assert cl.post(f"/api/samudaay/joins/{card['id']}", json={"yes": False}).json()["status"] == "declined"
    assert any(m == "declineChatJoinRequest" for m, _ in calls)
    assert cl.get("/api/samudaay").json()["bot"]["username"] == "yoga_helper_bot"
    assert "token" not in str(cl.get("/api/samudaay/telegram").json()).lower().replace("telegram", "")
    left = {"update_id": 5, "message": {"message_id": 78, "date": 1761200400, "chat": chat, "left_chat_member": {"id": 999}}}
    cl.post(url, json=left, headers=H)
    assert cl.delete("/api/samudaay/telegram").status_code == 200
    assert cl.post(url, json={"update_id": 9}, headers=H).status_code == 403             # removed bot: hook dead


def test_parse_telegram():
    from app.samudaay import adapters as A
    chat = {"id": -1, "type": "group", "title": "G"}
    ev = A.parse_telegram({"message": {"message_id": 1, "date": 1, "chat": chat, "new_chat_members": [{"id": 7, "first_name": "Om"}, {"id": 9}]}}, "9")
    assert [e["type"] for e in ev] == ["join", "bot_added"]
    ev = A.parse_telegram({"chat_member": {"chat": chat, "date": 1, "old_chat_member": {"status": "member", "user": {"id": 7}},
                                           "new_chat_member": {"status": "kicked", "user": {"id": 7}}}})
    assert ev[0]["type"] == "banned"
    ev = A.parse_telegram({"message": {"message_id": 2, "date": 1, "chat": chat, "from": {"id": 9}, "text": "mine"}}, "9")
    assert ev == []                                                                      # the bot's own messages ignored


def test_hoola_mandali(sam):
    S, fake, ev = sam
    from tests.test_net_groups import _three
    _three()
    from app.net import groups as grp
    g = grp.create("default", "FNW Field", members=["Kunal", "@swati.sales"])
    grp.answer_invite("kunal", g["gid"], "accept")
    v = S.link_hoola(T, "FNW Field")
    assert v["platform"] == "hoola" and {m["name"] for m in S.members(T)} >= {"Kunal ki Meera"}
    grp.answer_invite("swati", g["gid"], "accept")
    grp.post("kunal", g["gid"], "message", "Saala tu kamina hai")
    grp.post("kunal", g["gid"], "message", "Akola OLT kab theek hoga?")
    S.tick()
    assert len(S.members(T)) == 2
    assert kinds(ev, "samudaay_alert")[-1]["kind"] == "abuse"
    assert kinds(ev, "samudaay_question")
    x = S.request_action(T, "remove", v["id"], member="Kunal ki Meera", reason="gaali")
    S.decide(T, x["id"], True, x["hash"], by_tap=True)
    assert all(m["label"] != "Kunal ki Meera" for m in grp.detail("default", g["gid"])["members"])
    bad = S.request_action(T, "delete_post", v["id"], post=S.alerts(T, status="")[0]["post_id"])
    assert S.decide(T, bad["id"], True, bad["hash"], by_tap=True)["status"] == "failed"     # Mandali can't delete posts: said plainly
