"""v0.407 EK DIMAAG + HOOLA ARCHITECT (web Step 2 = W1 + W13 of docs/WEB_PLATFORM_PLAN.md).

W1: a website's web app runs on App Sahayak's backend + the DIMAAG logic engine. Linking moves every member and row over
unchanged (old logins keep working), the site's own /api/site-app/<site> addresses stay, and the logic (workflows with
maker-checker approvals, relations) runs on every write. An unlinked site is served exactly as before.
W13: her ONE line -> a spec card (pages, users, data, rules, features) she approves module by module -> the website and its
app brain are built from it. Proof: a school portal from one brief."""
import json

import pytest
from fastapi.testclient import TestClient

from tests.test_v0305_web_apps import DESIGN, T, app_site  # noqa: F401  (fixture)
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

WORKFLOW = {"summary": "Order: Naya -> Ban raha (staff) -> Taiyaar (manager ki approval)", "questions": [], "lists": [], "fields": [],
            "logic": {"workflows": [{"coll": "orders", "field": "status", "states": ["Naya", "Ban raha", "Taiyaar"], "initial": "Naya",
                                     "transitions": [
                                         {"from": ["Naya"], "to": "Ban raha", "label": "Start", "who": ["staff"]},
                                         {"from": ["Ban raha"], "to": "Taiyaar", "label": "Ready", "who": ["staff"],
                                          "approval": {"steps": [{"who": "admin", "label": "Manager"}], "maker_checker": True}}]}]}}


def _login(c, base, email, pw):
    return {"Authorization": "Bearer " + c.post(f"{base}/login", json={"email": email, "password": pw}).json()["token"]}


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.744.0"


def test_link_moves_everything_and_old_logins_keep_working(app_site, monkeypatch):
    from app.config import get_settings
    from app.main import app
    monkeypatch.setattr(get_settings(), "site_app_link", False)       # v0.414: an OLD v0.305 site (new ones link at once)
    from app.site import applink as AL
    from app.site import service as S
    from app.site import webapp as W
    sid = app_site
    c = TestClient(app)
    S.design_app(T, sid, "customers apna order track karein")
    base = f"/api/site-app/{sid}"
    a = c.post(f"{base}/signup", json={"email": "asha@x.in", "password": "asha-pass-1", "name": "Asha"}).json()
    ha = {"Authorization": "Bearer " + a["token"]}
    row = c.post(f"{base}/c/orders", headers=ha, json={"item": "Kaju katli", "phone": "9876500000"}).json()
    # unlinked: the v0.305 engine, and the DIMAAG-only addresses say so
    assert c.get(f"{base}/approvals", headers=ha).status_code == 404
    assert c.get(f"/api/sites/{sid}/logic").json()["linked"] is False
    got = c.post(f"/api/sites/{sid}/link-app").json()
    assert got["linked"] and got["number"].startswith("A-")
    assert c.post(f"/api/sites/{sid}/link-app").json()["app"] == got["app"]               # idempotent
    with W.session() as s:
        assert s.query(W.SiteAppRow).filter_by(site_id=sid).count() == 0                  # nothing left behind
        assert s.query(W.SiteAppRow).filter_by(site_id="app:" + got["app"]).count() == 1
    # the login made BEFORE the link still works, her row kept its id
    assert c.get(f"{base}/me", headers=ha).json()["me"]["name"] == "Asha"
    rows = c.get(f"{base}/c/orders", headers=ha).json()["rows"]
    assert [x["id"] for x in rows] == [row["id"]] and rows[0]["item"] == "Kaju katli"
    # a fresh login (same password) works on the app backend; schema is the app's
    hb = _login(c, base, "asha@x.in", "asha-pass-1")
    assert c.get(f"{base}/me", headers=hb).json()["me"]["email"] == "asha@x.in"
    sch = c.get(f"{base}/schema").json()
    assert [x["key"] for x in sch["collections"]] == ["orders", "notices"]
    # her console reads through the link
    info = c.get(f"/api/sites/{sid}/app").json()
    assert info["linked"]["app"] == got["app"] and info["counts"]["orders"] == 1
    assert {x["item"] for x in c.get(f"/api/sites/{sid}/app/rows/orders").json()["rows"]} == {"Kaju katli"}
    r = S._load(sid)
    assert AL.linked_id(r) == got["app"] and AL.project(r).status == "web"


