"""v0.179 cards close themselves: a resolved ask card shows its resolved state on reload (never the original
"waiting" again), jobs that end close their open ask, the TTL janitor expires asks nobody answered, and her
chat's waiting strip goes quiet — in the feed, in `extra`, and in waiting_cards."""
import asyncio
import json
from datetime import timedelta

import pytest

from app.db import now


@pytest.fixture
def api(env, monkeypatch):
    from app import convs
    convs._CACHE.clear()
    yield env
    convs._CACHE.clear()


def _conv(tenant):
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id=tenant)
        s.add(c)
        s.flush()
        return c.id


def _latest(api, conv, kind):
    """The card's latest payload as the phone would see it after a reload (timeline collapse)."""
    from app.events import timeline
    t = api["settings"].tenant_id
    rows = [e for e in timeline(conv, t, 400)["events"] if e["kind"] == kind]
    assert rows, f"no {kind} card on the timeline"
    return rows[-1]["payload"]


def _backdate(model, id_, hours):
    from app.db import session
    with session() as s:
        row = s.get(model, id_)
        row.created_at = now() - timedelta(hours=hours)


def test_resolved_ask_card_stays_resolved_after_reload(api):
    """THE old bug: the collapse kept the card's FIRST payload, so every reload resurrected the waiting state."""
    from app.events import bus, needs_her, timeline, waiting_cards
    t = api["settings"].tenant_id
    conv = _conv(t)
    bus.publish(conv, "operator_ask", {"id": "a1", "kind": "otp", "status": "pending", "reason": "OTP bhariye"})
    bus.publish(conv, "operator_ask", {"id": "a1", "kind": "otp", "status": "approved", "decided": True})
    p = _latest(api, conv, "operator_ask")
    assert p["status"] == "approved" and p["decided"] is True
    tl = timeline(conv, t, 60)
    card = [e for e in tl["events"] if e["kind"] == "operator_ask"][0]
    assert not needs_her(card["kind"], card["payload"])
    assert all(w["key"] != "operator_ask:id:a1" for w in waiting_cards(t))


def test_finished_operator_task_closes_its_ask_card(api):
    """Work ends while a question is open: the ask card goes terminal on its own key (never waits forever)."""
    from app.events import bus, waiting_cards
    from app.operator.models import OperatorTask
    from app.operator.service import _set
    t = api["settings"].tenant_id
    conv = _conv(t)
    with __import__("app.db", fromlist=["session"]).session() as s:
        row = OperatorTask(tenant_id=t, conversation_id=conv, task="bill nikalo",
                           pending=json.dumps({"id": "a9", "kind": "question", "reason": "consumer number?"}))
        s.add(row)
        s.flush()
        tid = row.id
    _set(tid, status="done", stage="Ho gaya")
    p = _latest(api, conv, "operator_ask")
    assert p["id"] == "a9" and p["status"] == "expired" and p["decided"] is True
    assert all(w["key"] != "operator_ask:id:a9" for w in waiting_cards(t))
    bus.publish(conv, "message", {"role": "assistant", "text": "done"})   # keep the chat alive for the timeline read


def test_resolve_with_browser_gone_closes_the_ask(api):
    """She taps a card whose browser is already gone: the card closes instead of erroring into a zombie."""
    from app.operator import service as op
    from app.operator.models import OperatorTask
    t = api["settings"].tenant_id
    conv = _conv(t)
    with __import__("app.db", fromlist=["session"]).session() as s:
        row = OperatorTask(tenant_id=t, conversation_id=conv, task="site ka kaam", status="waiting",
                           pending=json.dumps({"id": "aX", "kind": "otp", "status": "pending", "reason": "OTP"}))
        s.add(row)
        s.flush()
        rid = row.id
    op._ops.pop(t, None)   # no browser for this tenant
    with pytest.raises(op.OperatorJobError):
        asyncio.run(op.resolve(t, "aX", "approved"))
    p = _latest(api, conv, "operator_ask")
    assert p["id"] == "aX" and p["status"] == "expired"
    with __import__("app.db", fromlist=["session"]).session() as s:
        assert s.get(OperatorTask, rid).pending == ""


def test_operator_ask_expires_after_ttl(api):
    """The worker sweep: an ask that waited longer than ask_ttl_hours stops waiting (card closed, job stopped)."""
    from app.events import waiting_cards
    from app.operator.models import OperatorTask
    from app.operator.service import expire_stale_asks
    t = api["settings"].tenant_id
    conv = _conv(t)
    with __import__("app.db", fromlist=["session"]).session() as s:
        row = OperatorTask(tenant_id=t, conversation_id=conv, task="kaam", status="waiting",
                           pending=json.dumps({"id": "aT", "kind": "captcha", "status": "pending", "reason": "captcha"}))
        s.add(row)
        s.flush()
        tid = row.id
        row2 = s.get(OperatorTask, tid)
        row2.updated_at = now() - timedelta(hours=30)
    assert expire_stale_asks(24) == 1
    p = _latest(api, conv, "operator_ask")
    assert p["id"] == "aT" and p["status"] == "expired"
    with __import__("app.db", fromlist=["session"]).session() as s:
        r = s.get(OperatorTask, tid)
        assert r.status == "stopped" and r.pending == ""
    assert all(w["key"] != "operator_ask:id:aT" for w in waiting_cards(t))


