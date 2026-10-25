"""v0.178 Real time: the phone sees every task as it happens - Hoola replies word by word (live=1 deltas, the
same stream the console uses), the PC card narrates every step in Hinglish (Step n/40, 'Soch raha hoon…') and a
turn that crashes can never leave the chat silent (a reply always lands and the typing dots always go off)."""
import asyncio
import types

import pytest

from tests.test_bazar import _events, bz  # noqa: F401
from tests.test_pc_operator import FakeClaude, FakePC, JPEG, run, tu, txt  # noqa: F401


# ---- streamed brain (Claude messages.stream stand-in that feeds text_delta pieces) ----
class _Stream:
    def __init__(self, pieces):
        self.pieces = list(pieces)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    def __aiter__(self):
        return self._gen()

    async def _gen(self):
        for p in self.pieces:
            yield types.SimpleNamespace(type="content_block_delta", delta=types.SimpleNamespace(type="text_delta", text=p))

    async def get_final_message(self):
        return types.SimpleNamespace(
            content=[{"type": "text", "text": "".join(self.pieces)}], stop_reason="end_turn",
            usage=types.SimpleNamespace(input_tokens=10, output_tokens=5), model="claude-test")


class StreamClaude:
    def __init__(self, pieces):
        self.pieces = pieces
        self.seen = []
        self.messages = self

    def stream(self, **kw):
        self.seen.append(kw)
        return _Stream(self.pieces)


async def _turn_collecting(conv, text, brain):
    from app.agent import set_client
    from app.agent.santosh import run_turn
    from app.events import bus
    set_client(brain)
    q = bus.subscribe(conv)
    out = await run_turn(conv, text, tenant_id="default")
    evs = []
    while not q.empty():
        evs.append(q.get_nowait())
    bus.unsubscribe(conv, q)
    return out, evs


def test_reply_streams_word_by_word_to_a_live_stream(bz):
    """The phone (live=1) sees reply_start -> deltas -> reply_end while the words are written, and the final
    message carries the same turn so the bubble hands over cleanly."""
    conv = bz["conv"]
    out, evs = run(_turn_collecting(conv, "namaste", StreamClaude(["Namaste! ", "Main ", "Hoola hoon."])))
    kinds = [e["kind"] for e in evs]
    assert "reply_start" in kinds and "delta" in kinds and "reply_end" in kinds
    assert out.strip() == "Namaste! Main Hoola hoon."
    deltas = [e for e in evs if e["kind"] == "delta"]
    assert deltas and all(e.get("live") is True for e in deltas)   # live-only: an old stream (live=0) never gets them
    assert "".join(d["payload"]["text"] for d in deltas).strip() == out.strip()
    start = next(e for e in evs if e["kind"] == "reply_start")
    end = next(e for e in evs if e["kind"] == "reply_end")
    final = [e for e in evs if e["kind"] == "message" and e["payload"].get("role") == "assistant"][-1]
    assert final["payload"].get("turn") == start["payload"]["turn"]     # the app drops its bubble on this
    assert end["payload"]["turn"] == start["payload"]["turn"]


def test_no_streaming_when_the_brain_cannot_stream(bz):
    """A plain create()-only brain still answers; no live events are invented (old behaviour intact)."""
    class PlainClaude:
        def __init__(self):
            self.messages = self

        async def create(self, **kw):
            return types.SimpleNamespace(content=[{"type": "text", "text": "Seedha jawab."}], stop_reason="end_turn")

    conv = bz["conv"]
    out, evs = run(_turn_collecting(conv, "hi", PlainClaude()))
    assert out == "Seedha jawab."
    assert not [e for e in evs if e["kind"] == "delta"]   # no words are invented as deltas; start/end markers are fine


def test_crashed_turn_still_replies_and_typing_goes_off(bz, monkeypatch):
    """The never-silent promise: a crash anywhere in the turn still leaves a reply in the chat and the typing
    dots off (owner: 'some tasks never replied')."""
    conv = bz["conv"]
    import app.agent.santosh as s

    async def boom(*a, **k):
        raise RuntimeError("andar se toot gaya")

    monkeypatch.setattr(s, "_run_turn", boom)
    out = run(s.run_turn(conv, "kuch karo", tenant_id="default"))
    assert out.strip()
    msgs = _events(conv, "message")
    assert any(m.get("source") == "error" for m in msgs)
    typing = _events(conv, "typing")
    assert typing and typing[-1]["on"] is False
    from app.db import Message, session
    from sqlalchemy import select
    with session() as sess:
        rows = sess.scalars(select(Message).where(Message.conversation_id == conv,
                                                  Message.role == "assistant", Message.display.is_not(None))).all()
    assert any("gadbad" in (r.display or "") for r in rows)   # it is saved, not only shown once


