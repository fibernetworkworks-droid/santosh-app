"""v0.58 Hoola Employee: job, team, trust per duty, the server-side gate, owner's tap, audit, pause, report, team tasks."""
import asyncio

import pytest
from fastapi.testclient import TestClient

from app.agent.tools import Ctx, ToolError, dispatch
from tests.test_bazar import _events, _notices


def _job(**kw):
    from app.employee import service as emp
    args = dict(enabled=True, role="front_desk", business_name="Sharma Clinic", business_kind="clinic",
                about="Dant ka clinic, Akola", hours={"open": "10:00", "close": "19:00", "days": [0, 1, 2, 3, 4, 5]})
    args.update(kw)
    return emp.setup("default", **args)


def _ctx(actor="owner"):
    from app.net.service import home_conv
    return Ctx(tenant_id="default", conversation_id=home_conv("default"), actor=actor)


def run(c):
    return asyncio.run(c)


def test_setup_rules(env):
    from app.employee import service as emp
    with pytest.raises(emp.EmployeeError):
        emp.setup("default", enabled=True)                         # no business name
    with pytest.raises(emp.EmployeeError):
        emp.setup("default", role="ceo")
    with pytest.raises(emp.EmployeeError):
        emp.setup("default", business_name="X", hours={"open": "25:00"})
    with pytest.raises(emp.EmployeeError):
        emp.setup("default", business_name="X", role="custom", enabled=True)   # custom needs duties
    p = _job()
    assert p["enabled"] and p["duties"] == ["customers", "appointments", "reminders", "email", "research"]
    assert [t["level"] for t in emp.trust("default")] == ["seekh"] * 5            # every duty starts learning
    p = emp.setup("default", role="custom", duties=["records", "email", "email"])
    assert p["duties"] == ["records", "email"]


def test_owner_is_never_held_but_jobs_ask(env):
    from app.employee import service as emp
    from app.life import upcoming_reminders
    _job()
    out = run(dispatch("create_reminder", {"text": "Dawai", "when": "2027-01-15T09:00"}, _ctx()))
    assert "waiting_owner" not in str(out) and len(upcoming_reminders("default")) == 1
    # a scheduled job doing the same duty while trust is "seekh" -> waits for the owner's tap
    out = run(dispatch("create_reminder", {"text": "Patient ko call", "when": "2027-01-15T11:00"}, _ctx("routine")))
    assert out["status"] == "waiting_owner" and len(upcoming_reminders("default")) == 1
    asks = emp.asks("default")
    assert len(asks) == 1 and asks[0]["who"] == "Roz ka kaam" and "seekh" in asks[0]["why"]
    assert _events(_ctx().conversation_id, "employee_ask")
    # asking twice for the same thing does not make two cards
    run(dispatch("create_reminder", {"text": "Patient ko call", "when": "2027-01-15T11:00"}, _ctx("routine")))
    assert len(emp.asks("default")) == 1
    done = run(emp.decide("default", asks[0]["id"], True))
    assert done["status"] == "done" and len(upcoming_reminders("default")) == 2
    t = {x["duty"]: x for x in emp.trust("default")}["reminders"]
    assert t["approved"] == 1
    assert any("haan kaha" in (n or "") for n in _notices(_ctx().conversation_id))
    entries = emp.audit("default")
    assert any(e["outcome"] == "done" and e["approved_by"] == "owner" and e["who"] == "Roz ka kaam" for e in entries)
    # Mana: nothing runs, the streak resets
    run(dispatch("create_reminder", {"text": "Bill", "when": "2027-01-15T17:00"}, _ctx("routine")))
    aid = emp.asks("default")[0]["id"]
    assert run(emp.decide("default", aid, False))["status"] == "declined"
    assert len(upcoming_reminders("default")) == 2
    assert {x["duty"]: x for x in emp.trust("default")}["reminders"]["approved"] == 0
    # a routine about the owner's personal things (outside the job) is hers: no gate
    out = run(dispatch("remember", {"fact": "Meghana ko chai pasand hai"}, _ctx("routine")))
    assert "waiting_owner" not in str(out)


