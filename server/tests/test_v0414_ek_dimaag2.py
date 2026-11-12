"""v0.414 EK DIMAAG 2 - web Step 2 finished (W1 + W13 of docs/WEB_PLATFORM_PLAN.md).

1. old v0.305 sites move by themselves (worker sweep) and every NEW web app lands on the one backend at once;
   a website's lists are never re-made from an app plan when the backend version moves.
2. THE PROOF: a school portal from one line - admission -> principal approval (maker-checker) -> student -> fee ->
   class -> attendance -> report card, used by parent + teacher + principal, each seeing only what they should.
3. the SAME data in a phone app: the site's project becomes an App Sahayak plan (same id, same app_key) and the phone
   API reads / writes the very rows the website shows.
4. the spec card carries user stories, payments, notifications, other apps; any part changes in her words, and after
   the build only what the change touches is rebuilt.
5. a live check (real Opus on her server, nothing built)."""
import json

import pytest
from fastapi.testclient import TestClient

from tests.test_v0305_web_apps import T, app_site  # noqa: F401  (fixture)
from tests.test_v121_site import site_env  # noqa: F401  (fixture)


def _login(c, base, email, pw="pass-word-1"):
    r = c.post(f"{base}/login", json={"email": email, "password": pw}).json()
    return {"Authorization": "Bearer " + r["token"]}


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.857.0"


# ---------------------------------------------------------------- 1. old sites move by themselves
def test_old_sites_move_by_themselves_and_new_apps_land_linked(app_site, monkeypatch):
    from app.config import get_settings
    from app.main import app
    from app.site import applink as AL
    from app.site import service as S
    sid = app_site
    c = TestClient(app)
    monkeypatch.setattr(get_settings(), "site_app_link", False)       # an OLD v0.305 site (before this version)
    S.design_app(T, sid, "customers apna order track karein")
    assert AL.linked_id(S._load(sid)) == ""
    base = f"/api/site-app/{sid}"
    a = c.post(f"{base}/signup", json={"email": "asha@x.in", "password": "pass-word-1", "name": "Asha"}).json()
    ha = {"Authorization": "Bearer " + a["token"]}
    row = c.post(f"{base}/c/orders", headers=ha, json={"item": "Kaju katli", "phone": "9876500000"}).json()
    assert AL.migrate_all()["off"] is True                                            # switch off = nothing moves
    monkeypatch.setattr(get_settings(), "site_app_link", True)
    got = AL.migrate_all()
    assert got["moved"] == 1 and got["sites"][0]["site"] == sid
    assert AL.migrate_all()["moved"] == 0                                              # idempotent
    assert AL.linked_id(S._load(sid))
    assert c.get(f"{base}/me", headers=ha).json()["me"]["name"] == "Asha"              # her old login still works
    assert [x["id"] for x in c.get(f"{base}/c/orders", headers=ha).json()["rows"]] == [row["id"]]


def test_a_new_web_app_is_linked_at_once_and_its_lists_are_never_remade(app_site):
    from app.appmaker import backend as BE
    from app.appmaker.models import AppProject
    from app.db import session
    from app.site import applink as AL
    from app.site import service as S
    sid = app_site
    S.design_app(T, sid, "customers apna order track karein")
    p = AL.project(S._load(sid))
    assert p is not None and p.status == "web"
    with session() as s:                                    # an OLDER backend version (a future SCHEMA_V bump)
        row = s.get(AppProject, p.id)
        be = json.loads(row.backend)
        be["v"] = 1
        row.backend = json.dumps(be)
    p = AL.project(S._load(sid))
    out = BE.ensure(p)
    assert [x["key"] for x in out["schema"]["collections"]] == ["orders", "notices"] and out["v"] == BE.SCHEMA_V