def test_linked_site_runs_workflows_and_maker_checker_approvals(app_site, monkeypatch):
    from app.appmaker import ai as AAI
    from app.main import app
    from app.site import service as S
    sid = app_site
    c = TestClient(app)
    S.design_app(T, sid, "customers apna order track karein")
    base = f"/api/site-app/{sid}"
    for e, n in (("asha@x.in", "Asha"), ("ravi@x.in", "Ravi"), ("boss@x.in", "Boss")):
        c.post(f"{base}/signup", json={"email": e, "password": "pass-word-1", "name": n})
    asks = []
    monkeypatch.setattr(AAI, "ask_json", lambda system, prompt, max_tokens=7000: asks.append(prompt) or json.loads(json.dumps(WORKFLOW)))
    # design_app on a LINKED site = the app's own author (a checked draft, nothing live yet)
    c.post(f"/api/sites/{sid}/link-app")
    d = c.post(f"/api/sites/{sid}/app-design", json={"words": "order ready karne se pehle manager approve kare"}).json()["draft"]
    assert d["ready"] and asks and "manager approve" in asks[0]
    assert c.get(f"/api/sites/{sid}/logic").json()["draft"]["hash"] == d["hash"]
    assert c.post(f"/api/sites/{sid}/logic/apply", json={"hash": "wrong"}).status_code == 409     # only the exact draft she saw
    ok = c.post(f"/api/sites/{sid}/logic/apply", json={"hash": d["hash"]}).json()
    assert ok["rev"] >= 1 and any("Workflow" in x for x in ok["summary"])
    mem = {m["email"]: m["id"] for m in c.get(f"/api/sites/{sid}/app/members").json()["members"]}
    c.post(f"/api/sites/{sid}/app/members/{mem['ravi@x.in']}/role", json={"role": "staff"})
    c.post(f"/api/sites/{sid}/app/members/{mem['boss@x.in']}/role", json={"role": "admin"})
    ha, hr, hb = (_login(c, base, e, "pass-word-1") for e in ("asha@x.in", "ravi@x.in", "boss@x.in"))
    sch = c.get(f"{base}/schema").json()
    assert sch["approvals"] is True and next(x for x in sch["collections"] if x["key"] == "orders")["workflow"] == "status"
    o = c.post(f"{base}/c/orders", headers=ha, json={"item": "Laddoo", "phone": "9876500001", "status": "Taiyaar"}).json()
    assert o["status"] == "Naya"                                                                  # the workflow's start
    staff_view = next(x for x in c.get(f"{base}/c/orders", headers=hr).json()["rows"] if x["id"] == o["id"])
    assert staff_view["_actions"] == [{"to": "Ban raha", "label": "Start", "approval": False}]
    assert c.patch(f"{base}/c/orders/{o['id']}", headers=hr, json={"status": "Taiyaar"}).status_code == 422   # not a step from Naya
    assert c.patch(f"{base}/c/orders/{o['id']}", headers=hr, json={"status": "Ban raha"}).json()["status"] == "Ban raha"
    ask = c.patch(f"{base}/c/orders/{o['id']}", headers=hr, json={"status": "Taiyaar"}).json()
    assert ask["status"] == "Ban raha" and ask["_pending"]["waiting_for"] == "Manager"
    aid = ask["approval"]["id"]
    r = c.post(f"{base}/approvals/{aid}", headers=hr, json={"decision": "approve"})
    assert r.status_code == 403 and "maker-checker" in r.json()["error"]                         # not his own ask
    assert c.post(f"{base}/approvals/{aid}", headers=ha, json={"decision": "approve"}).status_code == 403
    assert c.get(f"{base}/approvals", headers=hb).json()["approvals"][0]["can_decide"]
    assert c.post(f"{base}/approvals/{aid}", headers=hb, json={"decision": "approve"}).json()["status"] == "approved"
    assert next(x for x in c.get(f"{base}/c/orders", headers=ha).json()["rows"] if x["id"] == o["id"])["status"] == "Taiyaar"
    # the stats + dashboard read the app's rows
    st = c.get(f"{base}/stats", headers=hb).json()
    assert st and "error" not in st


