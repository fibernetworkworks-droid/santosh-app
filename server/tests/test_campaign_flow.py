"""End-to-end: Santosh (with a scripted stand-in for Claude) runs a full WhatsApp campaign in test mode."""
import asyncio
import json
from datetime import timedelta
from types import SimpleNamespace

from sqlalchemy import select, update

from app import campaigns as camp
from app import worker
from app.agent import run_turn, set_client
from app.db import Campaign, Conversation, Event, Message, OutboundMessage, now, session
from app.leads import import_leads

from .conftest import SAMPLE

TEMPLATE = {"name": "diwali_offer_2026", "language": "hi", "category": "MARKETING",
            "body": "Namaste {{1}}, is Diwali hamari dukaan par sabhi saamaan par 30% chhoot hai. Offer 2 November tak hai.",
            "example_values": ["Rahul"], "footer": "STOP likhkar band karein"}


class ScriptedClaude:
    """Plays back a fixed sequence of responses and records what it was sent."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kw):
        self.calls.append(json.loads(json.dumps(kw["messages"], default=str)))
        step = self.script.pop(0)
        blocks = step(kw["messages"]) if callable(step) else step
        stop = "tool_use" if any(b["type"] == "tool_use" for b in blocks) else "end_turn"
        return SimpleNamespace(content=blocks, stop_reason=stop)


def last_result(messages):
    for m in reversed(messages):
        if m["role"] == "user" and isinstance(m["content"], list):
            for b in m["content"]:
                if b.get("type") == "tool_result":
                    return b
    return None


def tool(name, args, i):
    return [{"type": "tool_use", "id": f"tu_{i}", "name": name, "input": args}]


def text(t):
    return [{"type": "text", "text": t}]


def new_conv():
    with session() as s:
        c = Conversation(tenant_id="default"); s.add(c); s.flush(); return c.id


async def drain(wa, rounds=6):
    for _ in range(rounds):
        await worker.check_approvals(force=True)
        await worker.send_batches(max_seconds=60)
        for cid in camp.apply_message_status(wa.flush_all()):
            camp.publish_campaign(cid)


def test_full_campaign(env):
    wa = env["wa"]
    res = import_leads(SAMPLE.name, SAMPLE.read_bytes(), "default")
    conv = new_conv()
    state = {}

    def remember_template(msgs):
        r = json.loads(last_result(msgs)["content"])
        state["template_id"] = r["template_id"]
        return tool("create_campaign", {"title": "Diwali WhatsApp Campaign", "lead_list_id": res.list_id,
                                        "template_id": r["template_id"],
                                        "param_mapping": [{"source": "lead_name", "fallback": "ji"}],
                                        "consent_confirmed": False, "auto_send": True}, 4)

    def expect_consent_error(msgs):
        r = last_result(msgs)
        assert r.get("is_error") and "CONSENT_REQUIRED" in r["content"]
        return text("Kya in sab logon ne aapse WhatsApp par message lene ki permission di hai?")

    claude = ScriptedClaude([
        tool("get_lead_list", {"list_id": res.list_id}, 1),
        tool("check_template", TEMPLATE, 2),
        tool("submit_template", TEMPLATE, 3),
        remember_template,
        expect_consent_error,
        # second user turn: consent given
        lambda msgs: tool("create_campaign", {"title": "Diwali WhatsApp Campaign", "lead_list_id": res.list_id,
                                              "template_id": state["template_id"],
                                              "param_mapping": [{"source": "lead_name", "fallback": "ji"}],
                                              "consent_confirmed": True, "auto_send": True}, 5),
        text("Campaign bana diya. Meta approve karte hi bhej dunga."),
        # third turn: report
        lambda msgs: tool("get_campaign_status", {"campaign_id": state["campaign_id"]}, 6),
        text("Report upar hai."),
    ])
    set_client(claude)

    reply = asyncio.run(run_turn(conv, "Diwali offer ka campaign sab leads ko bhej do. 30% off, 2 Nov tak."))
    assert "permission" in reply
    reply = asyncio.run(run_turn(conv, "Haan, sabne consent diya hai."))
    assert "Campaign bana diya" in reply

    with session() as s:
        c = s.scalars(select(Campaign).where(Campaign.conversation_id == conv)).one()
        state["campaign_id"] = c.id
        assert c.status == "awaiting_approval" and c.auto_send
        params = s.scalars(select(OutboundMessage.params).where(OutboundMessage.campaign_id == c.id)).all()
        assert ["Rahul"] in params and ["ji"] in params      # first name, and fallback for the blank name

    asyncio.run(drain(wa))
    with session() as s:   # pretend statuses had time to settle
        s.execute(update(OutboundMessage).values(sent_at=now() - timedelta(minutes=5)))
    asyncio.run(worker.finish_campaigns())

    v = camp.campaign_view(state["campaign_id"])
    assert v["status"] == "completed"
    n = v["counts"]
    assert n["total"] == 11 and n["queued"] == 0
    assert n["sent"] + n["failed"] == 11
    assert n["delivered"] >= n["read"] > 0

    with session() as s:
        notes = s.scalars(select(Message.display).where(Message.conversation_id == conv,
                                                        Message.in_history.is_(False))).all()
        assert any("approve" in x for x in notes)
        assert any("poora ho gaya" in x for x in notes)
        kinds = set(s.scalars(select(Event.kind).where(Event.conversation_id == conv)).all())
        assert {"message", "step", "campaign", "typing"} <= kinds

    # next turn: worker notices are handed to Santosh as context
    asyncio.run(run_turn(conv, "Kaisa raha?"))
    sent_to_claude = json.dumps(claude.calls[-2], ensure_ascii=False)
    assert "[Santosh worker update]" in sent_to_claude and "poora ho gaya" in sent_to_claude


def test_daily_limit_and_ready_gate(env, monkeypatch):
    wa = env["wa"]
    monkeypatch.setattr(env["settings"], "max_daily_sends", 3)
    res = import_leads(SAMPLE.name, SAMPLE.read_bytes(), "default")
    conv = new_conv()
    from app.agent.tools import Ctx, submit_template
    t = asyncio.run(submit_template(Ctx("default", conv), **TEMPLATE))
    v = camp.create_campaign(tenant_id="default", conversation_id=conv, title="Test", lead_list_id=res.list_id,
                             template_id=t["template_id"], param_mapping=[{"source": "lead_name"}],
                             consent_confirmed=True, auto_send=False)
    asyncio.run(worker.check_approvals(force=True))
    assert camp.campaign_view(v["id"])["status"] == "ready"        # approved but waits for a yes
    asyncio.run(worker.send_batches(max_seconds=60))
    assert camp.campaign_view(v["id"])["counts"]["sent"] == 0

    camp.confirm_send(v["id"])
    asyncio.run(worker.send_batches(max_seconds=60))
    asyncio.run(worker.send_batches(max_seconds=60))
    view = camp.campaign_view(v["id"])
    assert view["counts"]["total"] - view["counts"]["queued"] == 3
    assert view["status"] == "waiting_limit"


def test_live_mode_never_messages_sample_numbers(env):
    res = import_leads(SAMPLE.name, SAMPLE.read_bytes(), "default")
    conv = new_conv()
    from app.agent.tools import Ctx, submit_template
    t = asyncio.run(submit_template(Ctx("default", conv), **TEMPLATE))
    try:
        camp.create_campaign(tenant_id="default", conversation_id=conv, title="x", lead_list_id=res.list_id,
                             template_id=t["template_id"], param_mapping=[{"source": "lead_name"}],
                             consent_confirmed=True, auto_send=True, live_mode=True)
        assert False, "should refuse"
    except camp.CampaignError as e:
        assert "sample numbers" in str(e)


def test_history_repair_after_crash(env):
    from app.agent.santosh import _sanitize
    msgs = [{"role": "user", "content": "hi"},
            {"role": "assistant", "content": [{"type": "text", "text": "ok"}, {"type": "tool_use", "id": "a", "name": "x", "input": {}}]},
            {"role": "assistant", "content": [{"type": "text", "text": "error"}]},
            {"role": "user", "content": "again"}]
    out = _sanitize(msgs)
    assert [m["role"] for m in out] == ["user", "assistant", "user"]
    assert all(b["type"] == "text" for b in out[1]["content"])