# ---------------------------------------------------------------- 2. the school portal from one line
SCHOOL_SPEC = {
    "name": "Gyan Vidya Mandir", "summary": "School portal: admission, principal approval, fees, classes, attendance, report card.",
    "field_hint": "school", "goal": "enquiry",
    "roles": [{"key": "parent", "label": "Parent", "can": "admission form, apne bachche ki fees, attendance, report card"},
              {"key": "teacher", "label": "Teacher", "can": "attendance aur marks bhare, admission aage bheje"},
              {"key": "principal", "label": "Principal", "can": "admission approve kare, fees ki jaanch"}],
    "stories": [{"who": "Parent", "want": "admission online apply karna", "so": "school jaana na pade"},
                {"who": "Teacher", "want": "roz attendance bharna", "so": "parent ko pata rahe"},
                {"who": "Principal", "want": "har admission approve karna", "so": "galat entry na ho"},
                {"who": "Parent", "want": "report card dekhna", "so": ""}, {"who": "", "want": ""}],
    "pages": [{"title": "Home", "purpose": "school", "for": "public"}, {"title": "Admissions", "purpose": "form", "for": "public"},
              {"title": "Fees", "purpose": "fee structure", "for": "public"}, {"title": "Contact", "purpose": "pata", "for": "public"},
              {"title": "My child", "purpose": "fees, attendance, report card", "for": "member"},
              {"title": "Attendance", "purpose": "roz ki haaziri", "for": "staff"}],
    "payments": {"mode": "record", "what": "school fees (office mein)"},
    "notifications": [{"when": "admission approved", "who": "row_owner", "how": "in_app"},
                      {"when": "fee due", "who": "row_owner", "how": "whatsapp"}, {"when": "", "who": "x"}],
    "integrations": [{"name": "google_sheets", "why": "fees ka register"}, {"name": "random_crm", "why": "no"}],
    "features": {"shop": False, "blog": False, "booking": False, "languages": ["hi"]},
    "app_words": "classes; admissions (parent applies, principal approves with maker-checker); student made on approval; "
                 "fee per student; attendance per student per day; report card with total, percent and result",
    "page_count": 4, "questions": []}