SCHOOL_SPEC = {"name": "Gyan Vidya Mandir", "summary": "School ka portal: admission, fees, chhutti ki arzi, notices.",
               "field_hint": "school", "goal": "enquiry",
               "roles": [{"key": "parent", "label": "Parent", "can": "admission form bhare, apne bachche ki fees aur chhutti dekhe"},
                         {"key": "parent", "label": "dup"}, {"key": "", "label": ""}],
               "pages": [{"title": "Home", "purpose": "school ka parichay", "for": "public"},
                         {"title": "Admissions", "purpose": "admission form", "for": "public"},
                         {"title": "Fees", "purpose": "fee structure", "for": "public"},
                         {"title": "Contact", "purpose": "pata, phone", "for": "public"},
                         {"title": "home", "purpose": "duplicate", "for": "public"},
                         {"title": "My child", "purpose": "fees + chhutti", "for": "member"},
                         {"title": "Leave requests", "purpose": "approve leave", "for": "staff"}],
               "features": {"shop": False, "blog": True, "booking": False, "languages": ["hi", "klingon"]},
               "app_words": "students list; leave requests by parents with class teacher approval", "page_count": 4,
               "questions": []}
SCHOOL_LOGIC = {"summary": "Students + chhutti ki arzi (teacher approve kare)", "questions": [],
                "lists": [{"key": "students", "label": "Students", "rules": {"create": "member", "read": "own", "update": "admin", "delete": "admin"},
                           "fields": [{"key": "name", "label": "Name", "type": "text", "required": True},
                                      {"key": "class_name", "label": "Class", "type": "text"}]},
                          {"key": "leaves", "label": "Leave requests", "rules": {"create": "member", "read": "own", "update": "own", "delete": "admin"},
                           "fields": [{"key": "student", "label": "Student", "type": "ref", "to": "students", "required": True},
                                      {"key": "days", "label": "Days", "type": "number"},
                                      {"key": "status", "label": "Status", "type": "choice", "options": ["Asked", "Approved", "Rejected"]}]}],
                "fields": [],
                "logic": {"relations": [{"name": "leaves", "from": "leaves", "field": "student", "to": "students", "label": "Leaves", "on_delete": "cascade"}],
                          "rules": [{"coll": "leaves", "check": "days > 0", "message": "Kam se kam 1 din", "on": "always"}],
                          "workflows": [{"coll": "leaves", "field": "status", "states": ["Asked", "Approved", "Rejected"], "initial": "Asked",
                                         "transitions": [{"from": ["Asked"], "to": "Approved", "label": "Approve", "who": ["staff"]},
                                                         {"from": ["Asked"], "to": "Rejected", "label": "Reject", "who": ["staff"]}]}],
                          "labels": {"students": "name"}}}


@pytest.fixture
def arch_env(site_env, monkeypatch):
    from app.appmaker import ai as AAI
    from app.site import ai as AI
    from app.site import architect as AR

    def ask(system, prompt, max_tokens=6000, kind="build"):
        if system.startswith(AR.ARCH_SYSTEM[:40]):
            assert "school" in prompt
            return json.loads(json.dumps(SCHOOL_SPEC))
        return site_env(system, prompt, max_tokens, kind)
    monkeypatch.setattr(AI, "ask_json", ask)
    monkeypatch.setattr(AAI, "ask_json", lambda system, prompt, max_tokens=7000: json.loads(json.dumps(SCHOOL_LOGIC)))
    return site_env