def test_saathi_bharosa_caps_and_big(env):
    from app.employee import service as emp
    _job()
    emp.set_trust("default", "reminders", "saathi", per_day=2)
    for i in range(2):
        out = run(dispatch("create_reminder", {"text": f"R{i}", "when": "2027-01-15T09:00"}, _ctx("routine")))
        assert "waiting_owner" not in str(out)
    out = run(dispatch("create_reminder", {"text": "R3", "when": "2027-01-15T09:00"}, _ctx("routine")))
    assert out["status"] == "waiting_owner" and "seemaa" in emp.asks("default")[0]["why"]
    # big things ask at saathi
    out = run(dispatch("cancel_routine", {"routine_id": "x"}, _ctx("routine")))
    assert out["status"] == "waiting_owner"
    emp.set_trust("default", "reminders", "bharosa", per_day=100)
    with pytest.raises(ToolError):                     # bharosa: it really runs (and the tool itself says no such job)
        run(dispatch("cancel_routine", {"routine_id": "x"}, _ctx("routine")))


def test_pause_stops_the_job_not_reading(env):
    from app.employee import service as emp
    _job()
    emp.set_pause("default", True)
    with pytest.raises(ToolError) as e:
        run(dispatch("create_reminder", {"text": "X", "when": "2027-01-15T09:00"}, _ctx()))   # even the owner, inside the job
    assert "Pause" in str(e.value)
    run(dispatch("list_reminders", {}, _ctx("routine")))                                   # reading is fine
    run(dispatch("remember", {"fact": "Ghar ki chaabi drawer mein"}, _ctx()))              # her personal things go on
    assert any(a["outcome"] == "paused" for a in emp.audit("default"))
    assert "KAAM ROK" in emp.prompt_block("default")
    emp.set_pause("default", False)
    run(dispatch("create_reminder", {"text": "X", "when": "2027-01-15T09:00"}, _ctx()))


def test_staff_permissions(env):
    from app.employee import service as emp
    _job()
    ramesh = emp.add_member("default", "Ramesh", phone="98765 43210", role="staff", duties=["appointments"])
    asha = emp.add_member("default", "Asha", role="manager")
    with pytest.raises(emp.EmployeeError):
        emp.add_member("default", "", role="staff")
    with pytest.raises(emp.EmployeeError):
        emp.add_member("default", "Y", phone="12")
    with pytest.raises(ToolError):        # reminders is in the job, but not one of Ramesh's duties
        run(dispatch("create_reminder", {"text": "X", "when": "2027-01-15T09:00"}, _ctx(f"staff:{ramesh['id']}")))
    with pytest.raises(ToolError):        # outside the job altogether
        run(dispatch("remember", {"fact": "x"}, _ctx(f"staff:{asha['id']}")))
    with pytest.raises(ToolError):        # unknown member
        run(dispatch("create_reminder", {"text": "X", "when": "2027-01-15T09:00"}, _ctx("staff:tm_nobody")))
    emp.set_trust("default", "reminders", "bharosa")
    out = run(dispatch("create_reminder", {"text": "Stock", "when": "2027-01-15T09:00"}, _ctx(f"staff:{asha['id']}")))
    assert "waiting_owner" not in str(out)
    out = run(dispatch("cancel_routine", {"routine_id": "x"}, _ctx(f"staff:{asha['id']}")))
    assert out["status"] == "waiting_owner"           # big things always go to the owner when staff asked
    emp.update_member("default", asha["id"], active=False)
    with pytest.raises(ToolError):
        run(dispatch("create_reminder", {"text": "Y", "when": "2027-01-15T09:00"}, _ctx(f"staff:{asha['id']}")))
    emp.setup("default", enabled=False)
    with pytest.raises(ToolError):
        run(dispatch("list_reminders", {}, _ctx(f"staff:{ramesh['id']}")))