ALL = {"rules": {"create": "admin", "read": "own", "update": "admin", "delete": "admin"}}
SCHOOL_LOGIC = {
    "summary": "Admission se report card tak", "questions": [], "fields": [],
    "lists": [
        {"key": "classes", "label": "Classes", "rules": {"create": "admin", "read": "members", "update": "admin", "delete": "admin"},
         "fields": [{"key": "name", "label": "Class", "type": "text", "required": True},
                    {"key": "fee", "label": "Yearly fee", "type": "number"}]},
        {"key": "admissions", "label": "Admissions", "rules": {"create": "member", "read": "own", "update": "own", "delete": "admin"},
         "fields": [{"key": "child", "label": "Child's name", "type": "text", "required": True},
                    {"key": "class_wanted", "label": "Class", "type": "ref", "to": "classes", "required": True},
                    {"key": "status", "label": "Status", "type": "choice", "options": ["Applied", "Approved", "Rejected"]}]},
        {"key": "students", "label": "Students", **ALL,
         "fields": [{"key": "name", "label": "Name", "type": "text", "required": True},
                    {"key": "klass", "label": "Class", "type": "ref", "to": "classes"},
                    {"key": "admission", "label": "Admission", "type": "ref", "to": "admissions"}]},
        {"key": "fees", "label": "Fees", **ALL,
         "fields": [{"key": "student", "label": "Student", "type": "ref", "to": "students", "required": True},
                    {"key": "amount", "label": "Amount", "type": "number"},
                    {"key": "receipt", "label": "Receipt no.", "type": "text"},
                    {"key": "status", "label": "Status", "type": "choice", "options": ["Due", "Paid"]}]},
        {"key": "attendance", "label": "Attendance", **ALL,
         "fields": [{"key": "student", "label": "Student", "type": "ref", "to": "students", "required": True},
                    {"key": "day", "label": "Date", "type": "date", "required": True},
                    {"key": "present", "label": "Present", "type": "yes_no"}]},
        {"key": "reports", "label": "Report cards", **ALL,
         "fields": [{"key": "student", "label": "Student", "type": "ref", "to": "students", "required": True},
                    {"key": "maths", "label": "Maths", "type": "number"}, {"key": "science", "label": "Science", "type": "number"},
                    {"key": "english", "label": "English", "type": "number"},
                    {"key": "total", "label": "Total", "type": "number"}, {"key": "percent", "label": "Percent", "type": "number"},
                    {"key": "result", "label": "Result", "type": "text"}]}],
    "logic": {
        "relations": [
            {"name": "applications", "from": "admissions", "field": "class_wanted", "to": "classes", "label": "Admissions", "on_delete": "restrict"},
            {"name": "fee_rows", "from": "fees", "field": "student", "to": "students", "label": "Fees", "on_delete": "cascade", "share": True},
            {"name": "days", "from": "attendance", "field": "student", "to": "students", "label": "Attendance", "on_delete": "cascade", "share": True},
            {"name": "report_cards", "from": "reports", "field": "student", "to": "students", "label": "Report cards", "on_delete": "cascade", "share": True}],
        "formulas": [{"coll": "reports", "field": "total", "expr": "maths + science + english"},
                     {"coll": "reports", "field": "percent", "expr": "round((maths + science + english) / 3, 1)"},
                     {"coll": "reports", "field": "result", "expr": "if((maths + science + english) / 3 >= 33, \"Pass\", \"Fail\")"}],
        "rules": [{"coll": "reports", "check": "maths <= 100 and science <= 100 and english <= 100", "message": "Marks 100 se zyada nahi", "on": "always"}],
        "unique": [{"coll": "attendance", "fields": ["student", "day"], "message": "Is din ki haaziri pehle se hai"}],
        "workflows": [
            {"coll": "admissions", "field": "status", "states": ["Applied", "Approved", "Rejected"], "initial": "Applied",
             "transitions": [{"from": ["Applied"], "to": "Approved", "label": "Approve", "who": ["staff"],
                              "approval": {"steps": [{"who": "admin", "label": "Principal"}], "maker_checker": True}},
                             {"from": ["Applied"], "to": "Rejected", "label": "Reject", "who": ["admin"]}]},
            {"coll": "fees", "field": "status", "states": ["Due", "Paid"], "initial": "Due",
             "transitions": [{"from": ["Due"], "to": "Paid", "label": "Paid", "who": ["admin"], "require": ["receipt"]}]}],
        "triggers": [
            {"name": "make_student", "coll": "admissions", "on": "enter:Approved",
             "do": [{"create": "students", "values": {"name": "child", "klass": "class_wanted", "admission": "id"}, "owner": "row_owner"},
                    {"notify": "row_owner", "title": "Admission approved", "body": "{{child}} ka admission ho gaya"}]},
            {"name": "first_fee", "coll": "students", "on": "create",
             "do": [{"create": "fees", "values": {"student": "id", "amount": "klass.fee"}, "owner": "row_owner"}]}],
        "labels": {"classes": "name", "students": "name"}}}


@pytest.fixture
def school(site_env, monkeypatch):
    from app.appmaker import ai as AAI
    from app.site import ai as AI
    from app.site import architect as AR
    calls = {"arch": [], "logic": []}

    def ask(system, prompt, max_tokens=6000, kind="build"):
        if system.startswith(AR.ARCH_SYSTEM[:40]):
            calls["arch"].append(prompt)
            if "her_change" in prompt:                      # a revise: the same spec + an Alumni page
                sp = json.loads(json.dumps(SCHOOL_SPEC))
                sp["pages"].append({"title": "Alumni", "purpose": "purane students", "for": "public"})
                return sp
            return json.loads(json.dumps(SCHOOL_SPEC))
        return site_env(system, prompt, max_tokens, kind)

    def logic(system, prompt, max_tokens=7000):
        calls["logic"].append(prompt)
        return json.loads(json.dumps(SCHOOL_LOGIC))
    monkeypatch.setattr(AI, "ask_json", ask)
    monkeypatch.setattr(AAI, "ask_json", logic)
    return calls


def _school_site(c):
    card = c.post("/api/site-architect", json={"words": "school portal - admission, principal approval, fees, attendance, report card"}).json()
    got = c.post(f"/api/site-architect/{card['id']}/approve", json={"hash": card["hash"]}).json()
    return card, got


