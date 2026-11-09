"""Parity Phase 2 (docs/CLAUDE_PARITY_PLAN.md): a small, FIXED system prompt for chat turns - core + this chat,
under 12,000 characters and byte-identical turn to turn; everything per-turn rides on her newest message, everything
else is fetched with tools. chat_small_prompt=false brings back the old long prompt."""
from __future__ import annotations

import asyncio
import json

import pytest

from app.config import get_settings
from tests.test_bazar import bz  # noqa: F401  (fresh DB + a real conversation)


@pytest.fixture()
def small(bz, monkeypatch):
    monkeypatch.delenv("CHAT_SMALL_PROMPT", raising=False)   # the conftest pin keeps old suites on the long prompt
    monkeypatch.setenv("HOOLA_LANGUAGE", "en")
    get_settings.cache_clear()
    from app.db import MemoryFact, Profile, session
    with session() as s:
        s.merge(Profile(tenant_id="default", name="Meghana", city="Akola", language="hinglish"))
        for i in range(15):
            s.add(MemoryFact(tenant_id="default", text=f"Her godown in Chakan holds {i * 10} boxes", pinned=(i == 0),
                             source=None if i % 2 else "auto"))
    from app import aboutme
    aboutme.set_text("default", "Meghana runs Newtika Pvt Ltd from Akola and sells solar pumps. " * 20)
    yield bz
    get_settings.cache_clear()


def _run(conv, msgs, monkeypatch):
    from app.agent import santosh
    seen = []

    async def fake_think(brain, system, history, settings, tools=None, live=None, max_tokens=None):
        seen.append({"system": system if isinstance(system, str) else "".join(b.get("text", "") for b in system),
                     "last": json.dumps(history[-1]["content"])})
        return ([{"type": "text", "text": "Done."}], "end_turn", brain)

    monkeypatch.setattr(santosh, "_think", fake_think)
    for m in msgs:
        asyncio.run(santosh.run_turn(conv, m))
    return seen


def test_setting_defaults_on():
    from app.config import Settings
    assert Settings.model_fields["chat_small_prompt"].default is True


def test_small_prompt_is_small_and_byte_identical(small, monkeypatch):
    seen = _run(small["conv"], ["hi kaise ho", "mera gst return file karna hai aur ek email bhejo"], monkeypatch)
    a, b = seen[0]["system"], seen[-1]["system"]
    assert len(a) < 12000, len(a)
    assert a == b                                    # same chat, different messages: the same bytes
    from app.agent.core_prompt import CHAT_HEAD
    assert CHAT_HEAD in a and a.index(CHAT_HEAD) > 6000   # the core comes first, this chat after it
    # the language anchors lang.apply rewrites are found in the core too
    assert "Always write in clear, simple English" in a
    assert "Answer in clear, simple English, whatever language she writes in" in a
    assert "Meghana" in a and "Pinned by her" in a          # her name + memory summary in this chat's block
    assert "boxes (saved" not in a                           # her other facts are fetched (yaad_khojo), not pasted
    assert "Abhi ka samay" not in a and ":" not in a[a.index("Today:") + 6:a.index("Today:") + 40]   # no clock
    # the gst family her words opened: its guide rides on HER message, never in the system prompt
    assert "GST work (she" not in b and "GST work (she" in seen[-1]["last"]


def test_old_long_prompt_with_the_switch_off(small, monkeypatch):
    monkeypatch.setenv("CHAT_SMALL_PROMPT", "false")
    get_settings.cache_clear()
    seen = _run(small["conv"], ["hi kaise ho"], monkeypatch)
    s = seen[0]["system"]
    assert len(s) > 30000 and "Making files" in s and "boxes (saved" in s


def test_cache_breakpoints_after_core_and_chat():
    from app.agent import cache
    from app.agent.core_prompt import CHAT_HEAD
    blocks = cache.system_prompt("CORE TEXT" + CHAT_HEAD + "chat part")
    assert [b["text"] for b in blocks] == ["CORE TEXT", CHAT_HEAD + "chat part"]
    assert all(b.get("cache_control") for b in blocks)
    one = cache.system_prompt("a plain prompt")
    assert len(one) == 1 and one[0]["cache_control"]
    kw = cache.shape({"system": "C" + CHAT_HEAD + "x", "tools": [{"name": "t"}],
                      "messages": [{"role": "user", "content": "hi"}]})
    n = len(kw["system"]) + sum(1 for t in kw["tools"] if t.get("cache_control")) + 1
    assert n <= 4                                    # Anthropic's breakpoint limit


def test_core_carries_the_avatar_name(small):
    from app.avatar.service import save
    from app.agent.core_prompt import core_prompt
    save("default", name="Meera", gender="f")
    c = core_prompt("default", True)
    assert "Meera" in c and "\nYou are Santosh" not in c
    assert core_prompt("default", True) == c          # fixed: nothing per-turn inside


def test_tool_search_brings_the_guide_beside_the_result(small):
    from app.agent import admit
    from app.agent.tools import Ctx
    ctx = Ctx(tenant_id="default", conversation_id=small["conv"])
    ctx.admit = admit.plan_for("hello", get_settings())
    ctx.small_prompt = True
    asyncio.run(admit.tool_search(ctx, need="gst return"))
    g = "\n".join(ctx.native_guides or [])
    assert "GST work (she" in g


def test_kaam_status_lists_waiting_cards(small):
    from app.agent.kaam_tools import KAAM_TOOLS, kaam_status
    from app.agent.tools import Ctx
    assert "cards" in KAAM_TOOLS[0]["input_schema"]["properties"]["action"]["enum"]
    out = asyncio.run(kaam_status(Ctx(tenant_id="default", conversation_id=small["conv"]), action="cards"))
    assert "cards" in out


def test_call_brain_and_routines_keep_their_shape(small):
    from app.agent import santosh
    from app.agent.tools import Ctx
    st = get_settings()
    assert santosh.small_prompt_on(st, Ctx("default", "c", actor="owner"))
    assert not santosh.small_prompt_on(st, Ctx("default", "c", actor="routine"))
    tok = santosh.VOICE_BRAIN_NOW.set(True)
    try:
        assert not santosh.small_prompt_on(st, Ctx("default", "c", actor="owner"))
    finally:
        santosh.VOICE_BRAIN_NOW.reset(tok)