def test_correction_drops_trust_and_becomes_a_rule(env):
    from app.employee import service as emp
    _job()
    emp.set_trust("default", "reminders", "bharosa")
    run(dispatch("create_reminder", {"text": "Galat time", "when": "2027-01-15T09:00"}, _ctx("routine")))
    e = next(x for x in emp.audit("default") if x["tool"] == "create_reminder")
    out = emp.mark_wrong("default", e["id"], "Patient reminder subah 8 se pehle nahi")
    assert out["trust"]["level"] == "saathi" and out["trust"]["corrections"] == 1
    assert "subah 8 se pehle nahi" in emp.profile("default")["rules"]
    assert "subah 8 se pehle nahi" in emp.job_sheet("default")["text"]
    assert emp.mark_wrong("default", e["id"])["trust"] is None      # once only


def test_promotion_suggestion(env):
    from app.db import session
    from app.employee import service as emp
    from app.employee.models import DutyTrust
    from sqlalchemy import select
    _job()
    emp.trust("default")
    with session() as s:
        s.scalars(select(DutyTrust).where(DutyTrust.duty == "email")).first().approved = 15
    t = {x["duty"]: x for x in emp.trust("default")}["email"]
    assert t["suggest"] == "saathi" and t["progress"] == [15, 15]
    assert "saathi" in emp.report("default")["text"]


def test_job_sheet_prompt_report(env):
    from app.employee import service as emp
    _job()
    emp.add_member("default", "Asha", role="manager")
    sheet = emp.job_sheet("default")
    assert not sheet["edited"] and "Sharma Clinic" in sheet["text"] and "PIN, OTP" in sheet["text"] and "Asha" in sheet["text"]
    assert "Sharma Clinic" in emp.prompt_block("default")
    from app.agent.prompts import system_prompt
    assert "Naukri (Hoola Employee)" in system_prompt(True, "", "default")
    emp.set_job_sheet("default", "Mera apna job sheet")
    assert emp.job_sheet("default") == {"text": "Mera apna job sheet", "edited": True}
    emp.set_job_sheet("default", "")
    assert not emp.job_sheet("default")["edited"]
    run(dispatch("create_reminder", {"text": "X", "when": "2027-01-15T09:00"}, _ctx()))
    r = emp.report("default")
    assert "Follow-up aur yaad: 1 kaam" in r["text"] and r["total"]["done"] == 1
    from datetime import datetime, timedelta
    from app.life import tz_of
    emp.setup("default", report_time=(datetime.now(tz_of("default")) - timedelta(minutes=1)).strftime("%H:%M"))
    assert emp.due_reports() == ["default"] and emp.due_reports() == []      # once a day
    emp.send_report("default")
    assert _events(_ctx().conversation_id, "employee_report")


def test_employee_tool(env):
    from app.employee import service as emp
    assert run(dispatch("employee", {"action": "status"}, _ctx()))["set_up"] is False
    _job()
    assert run(dispatch("employee", {"action": "pause"}, _ctx()))["paused"] is True
    assert emp.profile("default")["paused"]
    m = emp.add_member("default", "Ramesh", role="staff", duties=["appointments"])
    with pytest.raises(ToolError):        # staff can stop the work, never restart it or change trust
        run(dispatch("employee", {"action": "resume"}, _ctx(f"staff:{m['id']}")))
    assert run(dispatch("employee", {"action": "pause"}, _ctx(f"staff:{m['id']}")))["paused"]
    run(dispatch("employee", {"action": "resume"}, _ctx()))
    out = run(dispatch("employee", {"action": "trust", "duty": "email", "level": "saathi"}, _ctx()))
    assert out["duty"] == "Email"
    assert run(dispatch("employee", {"action": "status"}, _ctx()))["paused"] is False


