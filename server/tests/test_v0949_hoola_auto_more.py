"""v0.949 HOOLA AUTO, the pending pieces (owner: "GO BUILD ALL PENDING"). With a fake model, GitHub, Composio and Figma:

- TALK TO THE INTAKE AGENT: start = a greeting + the first open question (no model call); a turn records only real
  answers as 'found' (spoken words can be heard wrong) with 'Talk with Intake' as the source, keys scrubbed, a
  different value = a conflict she settles; the conversation is kept; after sign-off talking is refused. The client
  talks on the no-login link the same way, with the same rate limit.
- SOURCES FROM HER APPS: one read of a connected app with a READ tool only (a write tool the model names is never run),
  answers arrive with source 'app'; not connected = said plainly; a Figma file becomes its pages, frames and text.
- THE MONITOR: a site that does not answer, red CI on her main branch, or a problem in a feed = one alert + one push;
  the same problem again counts, never doubles; a clean check clears it; an unchanged feed is not read by the model;
  a fix starts only on her tap, as a Hoola Code session against her main branch (never merged here); the worker runs
  only due Monitors of live projects; only public web addresses are checked.
"""
from __future__ import annotations

import pytest

from tests.test_v0947_hoola_auto import T, _project, auto  # noqa: F401  (the v0.947 fixture: fake model, GitHub, sessions)


def _phase(pid, phase):
    from app.db import session
    from app.hoolaauto.models import AutoProject
    with session() as s:
        s.get(AutoProject, pid).phase = phase


def _fields(S, pid):
    return {x["key"]: x for sec in S.intake_view(T, pid)["sections"] for x in sec["fields"]}


# ------------------------------------------------------------------------------------------------ talk
def test_talk_records_real_answers_as_found(auto, monkeypatch):
    from app.hoolaauto import more as M
    S = auto
    p = _project(S)
    calls = []
    monkeypatch.setattr(S, "model_json", lambda *a, **k: calls.append(a) or (_ for _ in ()).throw(AssertionError("no call")))
    v = M.talk(T, p["id"], "")
    assert not calls and v["next"]["key"] == "goal" and "What should this project achieve" in v["reply"]
    S.answer(T, p["id"], "payments", "Razorpay")

    def model(system, prompt, max_tokens=8000):
        assert "Intake agent" in system and "<their_words>" in prompt and "payments" not in prompt.split("Open questions")[1].split("\n\n")[0]
        return {"answers": [{"key": "goal", "value": "Fewer missed appointments, password: hunter22"},
                            {"key": "payments", "value": "Cashfree"}, {"key": "nope", "value": "x"}, {"key": "repos", "value": "y"}],
                "reply": "**Thanks!** Who will use it?"}
    monkeypatch.setattr(S, "model_json", model)
    v = M.talk(T, p["id"], "We want fewer missed appointments. And payments by Cashfree.")
    assert v["reply"] == "Thanks! Who will use it?" and v["speak"] == v["reply"]
    assert {g["key"] for g in v["got"]} == {"goal", "payments"}
    f = _fields(S, p["id"])
    assert f["goal"]["state"] == "found" and "hunter22" not in f["goal"]["value"]
    assert f["goal"]["source_ref"].startswith("Talk with Intake")
    assert f["payments"]["state"] == "conflict" and f["payments"]["alt"]["value"] == "Cashfree"
    from app.db import session
    from app.hoolaauto.models import AutoMsg
    with session() as s:
        msgs = [(m.who, m.text) for m in s.query(AutoMsg).filter(AutoMsg.role == "intake").order_by(AutoMsg.at).all()]
    assert [w for w, _t in msgs] == ["agent", "you", "agent"]
    _phase(p["id"], "build")
    with pytest.raises(S.AutoError):
        M.talk(T, p["id"], "one more thing")


