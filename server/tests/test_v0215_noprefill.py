"""v0.215.0 NO-PREFILL - every model call ends with a user message; wake turns see their own words.

The owner's report: 'FOR EVERY LONG WORK HOOLA AI SHOW THIS ERROR (Error code: 400 - ... This model does
not support assistant message prefill. The conversation must end with a user message.)'. RCA: the
production model snapshot now refuses a conversation whose LAST message is an assistant message, and two
paths built exactly that shape:

- kaam_followup._wake_turn (and turn_inbox re-runs) call run_turn(..., save_user=False): the turn's own
  words were never saved AND never entered the model array, so the first call went out as
  [.., previous assistant reply] -> 400 on EVERY wake turn of EVERY long job (and the brain never even
  saw the job report it was supposed to speak about - masked for months because the old snapshot silently
  accepted assistant-final arrays and rambled on).
- any future caller of _call_brain with a badly-shaped array.

Fixes, each tested here: (1) _run_turn appends the unsaved words to the IN-MEMORY history when
save_user=False (nothing double-saved); (2) _call_brain's prefill guard sends a user message last on a
COPY for every brain, without mutating the caller's list.
"""
import asyncio
import json
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401  (the env fixture: fresh DB, dry-run WhatsApp)

REPO = Path(__file__).resolve().parents[2]


class _FakeMsg:
    def __init__(self, text: str = "theek hai, natija dekh liya"):
        self.content = [{"type": "text", "text": text}]
        self.stop_reason = "end_turn"


class _FakeMessages:
    def __init__(self, log: list):
        self._log = log

    async def create(self, **kw):
        self._log.append(kw)
        return _FakeMsg()


class _FakeClient:
    def __init__(self):
        self.log: list[dict] = []
        self.messages = _FakeMessages(self.log)


@pytest.fixture()
def claude_only(bz, monkeypatch):
    """Fake Anthropic client + no cheap brain + no self-check, so every call is captured and deterministic."""
    from app.agent import llm, santosh
    from app.config import get_settings

    fake = _FakeClient()
    old = santosh._client
    santosh.set_client(fake)
    monkeypatch.setattr(llm, "cheap_brain", lambda: None)
    st = get_settings()
    old_check = st.agent_self_check
    st.agent_self_check = False
    yield fake, st
    st.agent_self_check = old_check
    santosh.set_client(old)


def _seed(conv: str, user: str, assistant: str) -> None:
    from app.agent import santosh
    santosh._save(conv, "user", user, display=user)
    santosh._save(conv, "assistant", [{"type": "text", "text": assistant}], display=assistant)


def _rows(conv: str, role: str) -> int:
    from sqlalchemy import select
    from app.db import Message, session
    with session() as s:
        return len(s.scalars(select(Message).where(Message.conversation_id == conv, Message.role == role)).all())


def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.329.0"
    assert "0.329.0+369" in (REPO / "pubspec.yaml").read_text()


def test_wake_turn_ends_user_and_carries_its_words(claude_only, bz):
    """THE bug: a wake turn (save_user=False) went out as [.., previous assistant] -> 400 prefill,
    and the wake text never reached the brain at all. Now: user-last WITH the wake text, nothing double-saved."""
    from app.agent import santosh
    conv = bz["conv"]
    _seed(conv, "calender pe meeting daal do", "theek hai, daal di hai.")
    before = (_rows(conv, "user"), _rows(conv, "assistant"))
    wake = "[Santosh worker update, not the user] Ek background kaam ka natija abhi aaya hai:\nKaam: Calendar meeting\nNatija: poora ho gaya"

    async def go():
        return await santosh.run_turn(conv, wake, tenant_id="default", actor="wake", save_user=False)

    out = asyncio.run(go())
    fake, _st = claude_only
    assert fake.log, "the wake turn never called the model"
    first = fake.log[0]["messages"]
    assert first[-1]["role"] == "user"
    assert "background kaam ka natija" in json.dumps(first[-1]["content"], ensure_ascii=False)
    assert out.strip() == "theek hai, natija dekh liya"
    after = (_rows(conv, "user"), _rows(conv, "assistant"))
    # v0.221: the job's RESULT is now kept in history (one user row with display None - never shown as her words);
    # her own rows never double
    assert after[0] == before[0] + 1
    from app.db import Message, session
    from sqlalchemy import select
    with session() as s:
        mine = s.scalars(select(Message).where(Message.conversation_id == conv, Message.role == "user",
                                               Message.display.is_not(None))).all()
        saved = s.scalars(select(Message).where(Message.conversation_id == conv, Message.role == "user")
                          .order_by(Message.id.desc())).first()
    assert len(mine) == before[0] and saved.display is None and "Calendar meeting" in saved.content
    assert after[1] == before[1] + 1                   # only Hoola's reply landed


def test_inbox_rerun_after_crash_reply(claude_only, bz):
    """A crashed turn's guard saves an assistant error row after her words; the save_user=False re-run
    used to send [user, assistant-error] -> 400 again, forever. Now her words ride again, user-last."""
    from app.agent import santosh
    conv = bz["conv"]
    _seed(conv, "mera sawal", "Maaf kijiye, abhi kuch gadbad ho gayi. (Error code: 400)")

    async def go():
        return await santosh.run_turn(conv, "mera sawal", tenant_id="default", actor="routine", save_user=False)

    asyncio.run(go())
    fake, _st = claude_only
    first = fake.log[0]["messages"]
    assert first[-1]["role"] == "user"
    assert "mera sawal" in json.dumps(first[-1]["content"], ensure_ascii=False)


def test_normal_turn_still_user_last(claude_only, bz):
    """save_user=True turns kept working: her row is in the DB before the load, the array ends with it."""
    from app.agent import santosh
    conv = bz["conv"]
    _seed(conv, "purana sawal", "purana jawab")

    async def go():
        return await santosh.run_turn(conv, "naya sawal", tenant_id="default", actor="routine")

    asyncio.run(go())
    fake, _st = claude_only
    first = fake.log[0]["messages"]
    assert first[-1]["role"] == "user"
    assert "naya sawal" in json.dumps(first[-1]["content"], ensure_ascii=False)
    assert _rows(conv, "user") == 2


def test_call_brain_guard_copies_not_mutates(claude_only):
    """The belt-and-braces guard: an assistant-final array goes out user-last, and the CALLER's list is
    untouched (team sub-agents keep appending to theirs). A user-final array passes through as-is."""
    from app.agent import santosh
    from app.config import get_settings
    fake, st = claude_only
    history = [{"role": "assistant", "content": [{"type": "text", "text": "purana jawab"}]}]

    async def go():
        return await santosh._call_brain("claude", "system", history, st, tools=[])

    asyncio.run(go())
    sent = fake.log[0]["messages"]
    assert sent[-1]["role"] == "user"
    assert history[-1]["role"] == "assistant" and len(history) == 1     # caller's list untouched
    history2 = [{"role": "user", "content": "sawal"}]

    async def go2():
        await santosh._call_brain("claude", "system", history2, st, tools=[])

    asyncio.run(go2())
    sent2 = fake.log[1]["messages"]
    assert len(sent2) == 1 and sent2[-1]["role"] == "user"              # no extra message appended


def test_empty_history_guard(claude_only):
    """Even a bare array (no history at all) goes out user-last instead of 400ing on an empty messages list."""
    from app.agent import santosh
    from app.config import get_settings
    fake, st = claude_only

    async def go():
        await santosh._call_brain("claude", "system", [], st, tools=[])

    asyncio.run(go())
    assert fake.log[0]["messages"][-1]["role"] == "user"