def test_team_task_over_hoola_network(env, monkeypatch):
    from tests.test_net import _connect
    from app.employee import network
    from app.employee import service as emp
    net = _connect()                                   # default (the clinic) <-> kunal (works there)
    from app.net import identity as idn
    kunal_addr = idn.my_card("kunal")["address"]
    # not in the team yet: refused
    assert network.send_task("kunal", "@meghana.fnw", "Kal ke appointments ki list bana do")["status"] == "refused"
    _job()
    m = emp.add_member("default", "Kunal", address=kunal_addr, role="staff", duties=["appointments"])
    out = network.send_task("kunal", "@meghana.fnw", "Kal ke appointments ki list bana do")
    assert out["status"] == "accepted"
    with pytest.raises(Exception):
        network.send_task("kunal", "@meghana.fnw", "Mera OTP 482913 hai, bhar do")
    tasks = network.tasks("default")
    assert len(tasks) == 1 and tasks[0]["who"] == "Kunal" and tasks[0]["status"] == "pending"
    seen = {}

    async def fake_turn(conv, text, tenant_id=None, voice=False, context="", actor="owner", **_):
        seen.update(actor=actor, text=text)
        return "Kal 4 appointments hain: 10, 11:30, 3 aur 5 baje. Patient ka number 9876543210."

    monkeypatch.setattr("app.agent.run_turn", fake_turn)
    assert run(network.run_pending()) == 1
    assert seen["actor"] == f"staff:{m['id']}" and "Yeh owner nahi hain" in seen["text"]
    assert network.tasks("default")[0]["status"] == "done"
    got = [e for e in _events(net.home_conv("kunal"), "hoola_msg") if e.get("kind") == "staff_done"]
    assert got and "4 appointments" in got[0]["text"] and "9876543210" not in got[0]["text"]   # phone numbers scrubbed
    emp.set_pause("default", True)
    r = network.send_task("kunal", "@meghana.fnw", "Aur ek kaam")
    assert r["status"] == "refused" and "rok" in r["reason"]


def test_api(env):
    from app import main
    with TestClient(main.app) as c:
        r = c.get("/api/employee").json()
        assert r["profile"] is None and len(r["roles"]) == len(__import__("app.employee.roles", fromlist=["ROLES"]).ROLES) and len(r["levels"]) == 3
        assert c.put("/api/employee", json={"enabled": True}).status_code == 400
        p = c.put("/api/employee", json={"enabled": True, "role": "support_collect", "business_name": "FNW Broadband"}).json()
        assert p["enabled"] and "tickets" in p["duties"]
        m = c.post("/api/employee/team", json={"name": "Asha", "role": "manager"}).json()
        assert c.patch(f"/api/employee/team/{m['id']}", json={"role": "staff", "duties": ["tickets"]}).json()["duties"] == ["tickets"]
        assert c.put("/api/employee/trust/tickets", json={"level": "saathi"}).json()["level"] == "saathi"
        assert c.put("/api/employee/trust/nope", json={"level": "saathi"}).status_code == 400
        assert c.post("/api/employee/pause", json={"paused": True}).json()["paused"]
        r = c.get("/api/employee").json()
        assert r["status"]["paused"] and len(r["trust"]) == 7 and r["team"][0]["name"] == "Asha"
        assert any(e["tool"] == "pause" for e in c.get("/api/employee/audit").json()["entries"])
        assert "FNW Broadband" in c.get("/api/employee/job_sheet").json()["text"]
        assert c.get("/api/employee/report").json()["date"]
        assert c.get("/api/employee/report", params={"day": "kal"}).status_code == 400
        assert c.post("/api/employee/asks/ea_x", json={"approve": True}).status_code == 400
        assert c.delete(f"/api/employee/team/{m['id']}").json()["ok"]
        assert c.get("/api/employee/tasks").json() == {"tasks": []}