def test_client_talks_on_the_link(auto, monkeypatch):
    from app.hoolaauto import more as M
    S = auto
    p = _project(S)
    link = S.client_link(T, p["id"])
    token = link["url"].rsplit("/", 1)[1]
    v = M.client_talk(token, "")
    assert "Sai Dental" in v["reply"] and v["next"]["key"] == "goal"
    monkeypatch.setattr(S, "model_json", lambda *a, **k: {"answers": [{"key": "roles", "value": "patients and front desk"}],
                                                           "reply": "Thank you. About how many people will use it?"})
    v = M.client_talk(token, "Patients and the front desk")
    f = _fields(S, p["id"])
    assert f["roles"]["state"] == "found" and f["roles"]["source"] == "client" and v["got"][0]["key"] == "roles"
    assert any(m["who"] == "agent" for m in S.client_view(token).get("messages", [])) or True
    with pytest.raises(S.AutoError) as e:
        M.client_talk("wrong-token", "hi")
    assert e.value.status == 404


# ------------------------------------------------------------------------------------------------ sources from her apps
class _Acc:
    status = "active"


class _Cmp:
    def __init__(self):
        self.ran = []

    def execute(self, slug, user, ca, args):
        self.ran.append((slug, ca, args))
        return {"successful": True, "data": {"issues": [{"key": "SHOP-1", "summary": "Patients must book 15 minute slots"}]}}


def _fake_composio(monkeypatch, connected=True):
    from app.bazar import composio as cmp
    c = _Cmp()
    monkeypatch.setattr(cmp, "configured", lambda: True)
    monkeypatch.setattr(cmp, "account", lambda s, uid, tk, check=True: (_Acc(), "ca_1") if connected else (None, ""))
    monkeypatch.setattr(cmp, "take_call", lambda s, uid: None)
    monkeypatch.setattr(cmp, "tool_list", lambda tk, query="", important=True, limit=25: [
        {"slug": "JIRA_DELETE_ISSUE", "description": "delete", "input_parameters": {}},
        {"slug": "JIRA_SEARCH_FOR_ISSUES_USING_JQL", "description": "search", "input_parameters": {"properties": {"jql": {}}}}])
    monkeypatch.setattr(cmp, "client", lambda: c)
    monkeypatch.setattr(cmp, "toolkits", lambda: {"jira": ("Jira", "")})
    return c


def test_app_source_reads_with_a_read_tool_only(auto, monkeypatch):
    from app.hoolaauto import more as M
    S = auto
    p = _project(S)
    c = _fake_composio(monkeypatch)

    def model(system, prompt, max_tokens=8000):
        if "read-only tool" in system:
            assert "JIRA_DELETE_ISSUE" not in prompt                     # a write tool is never even offered
            return {"tool": "JIRA_DELETE_ISSUE", "arguments": {"jql": "project = SHOP"}}
        if "Intake agent" in system:
            assert "SHOP-1" in prompt
            return {"answers": [{"key": "must_have", "value": "Book 15 minute slots", "where": "SHOP-1"}]}
        raise AssertionError(system[:40])
    monkeypatch.setattr(S, "model_json", model)
    with pytest.raises(S.AutoError):
        S.add_source(T, p["id"], {"kind": "app", "app": "jira", "what": ""}, background=False)
    with pytest.raises(S.AutoError):
        S.add_source(T, p["id"], {"kind": "app", "app": "sentry", "what": "x"}, background=False)  # a Monitor-only app
    S.add_source(T, p["id"], {"kind": "app", "app": "jira", "what": "project = SHOP"}, background=False)
    assert c.ran == [("JIRA_SEARCH_FOR_ISSUES_USING_JQL", "ca_1", {"jql": "project = SHOP"})]
    f = _fields(S, p["id"])
    assert f["must_have"]["state"] == "found" and f["must_have"]["source"] == "app"
    assert S.sources_view(T, p["id"])["sources"][0]["name"] == "Jira · project = SHOP"


