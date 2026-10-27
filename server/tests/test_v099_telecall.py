"""v0.99 Telecaller Sahayak: Hoola prepares calls (list with a reason each, script per person, follow-ups, logs); a PERSON
makes every call. Compliance in code: DND / wrong numbers never listed, cold lists held back, calling hours, DPDP forget."""
import asyncio
import json
from datetime import datetime, time, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import Event, now, session
from tests.test_life import conv_ctx

T = "default"


def _T():
    from app.telecall import service as S
    return S


def _at(hh: int, mm: int = 0, days: int = 0) -> datetime:
    S = _T()
    d = S.local_now(T).date() + timedelta(days=days)
    return datetime.combine(d, time(hh, mm), tzinfo=S._tz(T))


def _rewind(at: datetime) -> None:
    """Leads made 'now' should be due at the moment the test asks about (the test may run after that hour)."""
    S = _T()
    with session() as s:
        for l in s.scalars(select(S.TeleLead)).all():
            l.created_at = at.astimezone(timezone.utc) - timedelta(minutes=10)
            if l.stage == "new":
                l.next_at = at.astimezone(timezone.utc) - timedelta(minutes=5)


def _local(dt_iso: str) -> datetime:
    S = _T()
    return datetime.fromisoformat(dt_iso).astimezone(S._tz(T))


def _events(kind):
    with session() as s:
        return [e.payload for e in s.scalars(select(Event).where(Event.kind == kind).order_by(Event.id)).all()]


@pytest.fixture
def fake_ai(monkeypatch):
    S = _T()

    def ai(system, prompt, max_tokens=1500):
        if "SHORT phone script" in system:
            return json.dumps({"opener": "Namaste Ramesh ji, Asha Greenview Homes se bol rahi hoon, aapne 2BHK ke liye enquiry ki thi.",
                               "permission": "2 minute baat kar sakte hain?", "questions": ["Budget kitna hai?"],
                               "value": "Site Akot road par hai, 100% guaranteed return.",
                               "objections": [{"if": "price zyada hai", "say": "Kis se tulna kar rahe hain?"}],
                               "next_step": "Saturday site visit", "close": "Dhanyavaad", "whatsapp": "Namaste Ramesh ji, brochure bhej rahi hoon.",
                               "notes": ["budget suniye"]})
        if "turn a telecaller's own words" in system:
            low = prompt.lower()
            if "site visit" in low:
                return json.dumps({"outcome": "interested", "interest": "hot", "summary": "Saturday site visit ke liye haan, budget 45 lakh",
                                   "objections": [{"said": "price zyada hai", "answer": "EMI option bataya"}],
                                   "promised": "Saturday site visit", "next_when": "Friday 5 baje", "amount": None,
                                   "language": "hindi", "need": "2BHK", "dnd": False})
            if "mat karna" in low:
                return json.dumps({"outcome": "not_interested", "dnd": True, "summary": "dobara call mat karna"})
            if "denge" in low:
                return json.dumps({"outcome": "promised_pay", "summary": "5000 Monday ko denge", "next_when": "Monday",
                                   "amount": 5000})
        return "{}"
    monkeypatch.setattr(S, "_ai", ai)


def test_when_understands_her_words(env):
    S = _T()
    nowl = S.local_now(T)
    k = S.when(T, "kal 4 baje").astimezone(S._tz(T))
    assert k.date() == nowl.date() + timedelta(days=1) and k.hour == 16
    two = S.when(T, "2 ghante baad")
    assert abs((two - datetime.now(timezone.utc)).total_seconds() - 7200) < 120
    f = S.when(T, "Friday shaam").astimezone(S._tz(T))
    assert f.weekday() == 4 and f.hour == 17 and f.date() > nowl.date()
    d = S.when(T, "28/10 3:30 pm").astimezone(S._tz(T))
    assert (d.day, d.month, d.hour, d.minute) == (28, 10, 15, 30)
    assert S.when(T, "jab bhi") is None
    assert S.phone_of("+91 98765 43210") == "9876543210" and S.phone_of("12345") == ""


