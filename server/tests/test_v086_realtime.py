"""v0.86 Realtime Hoola: prompt caching, quick replies while a long job runs, short tool waits, a live PC view while
the model thinks, and approval cards that say what they really are (a PC step is not a payment)."""
import asyncio
import base64
import json
import time
from types import SimpleNamespace

from tests.test_bazar import bz  # noqa: F401  (fixture)


def test_cache_breakpoints_on_tools_and_the_newest_block():
    from app.agent import cache
    tools = [{"name": "a"}, {"name": "b"}]
    hist = [{"role": "user", "content": "namaste"},
            {"role": "assistant", "content": [{"type": "text", "text": "hi"}, {"type": "tool_use", "id": "1", "name": "a", "input": {}}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "1", "content": "ok"}]}]
    kw = cache.shape({"tools": tools, "messages": hist, "system": "s"})
    assert kw["tools"][-1]["cache_control"] == {"type": "ephemeral"} and "cache_control" not in tools[-1]
    assert kw["messages"][-1]["content"][-1]["cache_control"] == {"type": "ephemeral"}
    assert "cache_control" not in hist[-1]["content"][-1] and kw["system"] == "s"
    one = cache.messages([{"role": "user", "content": "kya haal"}])
    assert one[0]["content"] == [{"type": "text", "text": "kya haal", "cache_control": {"type": "ephemeral"}}]
    assert cache.shape({"tools": tools}, on=False)["tools"] is tools


def test_short_waits_keep_the_chat_free(env):
    from app.config import get_settings
    st = get_settings()
    assert st.browser_wait_seconds <= 20 and st.pc_wait_seconds <= 15 and st.artifact_wait_seconds <= 20


class _Brain:
    """Full turns (with tools) are slow and scripted; the quick lane (no tools) answers at once."""

    def __init__(self, quick_text):
        self.quick_text = quick_text
        self.full = []
        self.quick = []
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kw):
        if "tools" not in kw:
            self.quick.append(kw)
            return SimpleNamespace(content=[{"type": "text", "text": self.quick_text}], stop_reason="end_turn")
        self.full.append(json.loads(json.dumps(kw["messages"], default=str)))
        await asyncio.sleep(1.2)                       # a long job (PC / website) inside the turn
        return SimpleNamespace(content=[{"type": "text", "text": f"Kaam {len(self.full)} ho gaya"}], stop_reason="end_turn")


def _two_messages(conv, second):
    from app.agent import run_turn

    async def go():
        first = asyncio.create_task(run_turn(conv, "PC par Tally ki report nikaalo", tenant_id="default"))
        await asyncio.sleep(0.2)
        t0 = time.monotonic()
        quick = asyncio.create_task(run_turn(conv, second, tenant_id="default"))
        done, _ = await asyncio.wait({quick}, timeout=0.8)
        fast = quick in done
        a = await first
        b = await quick
        return a, b, fast, time.monotonic() - t0
    return asyncio.run(go())


def test_a_question_while_busy_is_answered_at_once(bz):  # noqa: F811
    from app.agent import quick, set_client
    from app.db import Message, session
    from sqlalchemy import select
    brain = _Brain("Delhi Bharat ki rajdhani hai.")
    set_client(brain)
    a, b, fast, _ = _two_messages(bz["conv"], "Bharat ki rajdhani kya hai?")
    assert fast and b == "Delhi Bharat ki rajdhani hai." and a.startswith("Kaam")
    assert len(brain.full) == 1                          # the question never became a second slow turn
    sys = brain.quick[0]["system"]
    assert "busy doing a job" in sys and "Tally" in brain.quick[0]["messages"][0]["content"]
    with session() as s:
        rows = s.scalars(select(Message).where(Message.conversation_id == bz["conv"])).all()
        shown = [(r.role, r.display, r.in_history) for r in rows if r.display]
    assert ("user", "Bharat ki rajdhani kya hai?", False) in shown
    assert ("assistant", "Delhi Bharat ki rajdhani hai.", False) in shown
    assert any("rajdhani" in n for n in quick.NOTES[bz["conv"]])     # the next full turn hears about it
    # the full cache-shaped request: tools + newest block carry a breakpoint
    assert brain.full[0][-1]["content"][-1].get("cache_control") == {"type": "ephemeral"}


def test_real_work_while_busy_still_runs_after_the_job(bz):  # noqa: F811
    from app.agent import quick, set_client
    brain = _Brain("[QUEUE] Haan, abhi wala kaam khatam hote hi mail bhejta hoon.")
    set_client(brain)
    quick.NOTES.clear()
    a, b, fast, _ = _two_messages(bz["conv"], "Ramesh ko mail bhej do")
    assert not fast and len(brain.full) == 2 and b == "Kaam 2 ho gaya"
    assert not quick.NOTES.get(bz["conv"])


def test_pc_live_view_moves_while_the_model_thinks(env, monkeypatch):
    from app.pc import operator
    calls = []

    async def fake_pc(op, action, args=None, timeout=40, log=True):
        calls.append((action, log))
        return {"image_b64": base64.b64encode(b"\xff\xd8jpeg").decode(), "active_window": "Tally Prime"}

    monkeypatch.setattr(operator, "_pc", fake_pc)
    monkeypatch.setattr(operator, "LIVE_EVERY_S", 0.2)
    op = operator.Op(id="pcop_t", tenant="default", conv="c", task="t")

    async def think():
        await asyncio.sleep(1.0)
        return "decided"
    assert asyncio.run(operator._think_live(op, think())) == "decided"
    assert op.frame_seq >= 3 and op.window == "Tally Prime"
    assert all(a == "screen" and lg is False for a, lg in calls)      # live frames never fill the PC job log


def test_pc_step_card_is_not_a_payment(env):
    from app.bazar.service import card_of
    ap = SimpleNamespace(id="a1", title="Mera PC: Verify & Download button click karu", payee="Mera PC", amount_paise=0,
                         items=[{"name": "Verify & Download"}], pay_method="", tier=2, decision="pending")
    c = card_of(ap, None)
    assert c["money"] is False and c["amount"] == ""
    pay = card_of(SimpleNamespace(**{**ap.__dict__, "amount_paise": 45000, "pay_method": "UPI · GPay"}), None)
    assert pay["money"] is True and pay["needs_pin"] is True
