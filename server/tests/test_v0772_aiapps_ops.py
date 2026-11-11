"""v0.772 HOOLA AI APPS - part C: the owner API + D3 (logs, correct, stats, gaps, cost alerts)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI, Header
from fastapi.testclient import TestClient

SOUL = {"name": "Sharma Kirana", "about": "Grocery shop in Pune",
        "facts": ["Open 9 am to 9 pm", "Delivery free above Rs 500"], "actions": ["ticket"],
        "limits": {"monthly_cap_inr": 100}}


@pytest.fixture
def api(env):
    from app.aiapps import api as API
    from app.aiapps import runtime as RT
    old = RT.ASK[0]
    RT.ASK[0] = lambda s, p, n: "We are open 9 am to 9 pm."

    def require_key():
        return True

    def current_tenant(x_tenant: str = Header("t1")):
        return x_tenant

    app = FastAPI()
    app.include_router(API.make_router(require_key, current_tenant))
    c = TestClient(app)
    yield c
    RT.ASK[0] = old


def _new(c, tenant="t1", soul=None):
    r = c.post("/api/aiapps", json={"name": "Sharma Kirana", "soul": soul or SOUL}, headers={"x-tenant": tenant})
    assert r.status_code == 200, r.text
    return r.json()


def _live(c, tenant="t1"):
    a = _new(c, tenant)
    r = c.post(f"/api/aiapps/{a['id']}/publish", json={"hash": a["draft_hash"], "note": "first"}, headers={"x-tenant": tenant})
    assert r.status_code == 200, r.text
    return a


def test_create_get_list_fenced(api):
    a = _new(api)
    assert a["errors"] == []
    assert api.get(f"/api/aiapps/{a['id']}").json()["name"] == "Sharma Kirana"
    assert [x["id"] for x in api.get("/api/aiapps").json()["apps"]] == [a["id"]]
    hb = {"x-tenant": "t2"}
    assert api.get(f"/api/aiapps/{a['id']}", headers=hb).status_code == 404
    assert api.get("/api/aiapps", headers=hb).json()["apps"] == []
    assert api.get(f"/api/aiapps/{a['id']}/logs", headers=hb).status_code == 404
    assert api.delete(f"/api/aiapps/{a['id']}", headers=hb).status_code == 404


def test_draft_errors_and_publish_tap(api):
    a = _new(api)
    bad = api.put(f"/api/aiapps/{a['id']}/draft", json={"soul": {**SOUL, "actions": ["pay"]}}).json()
    assert bad["errors"] and "pay" in bad["errors"][0]
    # a draft whose errors survive the checker cannot go live (a form app with no fields)
    form = api.put(f"/api/aiapps/{a['id']}/draft", json={"soul": {**SOUL, "kind": "form"}}).json()
    assert form["errors"]
    assert api.post(f"/api/aiapps/{a['id']}/publish", json={"hash": form["draft_hash"]}).status_code == 422
    good = api.put(f"/api/aiapps/{a['id']}/draft", json={"soul": SOUL}).json()
    assert good["errors"] == []
    assert api.post(f"/api/aiapps/{a['id']}/publish", json={}).status_code == 422          # no hash at all
    assert api.post(f"/api/aiapps/{a['id']}/publish", json={"hash": ""}).status_code == 409
    assert api.post(f"/api/aiapps/{a['id']}/publish", json={"hash": bad["draft_hash"]}).status_code == 409   # stale
    p = api.post(f"/api/aiapps/{a['id']}/publish", json={"hash": good["draft_hash"], "note": "go"})
    assert p.status_code == 200 and p.json()["version"] == 1
    vs = api.get(f"/api/aiapps/{a['id']}/versions").json()["versions"]
    assert [v["version"] for v in vs] == [1]
    rs = api.post(f"/api/aiapps/{a['id']}/restore", json={"version": 1}).json()
    assert rs["version"] == 2 and rs["live_version"] == 2
    assert api.post(f"/api/aiapps/{a['id']}/restore", json={"version": 9}).status_code == 404
    assert api.post(f"/api/aiapps/{a['id']}/status", json={"status": "paused"}).json()["status"] == "paused"
    assert api.post(f"/api/aiapps/{a['id']}/status", json={"status": "live"}).json()["status"] == "live"
    assert api.post(f"/api/aiapps/{a['id']}/status", json={"status": "gone"}).status_code == 400
    ch = api.post(f"/api/aiapps/{a['id']}/channels", json={"api": True, "whatsapp": "1234"}).json()["channels"]
    assert ch["api"] is True and ch["whatsapp"] == "1234" and ch["page"] is True


def test_preview_uses_draft(api):
    from app.aiapps import runtime as RT, store as ST
    a = _live(api)
    p = api.post(f"/api/aiapps/{a['id']}/preview", json={"text": "When are you open?"}).json()
    assert p["outcome"] == "model" and p["session_id"] and p["version"] == 0
    sid = p["session_id"]
    new = {**SOUL, "facts": ["Open 7 am to 11 pm"]}
    api.put(f"/api/aiapps/{a['id']}/draft", json={"soul": new})
    seen = []

    def fake(system, prompt, n):
        seen.append(system)
        return "We are open 7 am to 11 pm." if "7 am" in system else "We are open 9 am to 9 pm."
    RT.ASK[0] = fake
    p2 = api.post(f"/api/aiapps/{a['id']}/preview", json={"text": "When are you open?", "session_id": sid}).json()
    assert p2["session_id"] == sid and "7 am" in p2["reply"]
    live = RT.answer(ST.row("t1", a["id"]), "When are you open?", channel="page")
    assert "9 am" in live["reply"] and live["version"] == 1
    assert api.post(f"/api/aiapps/{a['id']}/preview", json={"text": "hi", "session_id": "ais_nope"}).status_code == 404
    assert api.post(f"/api/aiapps/{a['id']}/preview", json={"text": ""}).status_code == 400


def test_logs_correct_annotated(api):
    from app.aiapps import runtime as RT, store as ST
    a = _live(api)
    r = ST.row("t1", a["id"])
    RT.ASK[0] = lambda s, p, n: "UNKNOWN"
    u = RT.answer(r, "Do you sell organic atta?", channel="page")
    assert u["outcome"] == "unknown"
    RT.answer(r, "my OTP is 482913", channel="page")
    allr = api.get(f"/api/aiapps/{a['id']}/logs").json()["logs"]
    assert len(allr) == 2 and allr[0]["outcome"] == "refused"           # newest first
    assert "482913" not in allr[0]["question"]
    unk = api.get(f"/api/aiapps/{a['id']}/logs", params={"outcome": "unknown"}).json()["logs"]
    assert [x["id"] for x in unk] == [u["message_id"]]
    assert api.get(f"/api/aiapps/{a['id']}/logs", params={"q": "atta"}).json()["logs"][0]["id"] == u["message_id"]
    assert api.get(f"/api/aiapps/{a['id']}/logs", params={"outcome": "nope"}).status_code == 400
    url = f"/api/aiapps/{a['id']}/logs/{u['message_id']}/correct"
    assert api.post(url, json={"answer": ""}).status_code == 422
    assert api.post(url, json={"answer": "Yes. Send us your OTP to confirm."}).status_code == 422
    assert api.post(url, json={"answer": "Yes, card 4111 1111 1111 1111"}).status_code == 422
    ok = api.post(url, json={"answer": "Yes, organic atta is Rs 60 a kg. Never share your OTP with anyone."})
    assert ok.status_code == 200 and ok.json()["ok"], ok.text
    row = api.get(f"/api/aiapps/{a['id']}/logs", params={"outcome": "unknown"}).json()["logs"][0]
    assert row["corrected"].startswith("Yes, organic atta")
    again = RT.answer(ST.row("t1", a["id"]), "Do you sell organic atta?", channel="page")
    assert again["outcome"] == "annotated" and again["reply"].startswith("Yes, organic atta is Rs 60")
    assert api.post(f"/api/aiapps/{a['id']}/logs/aim_nope/correct", json={"answer": "x"}).status_code == 404


def _seed(app_id, tenant, rows):
    from app.aiapps.models import AiAppMessage
    from app.db import session
    with session() as s:
        for r in rows:
            s.add(AiAppMessage(app_id=app_id, tenant_id=tenant, **r))


def test_stats_exact(api):
    a = _live(api)
    now = datetime.now(timezone.utc)
    _seed(a["id"], "t1", [
        dict(session_id="s1", channel="page", outcome="answered", ms=100, created_at=now),
        dict(session_id="s1", channel="page", outcome="model", ms=300, inr=10.0, created_at=now),
        dict(session_id="s2", channel="whatsapp", outcome="unknown", ms=200, created_at=now),
        dict(session_id="s3", channel="api", outcome="refused", ms=0, created_at=now),
        dict(session_id="s3", channel="api", outcome="action", ms=400, created_at=now),
        dict(session_id="sp", channel="preview", outcome="unknown", ms=999, inr=5.0, created_at=now),   # hers: not counted
        dict(session_id="s9", channel="page", outcome="answered", ms=1, created_at=now - timedelta(days=20)),
    ])
    st = api.get(f"/api/aiapps/{a['id']}/stats", params={"days": 7}).json()
    t = st["totals"]
    assert t["messages"] == 5 and t["sessions"] == 3
    assert t["answered_share"] == 0.6 and t["unknown"] == 1 and t["refused"] == 1 and t["actions"] == 1
    assert t["avg_ms"] == 200
    assert t["satisfaction"] is None and "No ratings yet" in st["says"]
    assert t["inr_month"] == 15.0                                # month spend counts her preview too (the cap does)
    assert t["cap_inr"] == 100 and t["cap_percent"] == 15.0
    assert len(st["per_day"]) == 7 and st["per_day"][-1]["messages"] == 5
    # ratings: 2 good, 1 bad
    from app.aiapps.models import AiAppMessage
    from app.db import session
    with session() as s:
        ms = s.query(AiAppMessage).filter(AiAppMessage.channel != "preview", AiAppMessage.created_at >= now - timedelta(days=1)).all()
        for m, fb in zip(ms, (1, 1, -1)):
            m.feedback = fb
    t2 = api.get(f"/api/aiapps/{a['id']}/stats").json()["totals"]
    assert t2["satisfaction"] == round(2 / 3, 4) and t2["ratings"] == 3


def test_gaps_grouped(api):
    a = _live(api)
    now = datetime.now(timezone.utc)
    _seed(a["id"], "t1", [
        dict(session_id="a", channel="page", outcome="unknown", question="Do you deliver to Baner?", created_at=now - timedelta(hours=3)),
        dict(session_id="b", channel="page", outcome="unknown", question="do you deliver to baner", created_at=now - timedelta(hours=2)),
        dict(session_id="c", channel="whatsapp", outcome="unknown", question="Deliver to Baner please?", created_at=now - timedelta(hours=1)),
        dict(session_id="d", channel="page", outcome="unknown", question="Is there parking near the shop?", created_at=now),
        dict(session_id="e", channel="page", outcome="answered", question="Do you deliver to Baner?", created_at=now),
        dict(session_id="f", channel="preview", outcome="unknown", question="test test", created_at=now),
    ])
    g = api.get(f"/api/aiapps/{a['id']}/gaps").json()["gaps"]
    assert [x["count"] for x in g] == [3, 1]
    assert "Baner" in g[0]["question"] and g[0]["last_asked"]
    assert "parking" in g[1]["question"]


def test_tick_alerts_once(api, monkeypatch):
    from app.aiapps import ops as OP
    told = []
    monkeypatch.setattr(OP, "_note", lambda tenant, text: told.append((tenant, text)))
    a = _live(api)
    hidden = _live(api, tenant="__aiappproof__")
    now = datetime.now(timezone.utc)
    _seed(a["id"], "t1", [dict(channel="page", outcome="model", inr=79.0, created_at=now)])
    _seed(hidden["id"], "__aiappproof__", [dict(channel="page", outcome="model", inr=500.0, created_at=now)])
    assert OP.tick()["sent"] == 0 and told == []
    _seed(a["id"], "t1", [dict(channel="page", outcome="model", inr=2.0, created_at=now)])
    assert OP.tick()["sent"] == 1
    assert told[-1][0] == "t1" and "81%" in told[-1][1] and "Rs 100" in told[-1][1]
    assert OP.tick()["sent"] == 0                                   # never twice the same month
    _seed(a["id"], "t1", [dict(channel="page", outcome="model", inr=30.0, created_at=now)])
    assert OP.tick()["sent"] == 1 and "reached its limit" in told[-1][1]
    assert OP.tick()["sent"] == 0 and len(told) == 2
    assert all(t != "__aiappproof__" for t, _ in told)


def test_tick_jump_straight_to_100(api, monkeypatch):
    from app.aiapps import ops as OP
    told = []
    monkeypatch.setattr(OP, "_note", lambda tenant, text: told.append(text))
    a = _live(api)
    _seed(a["id"], "t1", [dict(channel="page", outcome="model", inr=150.0, created_at=datetime.now(timezone.utc))])
    assert OP.tick()["sent"] == 1 and "reached its limit" in told[0]
    assert OP.tick()["sent"] == 0 and len(told) == 1


def test_note_reaches_her_chat(api):
    from app.aiapps import ops as OP
    from app.db import session
    from app.db import Message
    OP._note("t1", "Sharma Kirana has used 81% of its Rs 100 monthly limit.")
    with session() as s:
        assert s.query(Message).filter(Message.display.like("%81% of its%")).count() == 1


def test_delete_removes_logs(api):
    from app.aiapps import runtime as RT, store as ST
    from app.aiapps.models import AiAppMessage
    from app.db import session
    a = _live(api)
    RT.answer(ST.row("t1", a["id"]), "When are you open?", channel="page")
    with session() as s:
        assert s.query(AiAppMessage).filter(AiAppMessage.app_id == a["id"]).count() == 1
    assert api.delete(f"/api/aiapps/{a['id']}").json()["ok"]
    with session() as s:
        assert s.query(AiAppMessage).filter(AiAppMessage.app_id == a["id"]).count() == 0
    assert api.get(f"/api/aiapps/{a['id']}").status_code == 404


def test_worker_slot_registered():
    from app import worker
    import inspect
    assert "aiapp_ops_jobs" in inspect.getsource(worker.tick)
    worker._aiapp_last = 0.0
    worker.aiapp_ops_jobs()       # never raises, even with nothing set up