def test_spec_card_has_stories_payments_notifications_and_other_apps(school):
    from app.main import app
    c = TestClient(app)
    card = c.post("/api/site-architect", json={"words": "school portal - admission, fees, attendance, report card"}).json()
    mods = {m["key"]: m for m in card["modules"]}
    assert list(mods) == ["stories", "pages", "users", "flows", "data", "logic", "payments", "notifications", "integrations", "features", "quality", "phases", "risks"]
    assert len(mods["stories"]["lines"]) == 4 and mods["stories"]["lines"][0].startswith("Parent: admission online")
    assert "record" in json.dumps(card) or "Staff payment record" in mods["payments"]["lines"][0]
    assert any("Paisa kabhi khud nahi" in x for x in mods["payments"]["lines"])
    assert len(mods["notifications"]["lines"]) == 2 and "WhatsApp" in mods["notifications"]["lines"][1]
    assert mods["integrations"]["lines"][0].startswith("Google Sheets") and "random_crm" not in json.dumps(mods)
    assert card["data_ready"]
    assert "Notify: when admission approved -> row_owner" in school["logic"][0]          # in-app notes reach the logic author
    assert "Payments (record)" in school["logic"][0] and "money never moves" in school["logic"][0]


def test_school_portal_from_one_line_used_by_parent_teacher_and_principal(school):
    from app.main import app
    c = TestClient(app)
    card, got = _school_site(c)
    assert "Google Sheets" in got["say"]                                                 # connect later, her login
    from app.site import service as S
    r = S._load(got["site"])
    assert r.stage != "sitemap" and r.status == "looks"           # 'portal' in her words did not turn into a 25-page site map
    sid = got["site"]
    base = f"/api/site-app/{sid}"
    for e, n in (("meena@x.in", "Meena"), ("ravi@x.in", "Ravi Sir"), ("pc@x.in", "Principal"), ("other@x.in", "Other parent")):
        assert c.post(f"{base}/signup", json={"email": e, "password": "pass-word-1", "name": n}).status_code == 200
    mem = {m["email"]: m["id"] for m in c.get(f"/api/sites/{sid}/app/members").json()["members"]}
    c.post(f"/api/sites/{sid}/app/members/{mem['ravi@x.in']}/role", json={"role": "staff"})
    c.post(f"/api/sites/{sid}/app/members/{mem['pc@x.in']}/role", json={"role": "admin"})
    hp, ht, hpr, ho = (_login(c, base, e) for e in ("meena@x.in", "ravi@x.in", "pc@x.in", "other@x.in"))
    # the principal sets up a class
    assert c.post(f"{base}/c/classes", headers=hp, json={"name": "5A", "fee": 15000}).status_code == 403   # a parent cannot
    cls = c.post(f"{base}/c/classes", headers=hpr, json={"name": "5A", "fee": 15000}).json()
    # 1. admission: the parent applies; she cannot approve it herself
    adm = c.post(f"{base}/c/admissions", headers=hp, json={"child": "Aarav", "class_wanted": cls["id"], "status": "Approved"}).json()
    assert adm["status"] == "Applied" and adm["_labels"]["class_wanted"] == "5A"
    # 2. approval: the teacher sends it on, the principal approves (maker-checker: not the teacher himself)
    ask = c.patch(f"{base}/c/admissions/{adm['id']}", headers=ht, json={"status": "Approved"}).json()
    assert ask["status"] == "Applied" and ask["_pending"]["waiting_for"] == "Principal"
    aid = ask["approval"]["id"]
    assert c.post(f"{base}/approvals/{aid}", headers=ht, json={"decision": "approve"}).status_code == 403
    assert c.post(f"{base}/approvals/{aid}", headers=hp, json={"decision": "approve"}).status_code == 403
    assert c.post(f"{base}/approvals/{aid}", headers=hpr, json={"decision": "approve"}).json()["status"] == "approved"
    # 3. the student is made on approval and belongs to the parent; 4. the fee is made for the student
    studs = c.get(f"{base}/c/students", headers=hp).json()["rows"]
    assert [s["name"] for s in studs] == ["Aarav"] and studs[0]["_labels"]["klass"] == "5A"
    st = studs[0]
    fees = c.get(f"{base}/c/fees", headers=hp).json()["rows"]
    assert len(fees) == 1 and fees[0]["amount"] == 15000 and fees[0]["status"] == "Due"
    fee = fees[0]
    assert c.patch(f"{base}/c/fees/{fee['id']}", headers=hp, json={"status": "Paid"}).status_code in (403, 422)   # never herself
    assert c.patch(f"{base}/c/fees/{fee['id']}", headers=hpr, json={"status": "Paid"}).status_code == 422          # receipt first
    c.patch(f"{base}/c/fees/{fee['id']}", headers=hpr, json={"receipt": "R-101"})
    assert c.patch(f"{base}/c/fees/{fee['id']}", headers=hpr, json={"status": "Paid"}).json()["status"] == "Paid"
    # 5. class: the class page lists its admissions
    rel = c.get(f"{base}/c/classes/{cls['id']}/related/applications", headers=hpr).json()
    assert [x["child"] for x in rel["rows"]] == ["Aarav"]
    # 6. attendance: the teacher marks it once a day; the parent sees her own child's days
    assert c.post(f"{base}/c/attendance", headers=ht, json={"student": st["id"], "day": "2026-11-02", "present": True}).status_code == 200
    r = c.post(f"{base}/c/attendance", headers=ht, json={"student": st["id"], "day": "2026-11-02", "present": False})
    assert r.status_code == 409 and "pehle se" in r.json()["error"]
    assert c.post(f"{base}/c/attendance", headers=hp, json={"student": st["id"], "day": "2026-11-03"}).status_code == 403
    days = c.get(f"{base}/c/attendance", headers=hp).json()["rows"]
    assert [(d["day"], d["present"]) for d in days] == [("2026-11-02", True)]
    # 7. report card: the teacher enters marks, the server works out total / percent / result
    assert c.post(f"{base}/c/reports", headers=ht, json={"student": st["id"], "maths": 120, "science": 50, "english": 50}).status_code == 422
    rc = c.post(f"{base}/c/reports", headers=ht, json={"student": st["id"], "maths": 78, "science": 64, "english": 81, "result": "Topper"}).json()
    assert (rc["total"], rc["percent"], rc["result"]) == (223, 74.3, "Pass")
    mine = c.get(f"{base}/c/reports", headers=hp).json()["rows"]
    assert len(mine) == 1 and mine[0]["result"] == "Pass"
    # another parent sees none of it
    for coll in ("students", "fees", "attendance", "reports", "admissions"):
        assert c.get(f"{base}/c/{coll}", headers=ho).json()["rows"] == [], coll
    # the student page shows everything linked to Aarav to the principal
    assert len(c.get(f"{base}/c/students/{st['id']}/related/days", headers=hpr).json()["rows"]) == 1