def test_turn_running_reflects_the_chat_lock(bz):
    """The SSE typing refresh only fires while a turn really holds the chat."""
    from app.agent import santosh
    conv = bz["conv"]

    async def go():
        assert santosh.turn_running(conv) is False
        async with santosh._locks[conv]:
            assert santosh.turn_running(conv) is True
        return santosh.turn_running(conv)

    assert run(go()) is False


@pytest.fixture
def op(bz, monkeypatch):  # noqa: F811
    from app.pc import operator
    pc = FakePC()
    monkeypatch.setattr(operator, "_pc", pc)

    class Conn:
        info = {"control": True}
    from app.pc.hub import hub
    monkeypatch.setattr(hub, "is_online", lambda t, d=None: True)
    monkeypatch.setattr(hub, "online", lambda t: [Conn()])
    yield operator, pc, bz


def test_pc_card_narrates_every_step_live(op, monkeypatch):
    """The chat's PC card gets a browser event per step with Step n/40, a Hinglish line of what is happening
    right now, and the Soch state while the vision call runs - the task is seen in real time."""
    operator, pc, bz = op  # noqa: F811
    claude = FakeClaude([
        [txt("Chrome kholta hoon"), tu(1, "open_app", name="Chrome")],
        [tu(2, "type", text="Raaz-Baatein-123")],
        [tu(3, "done", answer="ho gaya", success=True)],
    ])
    import app.agent.santosh as s
    monkeypatch.setattr(s, "get_client", lambda: claude)

    async def go():
        r = await operator.start("default", bz["conv"], "Chrome kholo aur likho", wait=0)
        o = operator.get("default", r["session_id"])
        await asyncio.wait_for(o.done_event.wait(), 10)
        return o

    o = run(go())
    assert o.status == "done"
    evs = _events(bz["conv"], "browser")
    assert evs and evs[0]["session_id"].startswith("pcop_")
    assert all(e.get("steps_max") == operator.MAX_STEPS for e in evs)
    assert any(e.get("thinking") is True for e in evs)                       # 'Soch raha hoon…' state was on the card
    steps = [e for e in evs if e.get("step")]
    seq = [e["step"] for e in steps]
    assert seq == sorted(seq) and set(seq) == {1, 2, 3}                      # every step was on the card, in order
                                                                             # (a step repeats while she thinks about the next one - by design)
    actions = [str(e.get("action") or "") for e in steps]
    assert any("khol raha hoon" in a for a in actions)                       # human narration, not tool-speak
    assert any("likh raha hoon" in a for a in actions)
    assert not any("Raaz-Baatein-123" in a for a in actions)                 # privacy: typed text never on the card
    works = _events(bz["conv"], "work")
    labels = [w.get("label") or "" for w in works]
    assert any(f"PC (1/{operator.MAX_STEPS})" in lb for lb in labels)        # the work line counts the steps too
    assert not any("Raaz-Baatein-123" in lb for lb in labels)


def test_pc_narration_is_private_and_human(op, monkeypatch):
    """_say speaks like a person and never echoes what is typed / URLs beyond the host."""
    from app.pc.operator import _say
    assert _say("type", {"text": "Mera Aadhaar 1234-5678-9012"}) == "likh raha hoon (27 akshar)"
    assert _say("open_url", {"url": "https://web.whatsapp.com/send?phone=919999999999"}) == "web.whatsapp.com khol raha hoon"
    assert _say("open_app", {"name": "Chrome"}) == "Chrome khol raha hoon"
    assert _say("key", {"keys": "ctrl+s"}) == "'ctrl+s' daba raha hoon"
    assert _say("wait", {}) == "khulne ka intezaar…"
    assert _say("screenshot", {"monitor": "all"}) == "dono screen dekh raha hoon"
    assert _say("ask_approval", {}) == "aapki manzoori ka intezaar…"
