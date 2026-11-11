"""v0.772 HOOLA AI APPS part A: the one-line builder (D1), templates + trial (D5), export / import."""
import json

import pytest


def _fake(*answers):
    calls = []

    def ask(system, prompt, n):
        calls.append((system, prompt))
        return answers[min(len(calls) - 1, len(answers) - 1)]
    return ask, calls


GOOD = {"soul": {"name": "Sharma Kirana", "kind": "chat", "about": "Grocery shop in Kothrud, Pune.",
                 "facts": ["Open 9 am to 9 pm", "Free delivery above Rs 500"], "actions": ["ticket"],
                 "suggested": ["Do you deliver?"], "refuse": ["discounts"], "language": "auto"},
        "questions": ["Which days are you closed?"], "says": "Draft ready."}


def test_plan_returns_checked_soul(env):
    from app.aiapps import builder as B
    ask, calls = _fake(GOOD)
    B.ASK[0] = ask
    out = B.plan("t1", "Sharma Kirana, a grocery shop in Kothrud Pune, open 9 am to 9 pm, free delivery above Rs 500")
    assert out["errors"] == [], out
    assert out["soul"]["name"] == "Sharma Kirana"
    assert "ticket" in out["soul"]["actions"] and "handover" in out["soul"]["actions"]
    assert out["soul"]["facts"] == ["Open 9 am to 9 pm", "Free delivery above Rs 500"]
    assert "Which days are you closed?" in out["questions"]
    assert out["soul"]["limits"]["monthly_cap_inr"] == 500.0
    sys_prompt = calls[0][0]
    for word in ("ticket", "slots", "book", "handover", "long_text", "choice", "facts", "refuse"):
        assert word in sys_prompt
    assert len(calls) == 1
    from app.aiapps import store as ST
    assert ST.apps("t1") == []          # nothing saved


def test_invented_number_dropped(env):
    from app.aiapps import builder as B
    bad = json.loads(json.dumps(GOOD))
    bad["soul"]["facts"].append("Delivery charge Rs 40 below that")
    bad["soul"]["opening"] = "Get 10% off today!"
    B.ASK[0], _ = _fake(bad)
    out = B.plan("t1", "Sharma Kirana grocery, open 9 am to 9 pm, free delivery above Rs 500")
    assert "Delivery charge Rs 40 below that" not in out["soul"]["facts"]
    assert "Open 9 am to 9 pm" in out["soul"]["facts"]
    assert out["soul"]["opening"] == ""
    assert any("40" in w for w in out["warnings"]), out["warnings"]


def test_bad_action_refused_then_repaired(env):
    from app.aiapps import builder as B
    bad = json.loads(json.dumps(GOOD))
    bad["soul"]["actions"] = ["ticket", "refund_money"]
    ask, calls = _fake(bad, GOOD)
    B.ASK[0] = ask
    out = B.plan("t1", "Sharma Kirana grocery, open 9 am to 9 pm, free delivery above Rs 500")
    assert len(calls) == 2
    assert "refund_money" in calls[1][1] and "does not exist" in calls[1][1]
    assert out["errors"] == []
    assert "refund_money" not in out["soul"]["actions"]


def test_repair_kept_better_and_questions(env):
    from app.aiapps import builder as B
    bad = {"soul": {"name": "X", "kind": "robot", "about": "A salon", "actions": ["pay"]}}
    ask, calls = _fake(bad, bad)
    B.ASK[0] = ask
    out = B.plan("t1", "my salon in Nagpur")
    assert len(calls) == 2               # one repair round, no more
    assert out["soul"]["kind"] == "chat" and "pay" not in out["soul"]["actions"]
    assert any("removed from the draft" in w and "pay" in w for w in out["warnings"]), out["warnings"]
    assert out["questions"]              # unknowns come back as questions, never guesses
    assert any("timings" in q.lower() for q in out["questions"])


def test_plan_model_down_and_empty(env):
    from app.aiapps import builder as B
    from app.aiapps.store import AppError
    B.ASK[0] = lambda s, p, n: {}
    out = B.plan("t1", "Gupta Tailors in Akola")
    assert out["errors"] == [] and "Gupta Tailors" in out["soul"]["about"]
    with pytest.raises(AppError):
        B.plan("t1", "   ")


def test_every_template_is_clean(env):
    from app.aiapps import soul as SO
    from app.aiapps import templates as T
    cards = T.list()
    assert len(cards) >= 12
    keys = {c["key"] for c in cards}
    for k in ("kirana", "clinic", "school_office", "salon", "restaurant", "coaching", "real_estate", "ca_office", "gym",
              "homestay", "repair_shop", "pharmacy"):
        assert k in keys
    for c in cards:
        t = T.get(c["key"])
        got = SO.check(t["soul"])
        assert got["errors"] == [], (c["key"], got["errors"])
        assert 3 <= len(c["sample_questions"]) <= 5, c["key"]
        assert "[" in t["soul"]["about"], c["key"]           # her details are blanks
        for f in t["soul"]["facts"]:
            assert not any(ch.isdigit() for ch in f), (c["key"], f)
    ph = T.get("pharmacy")["soul"]
    assert "dosage" in ph["refuse"] and "medical advice" in ph["refuse"]
    assert [c["key"] for c in T.list("clinic")] == ["clinic"]