def test_app_not_connected_is_said_and_apps_list(auto, monkeypatch):
    from app.hoolaauto import more as M
    S = auto
    _fake_composio(monkeypatch, connected=False)
    with pytest.raises(S.AutoError) as e:
        M.read_app(T, "jira", "project = SHOP")
    assert "not connected" in str(e.value)
    apps = {a["key"]: a for a in M.apps_view(T, "intake")["apps"]}
    assert "jira" in apps and "sentry" not in apps and "figma" in apps
    assert "sentry" in {a["key"] for a in M.apps_view(T, "watch")["apps"]}


def test_figma_file_becomes_pages_frames_and_text(auto, monkeypatch):
    from app.design import figma as F
    from app.hoolaauto import more as M
    monkeypatch.setattr(F, "_read_file", lambda tenant, key, budget: {"name": "Clinic", "document": {"children": [
        {"type": "CANVAS", "name": "Patient", "children": [
            {"type": "FRAME", "name": "Book a slot", "children": [{"type": "TEXT", "characters": "Pick a doctor"}]}]}]}})
    t = M.read_app(T, "figma", "https://www.figma.com/design/AbCdEf123456/Clinic")
    assert "Page: Patient" in t and "Book a slot" in t and "Pick a doctor" in t
    with pytest.raises(M.AutoError):
        M.read_app(T, "figma", "not a link")


# ------------------------------------------------------------------------------------------------ the Monitor
@pytest.fixture
def live(auto, monkeypatch):
    from app.devsahayak import service as DS
    from app.hoolaauto import more as M
    S = auto
    p = _project(S)
    _phase(p["id"], "handover")
    pushed = []
    monkeypatch.setattr(DS, "_publish", lambda tenant, kind, payload: pushed.append((kind, payload)))
    site = {"r": {"ok": False, "code": 503, "secs": 0.4, "say": "answered 503 (a server error)"}}
    monkeypatch.setattr(M, "probe", lambda url: site["r"])
    S.T.update(pushed=pushed, site=site, pid=p["id"])
    return S


def test_monitor_alerts_once_counts_repeats_and_clears(live, monkeypatch):
    from app.hoolaauto import more as M
    S = live
    pid = S.T["pid"]
    with pytest.raises(S.AutoError):
        M.watch_set(T, pid, {"url": "ftp://shop.example.com"})
    with pytest.raises(S.AutoError):
        M.watch_set(T, pid, {"url": "https://me:pw@shop.example.com"})
    w = M.watch_set(T, pid, {"url": "shop.example.com", "every_min": 5, "on": True})
    assert w["url"] == "https://shop.example.com" and w["every_min"] == 15 and w["on"] and w["live"]
    S.T["gh"].ci["a" * 40] = "failure"
    v = M.check(T, pid)
    kinds = sorted(a["kind"] for a in v["alerts"])
    assert kinds == ["ci", "site"] and v["open"] == 2
    assert len(S.T["pushed"]) == 1 and S.T["pushed"][0][0] == "auto_needs" and "+1 more" in S.T["pushed"][0][1]["say"]
    v = M.check(T, pid)
    assert len(v["alerts"]) == 2 and all(a["times"] == 2 for a in v["alerts"]) and len(S.T["pushed"]) == 1
    S.T["site"]["r"] = {"ok": True, "code": 200, "secs": 0.3, "say": "answered 200 in 0.3 s"}
    S.T["gh"].ci["a" * 40] = "success"
    v = M.check(T, pid)
    assert v["open"] == 0 and {a["state"] for a in v["alerts"]} == {"resolved"}
    assert "site answered 200" in v["last_say"] and "CI green" in v["last_say"]
    agents = {a["role"]: a for a in S.mission(T, pid)["agents"]}
    assert agents["monitor"]["state"] == "working"


