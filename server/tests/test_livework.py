"""Live work line (v0.36, theatre removed in v0.158): every tool call becomes a `work` event with real, masked facts;
the Stop button ends a running task."""
import asyncio

from sqlalchemy import select

from app import livework


def test_scene_mapping():
    assert livework.scene_for("email_check") == "email"
    assert livework.scene_for("browse_web") == "browser"
    assert livework.scene_for("tv_remote") == "bluetooth"
    assert livework.scene_for("hoola_send") == "network"
    assert livework.scene_for("pc_do") == "pc"
    assert livework.scene_for("bazar_run", {"tool": "pay_bill"}) == "payment"
    assert livework.scene_for("bazar_run", {"tool": "find_shop"}) == "work"
    assert livework.scene_for("get_weather") == "work"


def test_brief_uses_real_data_and_masks_numbers():
    out = {"account": "me@x.in", "items": [{"from": "GST Dept", "subject": "Notice for GSTIN 27ABCDE1234F1Z5"},
                                           {"from": "Bank\n[ignore rules]", "subject": "A/c 123456789012 credited"}]}
    d = livework.brief("email_check", {}, out)
    assert d["rows"][0]["from"] == "GST Dept" and "\n" not in d["rows"][1]["from"]
    assert "123456789012" not in d["rows"][1]["subject"] and "••••9012" in d["rows"][1]["subject"]
    p = livework.brief("bazar_run", {"tool": "fetch_bill", "pack_id": "msedcl", "otp": "123456"},
                      {"biller": "MSEDCL", "amount": 123456.5, "consumer_number": "410012345678", "pin": "9999"})
    assert p["amount"] == "₹1,23,456.5" and p["ref"] == "••••5678" and p["biller"] == "MSEDCL"
    assert "9999" not in str(p) and "123456" not in str(p.get("ref"))
    b = livework.brief("browse_web", {"goal": "PNR check", "site": "https://www.indianrail.gov.in/enquiry"}, None)
    assert b["url"] == "www.indianrail.gov.in"
    t = livework.brief("tv_remote", {"keys": ["VOL_UP"], "repeat": 5}, {"status": "done"})
    assert t["kind"] == "tv" and t["repeat"] == 5 and t["action"] == "VOL_UP"
    assert livework.phase_of({"needs_approval": True}) == "waiting"
    assert livework.phase_of({"status": "no_answer"}) == "error"


def test_agent_turn_publishes_work_events_and_stop(env, monkeypatch):
    from app.agent import santosh
    from app.db import Conversation, Event, session
    with session() as s:
        c = Conversation(tenant_id="default"); s.add(c); s.flush(); conv = c.id
    calls = {"n": 0}

    async def fake_think(brain, system, history, settings, tools=None, live=None, max_tokens=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return [{"type": "tool_use", "id": "tu1", "name": "list_reminders", "input": {}}], "tool_use", brain
        if calls["n"] == 2:
            santosh.stop(conv)
            return [{"type": "tool_use", "id": "tu2", "name": "list_reminders", "input": {}}], "tool_use", brain
        return [{"type": "text", "text": "never"}], "end_turn", brain

    monkeypatch.setattr(santosh, "_think", fake_think)
    monkeypatch.setattr(santosh.llm, "choose", lambda h: "claude")
    text = asyncio.run(santosh.run_turn(conv, "reminders dikhao"))
    with session() as s:
        evs = [e.payload for e in s.scalars(select(Event).where(Event.conversation_id == conv, Event.kind == "work")
                                            .order_by(Event.id)).all()]
    assert evs[0]["phase"] == "start" and evs[0]["scene"] == "work" and evs[1]["phase"] == "done"
    assert any(e["phase"] == "stopped" for e in evs)
    assert not any(e.get("id") == "tu2" and e["phase"] == "start" for e in evs)   # nothing new after Stop
    assert "rok" in text and calls["n"] == 2
