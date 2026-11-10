"""Parity Phase 7 (docs/CLAUDE_PARITY_PLAN.md): ONE memory, Claude style.

A chat turn carries one short memory summary (her page + pinned facts, in the per-chat block of the system prompt)
plus a capped 'since your last reply' note (job state, card news) and her skill NAMES on her newest message. The
diary, her recent words, facts by meaning, recalled chats, the coder primer and the 9k described skills list are no
longer pasted: yaad_khojo (memory.search_all) fetches them. chat_one_memory=false brings back today's blocks; a call's
brain turn keeps its own shape.

Measured with server/tools/prompt_measure.py (seeded tenant: 15 facts, a memory page, a past chat, 6 finished jobs,
a coder work note, the starter skills): the memory text on her newest message went from 10,565 / 10,683 chars (two
turns) to 595 / 585 - of the old block 8,952 chars was the described skills list, 634 her recent words, 544 the diary.
The cap below (2,500) = the note cap (1,800) + the skill names (600) + headroom for the separators.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from app.config import get_settings
from tests.test_v0473_hoola_coder import cod  # noqa: F401  (fresh coder vault, switch on)

T = "default"
MEMORY_CAP = 2500


@pytest.fixture()
def one(cod, monkeypatch):
    monkeypatch.delenv("CHAT_ONE_MEMORY", raising=False)     # the conftest pin keeps old suites on the old blocks
    monkeypatch.delenv("CHAT_SMALL_PROMPT", raising=False)
    monkeypatch.setenv("HOOLA_LANGUAGE", "en")
    get_settings.cache_clear()
    from app import aboutme, kaamwatch, yaad
    from app.agent.pakka import TaskRun
    from app.coder import store
    from app.db import Conversation, Message, MemoryFact, Profile, now, session
    with session() as s:
        main = Conversation(tenant_id=T, title="Today")
        old = Conversation(tenant_id=T, title="Sharma quotation")
        s.add_all([main, old])
        s.flush()
        conv, old_id = main.id, old.id
        s.merge(Profile(tenant_id=T, name="Meghana", city="Akola", language="hinglish"))
        for i in range(15):
            s.add(MemoryFact(tenant_id=T, text=f"Her godown in Chakan holds {i * 10} boxes", pinned=(i == 0),
                             source=None if i % 2 else "auto"))
        s.add(Message(conversation_id=old_id, role="user", content="Sharma ji ka quotation: 40 Kesari boxes Rs 180 each",
                      display="Sharma ji ka quotation: 40 Kesari boxes Rs 180 each"))
        s.add(Message(conversation_id=old_id, role="assistant", content=[{"type": "text", "text": "Quotation ready."}],
                      display="Quotation ready."))
        for i in range(8):
            s.add(Message(conversation_id=conv, role="user", content=f"earlier ask {i} about the Lonavala order",
                          display=f"earlier ask {i} about the Lonavala order"))
            s.add(Message(conversation_id=conv, role="assistant", content=[{"type": "text", "text": "Noted."}],
                          display="Noted."))
        for i in range(6):
            s.add(TaskRun(tenant_id=T, request=f"Zarivala invoice batch {i} for the Pune distributors", outcome="done",
                          steps=4, conversation_id=conv))
        for i in range(30):   # a busy desk: far more job state than the note may carry
            s.add(kaamwatch.KaamJob(tenant_id=T, conversation_id=conv, key=f"x:{i}", kind="x", label="Job",
                                    title=f"Long running export number {i} " + "x" * 80, state="working",
                                    updated_at=now(), moved_at=now()))
    yaad.add_item(T, "exchange", "Sharma ji ka quotation: 40 Kesari boxes Rs 180 each", old_id)
    yaad.save_fact(T, "Her CA is Mr Bhandarkar in Amravati", "user")
    store.store_observation(conv, T, {"type": "discovery", "title": "Tally ledger Pulsewave for the Pune branch",
                                      "facts": [], "narrative": "Sales ledger is Sales GST 18%", "concepts": []})
    aboutme.set_text(T, "Meghana runs Newtika Pvt Ltd from Akola and sells solar pumps. " * 20)
    yield {"conv": conv, "old": old_id}
    get_settings.cache_clear()


def _run(conv, msgs, monkeypatch):
    from app.agent import santosh
    seen, mem = [], []
    real = santosh._chat_memory

    async def spy(*a, **k):
        out = await real(*a, **k)
        mem.append(out or "")
        return out

    async def fake_think(brain, system, history, settings, tools=None, live=None, max_tokens=None):
        seen.append({"system": system if isinstance(system, str) else "".join(b.get("text", "") for b in system),
                     "last": json.dumps(history[-1]["content"])})
        return ([{"type": "text", "text": "Done."}], "end_turn", brain)

    monkeypatch.setattr(santosh, "_chat_memory", spy)
    monkeypatch.setattr(santosh, "_think", fake_think)
    for m in msgs:
        asyncio.run(santosh.run_turn(conv, m))
    return seen, mem


def test_setting_defaults_on():
    from app.config import Settings
    assert Settings.model_fields["chat_one_memory"].default is True


def test_newest_message_memory_is_small(one, monkeypatch):
    seen, mem = _run(one["conv"], ["hi kaise ho", "pichhli baar Sharma ka quotation kya tha"], monkeypatch)
    assert mem and all(len(m) <= MEMORY_CAP for m in mem), [len(m) for m in mem]
    a, b = mem[0], mem[-1]
    assert "Long running export number" in a                       # job state still rides, capped
    assert "Her skills (" in a and len(a[a.index("Her skills ("):]) <= 600   # skill names only
    for gone in ("IS WAQT KA KAAM", "Work of the last 7 days", "CODER MEMORY", "ALL HER SKILLS",
                 "Older facts related", "earlier ask", "Zarivala", "Pulsewave"):
        assert gone not in a and gone not in b, gone
    assert "yaad_khojo" in b and "Kesari" not in b                 # a past pointer gets the hint, not the old chat
    sysx = seen[0]["system"]
    assert "Her memory page" in sysx and "Pinned by her" in sysx   # the one summary sits in the per-chat block


def test_yaad_khojo_finds_what_is_no_longer_injected(one):
    from app.agent import desk_tools
    from app.agent.tools import Ctx
    ctx = Ctx(tenant_id=T, conversation_id=one["conv"])

    def hits(q, **k):
        return asyncio.run(desk_tools.yaad_khojo(ctx, q, **k))["hits"]

    assert any(h["source"] == "fact" and "Bhandarkar" in h["text"] for h in hits("CA Bhandarkar"))
    chat = [h for h in hits("Sharma quotation Kesari boxes") if h["source"] == "chat"]
    assert chat and any("Kesari" in h["text"] for h in chat)
    assert any(h.get("chat_title") == "Sharma quotation" for h in chat)          # names the chat it came from
    assert any(h["source"] == "work" and "Pulsewave" in h["text"] for h in hits("Pulsewave ledger"))
    diary = hits("Zarivala invoice batch", source="diary")
    assert diary and diary[0]["source"] == "diary" and "Zarivala" in diary[0]["text"]


def test_switch_off_is_today(one, monkeypatch):
    monkeypatch.setenv("CHAT_ONE_MEMORY", "false")
    get_settings.cache_clear()
    _seen, mem = _run(one["conv"], ["hi kaise ho"], monkeypatch)
    m = mem[0]
    assert "IS WAQT KA KAAM" in m and "Work of the last 7 days" in m and "ALL HER SKILLS" in m
    assert len(m) > 5000


def test_voice_brain_turn_keeps_its_shape(one, monkeypatch):
    from app.agent import santosh
    assert santosh.one_memory_on(get_settings(), "owner") is True
    assert santosh.one_memory_on(get_settings(), "routine") is False
    tok = santosh.VOICE_BRAIN_NOW.set(True)
    try:
        assert santosh.one_memory_on(get_settings(), "owner") is False
    finally:
        santosh.VOICE_BRAIN_NOW.reset(tok)
    called = []

    async def fake_brain(*a, **k):
        called.append("brain")
        return ""

    async def boom(*a, **k):   # a call never goes through the chat memory path
        raise AssertionError("chat memory on a call")

    monkeypatch.setattr(santosh, "_brain_memory", fake_brain)
    monkeypatch.setattr(santosh, "_chat_memory", boom)

    async def fake_think(brain, system, history, settings, tools=None, live=None, max_tokens=None):
        return ([{"type": "text", "text": "Done."}], "end_turn", brain)

    monkeypatch.setattr(santosh, "_think", fake_think)

    async def go():
        t = santosh.VOICE_BRAIN_NOW.set(True)
        try:
            await santosh.run_turn(one["conv"], "ho gaya kya")
        finally:
            santosh.VOICE_BRAIN_NOW.reset(t)
    asyncio.run(go())
    assert called == ["brain"]


def test_skill_names_fit_their_budget(one):
    from app.coder import inject
    out = inject.skill_names(T, "excel ka macro likho")
    assert out.startswith("Her skills (") and len(out) <= inject.SKILL_NAMES_BUDGET
    assert "more)" in out                                           # the rest is one skill_manage list away