def test_ask_form_expires_after_ttl(api):
    from app import askform
    from app.events import waiting_cards
    t = api["settings"].tenant_id
    conv = _conv(t)
    v = askform.create(t, conv, "Bank details", [
        {"name": "ac", "label": "Account number", "kind": "text"},
    ], why="payment ke liye")
    _backdate(askform.AskForm, v["id"], 30)
    assert askform.expire_asks(24) == 1
    p = _latest(api, conv, "ask_form")
    assert p["id"] == v["id"] and p["status"] == "expired"
    assert all(w["key"] != f"ask_form:id:{v['id']}" for w in waiting_cards(t))
    with pytest.raises(askform.FormError):
        askform.answer(t, v["id"], {"ac": "1234"})   # an expired form takes no answers


def test_bazar_approval_expires_after_ttl(api):
    from app.bazar.db import Approval, Task
    from app.bazar.service import ensure_user, expire_approvals
    from app.db import session
    from app.events import waiting_cards
    t = api["settings"].tenant_id
    conv = _conv(t)
    with session() as s:
        u = ensure_user(s, t)
        task = Task(user_id=u.id, text="order karo", conversation_id=conv)
        s.add(task)
        s.flush()
        ap = Approval(task_id=task.id, user_id=u.id, tier=2, title="Bijli bill", amount_paise=54000,
                      conversation_id=conv, action={}, items=[])
        s.add(ap)
        s.flush()
        apid = ap.id
    _backdate(Approval, apid, 30)
    assert expire_approvals(24) == 1
    p = _latest(api, conv, "bazar_approval")
    assert p["id"] == apid and p["status"] == "expired"
    assert all(w["key"] != f"bazar_approval:id:{apid}" for w in waiting_cards(t))
    with session() as s:
        assert s.get(Approval, apid).decision == "expired"


def test_pg_write_expires_after_ttl(api):
    from app.db import session
    from app.events import waiting_cards
    from app.pgdb.service import PgConn, PgWrite, expire_asks
    t = api["settings"].tenant_id
    conv = _conv(t)
    with session() as s:
        c = PgConn(tenant_id=t, name="Bills DB", label="u@host/db", dsn_sealed="x")
        s.add(c)
        s.flush()
        w = PgWrite(tenant_id=t, conn_id=c.id, conversation_id=conv, number="W-0001", sql="delete from x;",
                    reason="purana data", kind="data", count=1, hash="h")
        s.add(w)
        s.flush()
        wid = w.id
    _backdate(PgWrite, wid, 30)
    assert expire_asks(24) == 1
    p = _latest(api, conv, "pg_write")
    assert p["id"] == wid and p["status"] == "stale"
    assert all(w["key"] != f"pg_write:id:{wid}" for w in waiting_cards(t))


def test_employee_ask_expiry_reaches_the_chat(api):
    """expire_asks already flipped the DB row; v0.179 the chat hears it too (the card stops asking)."""
    from app.db import session
    from app.employee.models import EmployeeAsk
    from app.employee import service as emp
    from app.events import waiting_cards
    t = api["settings"].tenant_id
    conv = _conv(t)
    with session() as s:
        a = EmployeeAsk(tenant_id=t, conversation_id=conv, tool="email_draft", duty="email", why="customer ne maanga", args="{}")
        s.add(a)
        s.flush()
        aid = a.id
    _backdate(EmployeeAsk, aid, 50)
    assert emp.expire_asks() == 1
    p = _latest(api, conv, "employee_ask")
    assert p["id"] == aid and p["status"] == "expired"
    assert all(w["key"] != f"employee_ask:id:{aid}" for w in waiting_cards(t))


def test_waiting_page_keeps_only_truly_waiting_cards(api):
    """extra[-20:] must re-pin a card only while it still waits: once resolved it stays in its own page."""
    from app.events import bus, timeline
    t = api["settings"].tenant_id
    conv = _conv(t)
    bus.publish(conv, "bazar_approval", {"id": "apE", "title": "Order", "status": "pending"})
    bus.publish(conv, "bazar_approval", {"id": "apE", "title": "Order", "status": "approved",
                                         "result": {"message": "ho gaya"}})
    for i in range(200):
        bus.publish(conv, "message", {"role": "user", "text": f"m{i}"})
    tl = timeline(conv, t, 60)
    assert not any(e["kind"] == "bazar_approval" for e in tl["events"])   # resolved, not re-pinned above the page
    keys = [e["key"] for e in tl["events"]]
    assert all(k != "bazar_approval:id:apE" for k in keys)