def test_list_has_a_reason_each_and_compliance(env, fake_ai):
    S = _T()
    S.save_settings(T, business="Greenview Homes", caller_name="Asha", start_hour="10:00", end_hour="19:30")
    a = S.add_lead(T, "Ramesh", "9876543210", "website", need="2BHK")
    assert a["new"] and not a["warn"]
    S.add_lead(T, "Cold Wala", "9876500001", "bought")                  # bought list: no consent
    S.add_lead(T, "Seema", "9876500002", "customer", "dues", amount=12000)
    S.add_lead(T, "Galat", "9876500003", "enquiry")
    S.mark_dnd(T, "Galat", wrong=True)
    with pytest.raises(S.TeleError):
        S.add_lead(T, "x", "12345")
    _rewind(_at(11))
    cl = S.call_list(T, at=_at(11))
    names = [r["name"] for r in cl["now"]]
    assert names[0] == "Ramesh" and "pehle ghante" in cl["now"][0]["why"]        # fresh enquiry first (speed-to-lead)
    assert "Seema" in names and "₹12,000 baaki" in next(r for r in cl["now"] if r["name"] == "Seema")["why"]
    assert "Galat" not in names and [b["name"] for b in cl["blocked"]] == ["Cold Wala"]
    assert "TRAI" in cl["blocked"][0]["risk"]
    S.save_settings(T, registered=True)                                       # registered 140 line: may call
    assert "Cold Wala" in [r["name"] for r in S.call_list(T, at=_at(11))["now"]]
    _rewind(_at(20))
    late = S.call_list(T, at=_at(20))                                          # after her hours
    assert not late["now"] and late["later"]
    _rewind(_at(19, 15))
    dues_eve = S.call_list(T, at=_at(19, 15))                                  # dues stop at 7 pm, sales go on
    assert "Seema" not in [r["name"] for r in dues_eve["now"]] and "Ramesh" in [r["name"] for r in dues_eve["now"]]
    S.save_settings(T, start_hour="06:00", end_hour="23:00")                  # never before 9 or after 9 pm
    assert S.settings(T)["start_hour"] == "09:00" and S.settings(T)["end_hour"] == "21:00"


def test_script_is_personal_and_has_no_false_promises(env, fake_ai):
    S = _T()
    S.save_settings(T, business="Greenview Homes", caller_name="Asha", record_calls=True)
    S.add_lead(T, "Ramesh", "9876543210", "website", need="2BHK")
    out = S.make_script(T, "Ramesh")
    sc = out["script"]
    assert "Ramesh" in sc["opener"] and sc["objections"][0]["if"] == "price zyada hai"
    assert "guaranteed" not in sc["value"].lower() and "jhoota vaada" in sc["warning"]
    assert sc["wa_link"].startswith("https://wa.me/919876543210")
    assert S.get_lead(T, "Ramesh")["script"]["opener"]


def test_a_person_calls_hoola_logs_and_learns(env, fake_ai):
    S = _T()
    S.save_settings(T, business="Greenview Homes", caller_name="Asha", start_hour="09:00", end_hour="21:00")
    S.add_lead(T, "Ramesh", "9876543210", "website", need="2BHK")
    st = S.start_call(T, "Ramesh")
    assert st["tel"] == "tel:9876543210" and "khud" in st["say"]
    with session() as s:                                                       # she was away 3 minutes on the call
        c = s.get(S.TeleCall, st["call_id"])
        c.started_at = now() - timedelta(minutes=3)
    out = S.log_call(T, call_id=st["call_id"], notes="Ramesh ji se baat hui, price zyada lag raha tha, EMI bataya, "
                                                      "Saturday site visit ke liye haan, Friday 5 baje confirm karna")
    assert out["call"]["outcome"] == "interested" and 170 <= out["call"]["seconds"] <= 200
    lv = S.get_lead(T, "Ramesh")
    assert lv["stage"] == "interested" and lv["interest"] == "hot" and lv["connects"] == 1
    nx = _local(lv["next_at"])
    assert nx.weekday() == 4 and nx.hour == 17
    assert out["whatsapp"]["wa_link"].startswith("https://wa.me/91")
    assert _events("tele_logged")
    lib = S.objection_library(T)
    assert lib[0]["objection"] == "price zyada hai" and lib[0]["worked"] == "EMI option bataya"
    # no answer twice -> retry spacing + WhatsApp nudge
    S.add_lead(T, "Mohan", "9876500010", "enquiry")
    S.log_call(T, "Mohan", outcome="no_answer")
    r2 = S.log_call(T, "Mohan", outcome="no_answer")
    assert "2 baar phone nahi uthaya" in r2["say"] and r2["whatsapp"]["text"]
    m = S.get_lead(T, "Mohan")
    assert m["attempts"] == 2 and m["next_at"]
    # 'call mat karna' -> never listed again
    S.add_lead(T, "Naraz", "9876500011", "enquiry")
    S.log_call(T, "Naraz", notes="unhone bola dobara call mat karna")
    assert S.get_lead(T, "Naraz")["stage"] == "dnd"
    with pytest.raises(S.TeleError):
        S.start_call(T, "Naraz")