# ---------------------------------------------------------------- 3. the same data in the phone app
def test_phone_app_runs_on_the_websites_own_data(school):
    from app.appmaker import service as AS
    from app.main import app
    from app.site import applink as AL
    from app.site import service as S
    c = TestClient(app)
    card, got = _school_site(c)
    sid = got["site"]
    p0 = AL.project(S._load(sid))
    key = json.loads(p0.android)["app_key"]
    base = f"/api/site-app/{sid}"
    c.post(f"{base}/signup", json={"email": "pc@x.in", "password": "pass-word-1", "name": "Principal"})
    mem = {m["email"]: m["id"] for m in c.get(f"/api/sites/{sid}/app/members").json()["members"]}
    c.post(f"/api/sites/{sid}/app/members/{mem['pc@x.in']}/role", json={"role": "admin"})
    hpr = _login(c, base, "pc@x.in")
    cls = c.post(f"{base}/c/classes", headers=hpr, json={"name": "6B", "fee": 18000}).json()
    out = c.post(f"/api/sites/{sid}/phone-app", json={}).json()
    assert out["app"] == p0.id and out["status"] == "planned"                          # same project, App Sahayak's plan card
    p1 = AL.project(S._load(sid))
    assert json.loads(p1.android)["app_key"] == key and p1.id == p0.id
    assert len([a for a in AS.apps(T) if a["id"] != p0.id and a["status"] == "planned"]) == 0   # no second copy left behind
    # the phone API (what the Android / iPhone kit calls) reads the website's rows with the website's password
    api = f"/api/app-api/{key}"
    tok = c.post(f"{api}/login", json={"email": "pc@x.in", "password": "pass-word-1"}).json()["token"]
    hh = {"Authorization": "Bearer " + tok}
    assert [x["name"] for x in c.get(f"{api}/c/classes", headers=hh).json()["rows"]] == ["6B"]
    made = c.post(f"{api}/c/classes", headers=hh, json={"name": "7C", "fee": 20000}).json()        # and writes back
    assert {x["name"] for x in c.get(f"{base}/c/classes", headers=hpr).json()["rows"]} == {"6B", "7C"} and made["id"] != cls["id"]
    assert c.post(f"/api/sites/{sid}/phone-app", json={}).json()["status"] == "planned"   # asked twice: still one app
    assert c.get(f"{base}/schema").status_code == 200                                     # the website keeps working