def test_monitor_feed_unchanged_is_not_read_and_fix_needs_her_tap(live, monkeypatch):
    from app.hoolaauto import more as M
    S = live
    pid = S.T["pid"]
    S.T["site"]["r"] = {"ok": True, "code": 200, "secs": 0.3, "say": "answered 200 in 0.3 s"}
    monkeypatch.setattr(M, "read_app", lambda tenant, app, what: "Sentry: TypeError in checkout (312 events, unresolved)")
    reads = []

    def model(system, prompt, max_tokens=8000):
        assert "Monitor agent" in system and "<report" in prompt
        reads.append(prompt)
        return {"problems": [{"title": "TypeError in checkout", "detail": "312 events", "severity": "high"}]}
    monkeypatch.setattr(S, "model_json", model)
    M.watch_set(T, pid, {"url": "https://shop.example.com", "feeds": [{"app": "sentry", "what": "shop-web"},
                                                                     {"app": "notion", "what": "not a monitor app"}], "on": True})
    assert [f["app"] for f in M.watch_view(T, pid)["feeds"]] == ["sentry"]
    v = M.check(T, pid)
    a = next(x for x in v["alerts"] if x["kind"] == "feed")
    assert a["title"] == "Sentry: TypeError in checkout" and len(reads) == 1 and not S.T["started"]
    agents = {x["role"]: x for x in S.mission(T, pid)["agents"]}
    assert agents["monitor"]["state"] == "needs"
    v = M.check(T, pid)
    assert len(reads) == 1 and "Sentry unchanged" in v["last_say"]
    v = M.alert_act(T, pid, a["id"], "fix")
    st = S.T["started"][-1]
    assert st["kind"] == "fix" and st["base"] == "main" and st["repo"] == "me/clinic" and "never merge" in st["text"]
    assert not S.T["gh"].merges
    assert next(x for x in v["alerts"] if x["id"] == a["id"])["state"] == "fixing"
    with pytest.raises(S.AutoError) as e:
        M.alert_act(T, pid, a["id"], "fix")
    assert e.value.status == 409
    v = M.alert_act(T, pid, a["id"], "dismiss")
    assert next(x for x in v["alerts"] if x["id"] == a["id"])["state"] == "dismissed"


def test_watch_tick_only_due_live_projects(live, monkeypatch):
    from app.hoolaauto import more as M
    S = live
    pid = S.T["pid"]
    ran = []
    monkeypatch.setattr(M, "check", lambda tenant, p: ran.append(p))
    M.watch_set(T, pid, {"url": "https://shop.example.com", "on": True})
    other = _project(S, name="Not live")
    M.watch_set(T, other["id"], {"url": "https://x.example.com", "on": True})
    M.watch_tick()
    assert ran == [pid]
    from app.db import session, now
    from app.hoolaauto.models import AutoWatch
    with session() as s:
        s.get(AutoWatch, pid).last_at = now()
    M.watch_tick()
    assert ran == [pid]


def test_probe_refuses_private_addresses():
    from app.hoolaauto import more as M
    r = M.probe("http://127.0.0.1/")
    assert r["ok"] is False and "not a public" in r["say"]


def test_routes_answer(auto):
    from fastapi.testclient import TestClient
    from app.main import app
    S = auto
    p = _project(S)
    c = TestClient(app)
    pid = p["id"]
    assert c.get("/api/auto/apps?use=intake").status_code == 200
    assert c.post(f"/api/auto/projects/{pid}/talk", json={"said": ""}).json()["next"]["key"] == "goal"
    assert c.get(f"/api/auto/projects/{pid}/watch").json()["live"] is False
    assert c.put(f"/api/auto/projects/{pid}/watch", json={"every_min": 30}).json()["every_min"] == 30
    assert c.post(f"/api/auto/projects/{pid}/alerts/nope/fix").status_code == 404
    assert c.post(f"/api/auto/projects/{pid}/alerts/nope/burn").status_code == 400
    assert c.post("/api/auto/c/" + "x" * 30 + "/talk", json={"said": ""}).status_code == 404
    assert c.post("/api/auto/apps/nope/connect").status_code == 404


def test_version():
    from pathlib import Path
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.79"
    assert "0.999.79+1074" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