def test_architect_builds_a_school_portal_from_one_line(arch_env):
    from app.appmaker import service as AS
    from app.main import app
    from app.site import applink as AL
    from app.site import service as S
    c = TestClient(app)
    assert c.post("/api/site-architect", json={"words": "x"}).status_code == 400
    card = c.post("/api/site-architect", json={"words": "hamare school ka portal - admission, fees, chhutti ki arzi, notices"}).json()
    mods = {m["key"]: m for m in card["modules"]}
    assert list(mods) == ["stories", "pages", "users", "flows", "data", "logic", "payments", "notifications", "integrations", "features", "quality", "phases", "risks"]   # v0.414
    assert card["data_ready"] and card["name"] == "Gyan Vidya Mandir"
    assert "Admissions" in mods["pages"]["lines"][0] and any("Leave requests" in x for x in mods["pages"]["lines"])
    assert len([x for x in mods["users"]["lines"] if x.startswith("Parent")]) == 1               # duplicate role dropped
    assert any(x.startswith("Students:") for x in mods["data"]["lines"]) and any("Workflow" in x for x in mods["logic"]["lines"])
    assert "Blog" in mods["features"]["lines"] and not any("klingon" in x.lower() for x in mods["features"]["lines"])
    assert all(a["status"] != "spec" for a in AS.apps(T))                                         # a spec is not an app yet
    assert c.get("/api/site-architect").json()["specs"][0]["status"] == "waiting"
    # only the exact card she saw; nothing was built before her tap
    assert c.post(f"/api/site-architect/{card['id']}/approve", json={"hash": "nope"}).status_code == 409
    from app.db import session
    from app.site.models import Site
    with session() as s:
        assert s.query(Site).count() == 0
    got = c.post(f"/api/site-architect/{card['id']}/approve", json={"hash": card["hash"]}).json()
    assert got["number"].startswith("S-") and got["app"] == card["id"]
    assert c.post(f"/api/site-architect/{card['id']}/approve", json={"hash": card["hash"]}).status_code == 409   # once
    r = S._load(got["site"])
    assert AL.linked_id(r) == card["id"] and r.status == "looks"                                  # plan approved -> 3 looks
    assert "Admissions" in r.brief and "hi" in json.loads(r.languages)
    # the site's app is the school's data + logic, live through the site's own addresses
    base = f"/api/site-app/{got['site']}"
    sch = c.get(f"{base}/schema").json()
    assert {x["key"] for x in sch["collections"]} == {"students", "leaves"}
    p = c.post(f"{base}/signup", json={"email": "parent@x.in", "password": "pass-word-1", "name": "Meena"}).json()
    hp = {"Authorization": "Bearer " + p["token"]}
    st = c.post(f"{base}/c/students", headers=hp, json={"name": "Aarav", "class_name": "5A"}).json()
    assert c.post(f"{base}/c/leaves", headers=hp, json={"student": st["id"], "days": 0}).status_code == 422   # rule: days > 0
    lv = c.post(f"{base}/c/leaves", headers=hp, json={"student": st["id"], "days": 2, "status": "Approved"}).json()
    assert lv["status"] == "Asked" and lv["_labels"]["student"] == "Aarav"                       # a parent cannot self-approve
    rel = c.get(f"{base}/c/students/{st['id']}/related/leaves", headers=hp).json()
    assert [x["days"] for x in rel["rows"]] == [2]
    assert card["id"] in {a["id"] for a in AS.apps(T)}                                            # now a real app (phone app later)


def test_architect_modules_she_switches_off_are_skipped(arch_env):
    from app.main import app
    from app.site import applink as AL
    from app.site import service as S
    c = TestClient(app)
    card = c.post("/api/site-architect", json={"words": "school ka portal chahiye, admission aur notices"}).json()
    got = c.post(f"/api/site-architect/{card['id']}/approve", json={"hash": card["hash"], "modules": ["pages", "features"]}).json()
    assert got["modules"] == ["features", "pages", "stories", "users"]          # v0.414 stories always kept
    r = S._load(got["site"])
    assert AL.linked_id(r) == ""                                                                  # no data module -> no app link


def test_architect_tool_needs_her_haan(arch_env):
    from app.agent import site_tools as ST
    from app.agent.tools import Ctx, ToolError
    out = ST._act(Ctx(tenant_id=T, conversation_id="", actor="owner"), "architect", {"brief": "school ka portal, fees aur chhutti"})
    assert out["modules"] and out["hash"]
    with pytest.raises(ToolError):
        ST._act(Ctx(tenant_id=T, conversation_id="", actor="staff:x"), "architect_ok", {"spec": out["number"], "hash": out["hash"]})
    done = ST._act(Ctx(tenant_id=T, conversation_id="", actor="owner"), "architect_ok", {"spec": out["number"], "hash": out["hash"]})
    assert done["number"].startswith("S-")


def test_site_app_script_draws_workflow_buttons_approvals_and_links():
    from pathlib import Path
    js = (Path(__file__).resolve().parents[1] / "app" / "site" / "assets" / "hoola-app.js").read_text()
    for k in ("decideButtons", "approvalsBox", "refOptions", "inForm", "_actions", "_pending", "_labels"):
        assert k in js, k
    con = (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "build.js").read_text()
    assert "site_spec" in con and "/api/site-architect/" in con and "logicBox" in con
