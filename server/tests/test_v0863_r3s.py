"""v0.863 R3s (docs/HOOLA_APP_REDESIGN_PLAN.md): every step says its kind + housekeeping, and one turn-result record
per chat that the chat list, the /result route and the reply notification all read."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db import Conversation, Message, session

T = "default"


def _chat(cid: str) -> str:
    with session() as s:
        s.add(Conversation(id=cid, tenant_id=T))
    return cid


def _msg(conv: str, role: str, text: str, mins_ago: float = 0):
    with session() as s:
        s.add(Message(conversation_id=conv, role=role, content=[{"type": "text", "text": text}], display=text,
                      created_at=datetime.now(timezone.utc) - timedelta(minutes=mins_ago)))


# ------------------------------------------------------------------ step kinds
def test_classify_kinds_and_housekeeping():
    from app.agent.stepkind import KINDS, classify
    cases = {
        ("web_search", ""): "search", ("email_search", ""): "search", ("scrape_page", ""): "web",
        ("pylab", ""): "run", ("drive_read", ""): "read", ("artifact_make", ""): "write",
        ("agent:Researcher", "Agent Researcher"): "agent", ("yaad_khojo", ""): "memory",
        ("email_draft", ""): "card", ("mystery_tool", "Searching your bills"): "search",
        ("mystery_tool", ""): "other",
    }
    for (tool, label), kind in cases.items():
        k, _ = classify(tool, label)
        assert k == kind, (tool, k, kind)
        assert k in KINDS
    assert classify("tool_search")[1] is True
    assert classify("jaanch", "Checking the answer")[1] is True
    assert classify("kaam_plan")[1] is True
    assert classify("web_search")[1] is False


def test_bus_adds_kind_to_every_step_event(env):
    from app.events import bus
    conv = _chat("c-steps")
    ev = bus.publish(conv, "step", {"tool": "web_search", "label": "Searching the web", "state": "running", "id": "x"})
    assert ev["payload"]["kind"] == "search" and ev["payload"]["housekeeping"] is False
    ev = bus.publish(conv, "step", {"tool": "tool_search", "label": "Finding tools", "state": "done", "id": "y"})
    assert ev["payload"]["housekeeping"] is True
    # a publisher that already set a kind keeps it; other kinds of event are untouched
    ev = bus.publish(conv, "step", {"tool": "x", "label": "", "kind": "edit", "state": "done", "id": "z"})
    assert ev["payload"]["kind"] == "edit"
    ev = bus.publish(conv, "note", {"text": "hi"})
    assert "kind" not in ev["payload"]


# ------------------------------------------------------------------ the turn result
def test_result_done_from_the_reply(env):
    from app import turnresult
    conv = _chat("c-done")
    assert turnresult.result(T, conv)["status"] == ""          # nothing asked yet
    _msg(conv, "user", "Make the GST summary", 2)
    assert turnresult.result(T, conv)["status"] == ""          # asked, nothing running, no answer: no guess
    _msg(conv, "assistant", "**Your October GST summary is ready.** Two bills are missing.", 1)
    r = turnresult.result(T, conv)
    assert r["status"] == "done" and r["needs_you"] is False
    assert r["line"] == "Your October GST summary is ready."


def test_result_from_the_task_log(env):
    from app import turnresult
    from app.agent.pakka import TaskRun
    conv = _chat("c-part")
    _msg(conv, "user", "Send all 40 invoices", 3)
    _msg(conv, "assistant", "I sent 25 of them.", 1)
    with session() as s:
        s.add(TaskRun(tenant_id=T, request="send invoices", outcome="partial", left="15 invoices not sent",
                      conversation_id=conv))
    r = turnresult.result(T, conv)
    assert r["status"] == "partial" and "15 invoices" in r["line"]


def test_result_waiting_and_working_jobs(env):
    from app import turnresult
    from app.kaamwatch import KaamJob
    conv = _chat("c-job")
    _msg(conv, "user", "Build my website", 5)
    now = datetime.now(timezone.utc)
    with session() as s:
        s.add(KaamJob(tenant_id=T, conversation_id=conv, key="k1", kind="site_board", label="Website",
                      title="Pick one of three looks", state="waiting", status="waiting",
                      updated_at=now, moved_at=now, started_at=now))
    r = turnresult.result(T, conv)
    assert r["status"] == "needs_you" and r["needs_you"] and r["line"] == "Pick one of three looks"
    with session() as s:
        j = s.query(KaamJob).filter_by(key="k1").one()
        j.state = "working"
    assert turnresult.result(T, conv)["status"] == "working"


def test_result_queued_and_failed_inbox(env):
    from app import turn_inbox, turnresult
    conv = _chat("c-inbox")
    _msg(conv, "user", "hello", 1)
    turn_inbox.ensure_table()
    with session() as s:
        s.add(turn_inbox.TurnInbox(tenant_id=T, conversation_id=conv, text="hello", status="accepted"))
    assert turnresult.result(T, conv)["status"] == "queued"
    with session() as s:
        r = s.query(turn_inbox.TurnInbox).filter_by(conversation_id=conv).one()
        r.status = "failed"
    assert turnresult.result(T, conv)["status"] == "failed"


def test_made_lists_what_the_ask_produced(env):
    from app import turnresult
    from app.events import bus
    conv = _chat("c-made")
    _msg(conv, "user", "Make a poster", 1)
    bus.publish(conv, "artifact", {"id": "a1", "title": "Diwali poster"})
    bus.publish(conv, "artifact", {"id": "a1", "title": "Diwali poster"})   # the same page's update counts once
    _msg(conv, "assistant", "Your poster is ready.", 0)
    made = turnresult.result(T, conv)["made"]
    assert made == [{"kind": "page", "title": "Diwali poster", "id": "a1"}]


def test_chat_list_and_route_carry_the_result(env, monkeypatch):
    monkeypatch.setattr(env["settings"], "api_key", "secret")
    from app.main import app
    conv = _chat("c-list")
    _msg(conv, "user", "What is the weather", 2)
    _msg(conv, "assistant", "It is 31 degrees and sunny in Akola.", 1)
    h = {"Authorization": "Bearer secret"}
    with TestClient(app) as c:
        rows = c.get("/api/conversations", headers=h).json()["conversations"]
        row = next(r for r in rows if r["id"] == conv)
        assert row["result"]["status"] == "done" and row["result"]["line"].startswith("It is 31 degrees")
        r = c.get(f"/api/conversations/{conv}/result", headers=h)
        assert r.status_code == 200 and r.json()["status"] == "done"
        assert c.get("/api/conversations/nope/result", headers=h).status_code == 404


def test_reply_notification_carries_the_status(env):
    from app import push
    conv = _chat("c-push")
    _msg(conv, "user", "hi", 1)
    _msg(conv, "assistant", "Hello there, all set.", 0)
    ev = {"kind": "message", "id": 7, "at": "", "conv": conv,
          "payload": {"role": "assistant", "text": "Hello there, all set."}}
    out = push.build("tok", ev)
    assert out is not None and out["message"]["data"]["status"] == "done"
    assert out["message"]["data"]["needs_you"] == "0"