def test_promise_to_pay_marks_dues_book_and_hours(env, fake_ai):
    from app.employee.models import BizDue
    S = _T()
    S.save_settings(T, start_hour="09:00", end_hour="21:00")
    with session() as s:
        s.add(BizDue(tenant_id=T, name="Seema", phone="919876500002", amount_paise=500000, status="open"))
    S.add_lead(T, "Seema", "9876500002", "customer", "dues", amount=5000)
    S.log_call(T, "Seema", notes="Seema ji Monday ko 5000 denge")
    lv = S.get_lead(T, "Seema")
    assert lv["stage"] == "callback" and lv["promise_on"] and _local(lv["next_at"]).weekday() == 0
    assert 8 <= _local(lv["next_at"]).hour < 19                                # dues follow-up inside 8 am - 7 pm
    with session() as s:
        d = s.scalars(select(BizDue).where(BizDue.tenant_id == T)).first()
        assert d.status == "promised" and d.promised_on == lv["promise_on"]


def test_import_report_forget(env, fake_ai):
    S = _T()
    from app.leads import import_leads
    csv = "Name,Mobile,Source,Course\nAnil,9876511111,website,NEET\nBina,9876522222,,JEE\nBad,123,,\n".encode()
    res = import_leads("leads.csv", csv, T)
    out = S.import_list(T, list_id=res.list_id, purpose="sales")
    assert out["added"] == 2
    anil = S.get_lead(T, "Anil")
    assert anil["source"] == "website" and anil["need"] == "NEET" and anil["consent"] is True
    assert S.get_lead(T, "Bina")["consent"] is False and out["cold"] == 1         # sheet without a source = list (cold)
    S.log_call(T, "Anil", outcome="converted")
    rep = S.report(T, 1)
    assert rep["calls"] == 1 and rep["converted"] == 1 and "Calls 1/" in rep["text"]
    assert S.forget(T, "Anil")["say"]
    with pytest.raises(S.TeleError):
        S.get_lead(T, "Anil")
    S.save_settings(T, morning_time=S.local_now(T).strftime("%H:%M"), start_hour="09:00", end_hour="21:00")
    assert T in S.due_mornings() and T not in S.due_mornings()


def test_tools_and_wiring(env, fake_ai):
    from app import voice
    from app.agent.tools import HANDLERS, Ctx, ToolError
    from app.employee import roles
    ctx = conv_ctx()

    def run(tool, **a):
        return asyncio.run(HANDLERS[tool](ctx, **a))
    run("telecall", action="add", name="Ramesh", phone="9876543210", source="website", need="2BHK")
    assert run("telecall_dekho", what="list")["now"] or run("telecall_dekho", what="list")["later"]
    assert run("telecall", action="log", lead="Ramesh", outcome="callback", next_when="kal 4 baje")["lead"]["stage"] == "callback"
    assert run("telecall_dekho", what="lead", lead="Ramesh")["history"]
    staff = Ctx(T, ctx.conversation_id, actor="staff:x")
    with pytest.raises(ToolError):
        asyncio.run(HANDLERS["telecall"](staff, action="settings", business="x"))
    with pytest.raises(ToolError):
        run("telecall", action="log", lead="Nobody")
    assert roles.duty_of("telecall") == "telecalling" and roles.kind_of("telecall_dekho") == "read"
    assert "telecalling" in roles.role_duties("telecaller") and roles.PRESETS["telecalling"]["role"] == "telecaller"
    assert "telecall" in voice.VOICE_TOOL_NAMES


def test_api(env, fake_ai):
    from app import main
    with TestClient(main.app) as c:
        assert "telecall" in c.get("/healthz").json()["features"]
        c.put("/api/telecall/settings", json={"business": "Greenview", "start_hour": "09:00", "end_hour": "21:00"})
        l = c.post("/api/telecall/leads", json={"name": "Ramesh", "phone": "9876543210", "source": "website"}).json()["lead"]
        assert c.post(f"/api/telecall/leads/{l['id']}/script").json()["script"]["opener"]
        st = c.post(f"/api/telecall/leads/{l['id']}/call", json={}).json()
        assert st["tel"] == "tel:9876543210"
        r = c.post(f"/api/telecall/calls/{st['call_id']}/log", json={"outcome": "callback", "next_when": "kal 11 baje"}).json()
        assert r["lead"]["stage"] == "callback"
        assert c.get(f"/api/telecall/leads/{l['id']}").json()["history"][0]["outcome"] == "callback"
        allv = c.get("/api/telecall").json()
        assert allv["report"]["calls"] == 1 and "interested" in allv["outcomes"]
        assert c.patch(f"/api/telecall/leads/{l['id']}", json={"need": "3BHK"}).json()["lead"]["need"] == "3BHK"
        assert c.post(f"/api/telecall/leads/{l['id']}/dnd", json={}).json()["lead"]["stage"] == "dnd"
        assert c.post("/api/telecall/leads", json={"phone": "123"}).status_code == 400
        assert c.delete(f"/api/telecall/leads/{l['id']}").status_code == 200