def test_trial_answers_and_saves_nothing(env):
    from app.aiapps import runtime as RT
    from app.aiapps import store as ST
    from app.aiapps import templates as T
    from app.aiapps.models import AiApp, AiAppMessage
    from app.db import session
    out = T.trial("pharmacy", "What dosage of paracetamol should I take?")
    assert out["outcome"] == "unknown" and out["saved"] is False
    RT.ASK[0] = lambda s, p, n: "Please tell us the medicine name and we will check stock."
    out = T.trial("kirana", "Do you have basmati rice?")
    assert out["outcome"] in ("model", "unknown"), out
    out = T.trial("kirana", "my parcel came damaged")
    assert out["outcome"] == "action"
    out = T.trial("tiffin", "", {"name": "Asha", "phone": "9000000000", "need": "Daily tiffin"})
    assert out["outcome"]
    assert ST.apps("t1") == []
    assert ST.apps(T.TRIAL_TENANT) == []
    with session() as s:
        assert s.query(AiApp).count() == 0
        assert s.query(AiAppMessage).count() == 0
        from app.seva.service import SevaTicket
        assert s.query(SevaTicket).filter(SevaTicket.tenant_id == T.TRIAL_TENANT).count() == 0


def test_use_creates_template_origin(env):
    from app.aiapps import store as ST
    from app.aiapps import templates as T
    a = T.use("t1", "salon", "Glow Salon")
    assert a["origin"] == "template" and a["template"] == "salon" and a["name"] == "Glow Salon"
    assert a["status"] == "draft" and a["errors"] == []
    assert len(ST.apps("t1")) == 1


def test_export_has_no_secrets(env):
    from app.aiapps import dsl as D
    from app.aiapps import store as ST
    from app.aiapps import templates as T
    a = T.use("t1", "kirana", "Sharma Kirana")
    ST.set_channels("t1", a["id"], whatsapp="1234567890", api=True)
    f = D.export("t1", a["id"])
    assert f["format"] == "hoola-aiapp" and f["v"] == 1 and f["name"] == "Sharma Kirana"
    txt = json.dumps(f)
    for bad in (a["code"], a["id"], "1234567890", "aik_", "channels", "sessions", "messages"):
        assert bad not in txt, bad


def test_import_check_and_confirm(env):
    from app.aiapps import dsl as D
    from app.aiapps import store as ST
    from app.aiapps import templates as T
    from app.aiapps.store import AppError
    a = T.use("t1", "clinic", "City Clinic")
    f = D.export("t1", a["id"])
    with pytest.raises(AppError) as e:
        D.import_check("t2", {"format": "dify", "soul": {}})
    assert e.value.code == 400
    with pytest.raises(AppError) as e:
        D.import_check("t2", "not json")
    assert e.value.code == 400
    big = dict(f, padding="x" * (70 * 1024))
    with pytest.raises(AppError) as e:
        D.import_check("t2", json.dumps(big))
    assert e.value.code == 413
    chk = D.import_check("t2", json.dumps(f))
    assert chk["errors"] == []
    needs = {n["what"]: n for n in chk["needs"]}
    assert needs["Knowledge base answers (Seva)"]["have"] is False
    hours = [n for n in chk["needs"] if "hours" in n["what"].lower()]
    assert hours and hours[0]["have"] is False and hours[0]["fix"]
    got = D.import_confirm("t2", f, "My Clinic")
    assert got["origin"] == "import" and got["status"] == "draft" and got["name"] == "My Clinic"
    assert len(ST.apps("t2")) == 1 and got["needs"]


def test_import_needs_seen_when_present(env):
    from app.aiapps import dsl as D
    from app.aiapps import templates as T
    from app.seva import service as SV
    from app.db import init_db
    init_db()
    a = T.use("t3", "kirana", "")
    f = D.export("t3", a["id"])
    SV.kb_add("t3", "Do you deliver?", "Yes, nearby.")
    chk = D.import_check("t3", f)
    seva = [n for n in chk["needs"] if "Seva" in n["what"]][0]
    assert seva["have"] is True


@pytest.fixture
def client(env):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.aiapps import builder_api
    app = FastAPI()
    app.include_router(builder_api.make_router(lambda: None, lambda: "t9"))
    return TestClient(app)


def test_routes(client):
    from app.aiapps import builder as B
    from app.aiapps import runtime as RT
    B.ASK[0], _ = _fake(GOOD)
    r = client.post("/api/aiapps/plan", json={"words": "Sharma Kirana open 9 am to 9 pm, delivery above Rs 500"})
    assert r.status_code == 200 and r.json()["soul"]["name"] == "Sharma Kirana"
    assert client.post("/api/aiapps/plan", json={"words": ""}).status_code == 400
    r = client.get("/api/aiapps/templates", params={"q": "salon"})
    assert r.status_code == 200 and r.json()[0]["key"] == "salon"
    assert set(r.json()[0]) >= {"key", "trade", "name", "about", "sample_questions", "actions"}
    RT.ASK[0] = lambda s, p, n: "UNKNOWN"
    r = client.post("/api/aiapps/templates/gym/trial", json={"text": "Can I take a trial?"})
    assert r.status_code == 200 and r.json()["saved"] is False
    assert client.post("/api/aiapps/templates/nope/trial", json={"text": "hi"}).status_code == 404
    r = client.post("/api/aiapps/templates/gym/use", json={"name": "Iron Gym"})
    assert r.status_code == 200 and r.json()["origin"] == "template"
    aid = r.json()["id"]
    f = client.get(f"/api/aiapps/{aid}/export").json()
    assert f["format"] == "hoola-aiapp"
    assert client.get("/api/aiapps/nope/export").status_code == 404
    r = client.post("/api/aiapps/import", json={"file": f})
    assert r.status_code == 200 and "needs" in r.json()
    assert client.post("/api/aiapps/import", json={"file": {"format": "x"}}).status_code == 400
    r = client.post("/api/aiapps/import/confirm", json={"file": f, "name": "Iron Gym 2"})
    assert r.status_code == 200 and r.json()["origin"] == "import" and r.json()["status"] == "draft"