# ---------------------------------------------------------------- 4. change any part, rebuild only what it touches
def test_revise_before_and_after_the_build(school, monkeypatch):
    from app.main import app
    from app.site import service as S
    c = TestClient(app)
    card = c.post("/api/site-architect", json={"words": "school portal - admission, fees, attendance, report card"}).json()
    n_logic = len(school["logic"])
    r = c.post(f"/api/site-architect/{card['id']}/revise", json={"words": "alumni page bhi jodo"}).json()
    assert "Alumni" in json.dumps(r["modules"]) and r["hash"] != card["hash"]
    assert len(school["logic"]) == n_logic                                    # pages only: the data draft was not redone
    assert c.post(f"/api/site-architect/{card['id']}/approve", json={"hash": card["hash"]}).status_code == 409   # old card
    got = c.post(f"/api/site-architect/{card['id']}/approve", json={"hash": r["hash"]}).json()
    changes = []
    monkeypatch.setattr(S, "change", lambda t, site, ins, conv="": changes.append(ins) or {"ok": True})
    # after the build: same Alumni spec again -> nothing to rebuild; a new page -> only a website change
    school_more = json.loads(json.dumps(SCHOOL_SPEC))
    school_more["pages"] += [{"title": "Alumni", "purpose": "x", "for": "public"}, {"title": "Gallery", "purpose": "photos", "for": "public"}]
    from app.site import ai as AI
    old_ask = AI.ask_json
    monkeypatch.setattr(AI, "ask_json", lambda s, p, m=6000, k="build": json.loads(json.dumps(school_more))
                        if "her_change" in p else old_ask(s, p, m, k))
    out = c.post(f"/api/site-architect/{card['id']}/revise", json={"words": "gallery page bhi"}).json()
    assert out["added_pages"] == ["Gallery"] and out["removed_pages"] == [] and changes == ["Naye pages jodo: Gallery"]
    assert "logic_draft" not in out and got["number"] == out["site"]


def test_live_check_builds_nothing(school):
    from app.appmaker import service as AS
    from app.site import architect as AR
    res = AR.live_check()
    assert res["data_ready"] and len(res["modules"]) == 13 and res["seconds"] >= 0
    assert AS.apps(T) == [] and AR.specs(T) == []                            # the spec was removed again


def test_phone_card_and_api_exist():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    card = (root / "lib" / "ui" / "site_spec.dart").read_text()
    assert "class SiteSpecCard" in card and "'approve'" in card and "'revise'" in card and "'hash'" in card
    assert "architectAct" in (root / "lib" / "api.dart").read_text()
    st = (root / "lib" / "state.dart").read_text()
    assert "case 'site_spec':" in st and "SiteSpecCard(" in (root / "lib" / "ui" / "chat_screen.dart").read_text()
