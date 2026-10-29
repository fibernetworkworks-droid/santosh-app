"""v0.189.0 "HARNESS-1" - the three latency killers + the monitoring hole, from the dsh / Claude Code study:

1. tool-result pruner (agent/prune.py): old steps' tool results leave the request (head + marker + tail), the
   newest step stays whole, her words and the memory blocks are never touched, pure projection (the stored
   history is untouched), idempotent. The dsh harness prunes exactly like this before compaction pressure.
2. parallel read-only look-ups (santosh.PARALLEL_SAFE + agent_parallel_tools): a step that asks for several
   pure look-ups runs them TOGETHER; results still commit in the model's order; anything not clearly safe
   (writes, her PC's one WebSocket, mail/Drive reads) stays strictly serial, byte-for-byte the old path.
3. prompt cache covers the system prompt too (cache.system_prompt, the 3rd of Anthropic's 4 breakpoints).
4. a STOPPED background job reports in Hoola's own words like done/failed always did (v0.187's coverage hole).
"""
import asyncio
import time
import types

import pytest
from sqlalchemy import select

import app.kaam_followup as kf
import app.kaamwatch as kw

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0187_realtime import fu, tick_drain  # noqa: F401


def tu(i, tool, **inp):
    return {"type": "tool_use", "id": f"t{i}", "name": tool, "input": inp}


def txt(t):
    return {"type": "text", "text": t}


class FakeBrain:
    """Scripted Claude: each create() pops the next response; stop_reason rides with it."""

    def __init__(self, script):
        self.script = list(script)
        self.seen = []
        self.messages = self

    async def create(self, **kw):
        self.seen.append(kw)
        blocks, stop = self.script.pop(0)
        return types.SimpleNamespace(content=blocks, stop_reason=stop)


# ---------------- 1. the tool-result pruner ----------------

def test_prune_caps_old_results_keeps_newest_whole():
    from app.agent.prune import MARK, prune_history
    big = "x" * 12000
    history = [
        {"role": "user", "content": "report nikalo"},
        {"role": "assistant", "content": [tu(1, "open_website")]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": big}]},
        {"role": "assistant", "content": [txt("padh liya")]},
        {"role": "user", "content": "aage badho"},
        {"role": "assistant", "content": [tu(2, "open_website")]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t2", "content": big}]},
    ]
    out = prune_history(history)
    old, new = out[2]["content"][0]["content"], out[6]["content"][0]["content"]
    assert len(old) < 4000 and MARK in old                    # old step: head + marker + tail
    assert old.startswith("x" * 100) and old.endswith("x" * 100)
    assert new == big                                          # the newest step stays WHOLE
    assert out[0]["content"] == "report nikalo" and out[4]["content"] == "aage badho"   # her words untouched
    assert history[2]["content"][0]["content"] == big          # pure projection: the input list is untouched
    again = prune_history(out)
    assert again[2]["content"][0]["content"] == old            # idempotent


def test_prune_leaves_small_results_her_words_and_memory_blocks_alone():
    from app.agent import prune
    from app.agent.prune import prune_history
    prune.STATS["trimmed"] = 0
    small = {"type": "tool_result", "tool_use_id": "t1", "content": "12 mails mile"}
    memory_block = [{"type": "text", "text": "YAAD: uski favourite sweets kaju katli hai."},
                    {"type": "text", "text": "ab batao"}]
    history = [
        {"role": "user", "content": "mailbox dekho"},
        {"role": "assistant", "content": [tu(1, "email_list")]},
        {"role": "user", "content": [small]},
        {"role": "assistant", "content": [txt("12 mails")]},
        {"role": "user", "content": memory_block},              # v0.187 memory rides as text blocks: never touched
    ]
    out = prune_history(history)
    assert out == history
    assert prune.STATS["trimmed"] == 0


# ---------------- 2. parallel read-only look-ups ----------------

class _Barrier:
    def __init__(self):
        self.count = 0
        self.evt = asyncio.Event()


def _set_brain(monkeypatch, brain):
    import app.agent.santosh as s
    monkeypatch.setattr(s, "get_client", lambda: brain)
    return brain


def test_parallel_step_runs_lookups_together_and_commits_in_model_order(bz, monkeypatch):  # noqa: F811
    """Three pure look-ups in ONE step: all three run together (the barrier only opens when all three are in
    flight), yet the brain sees the results in ITS order (t1, t2, t3)."""
    conv = bz["conv"]
    brain = _set_brain(monkeypatch, FakeBrain([
        ([txt("teen lookups"), tu(1, "google_search", q="a"), tu(2, "get_weather", city="Pune"),
          tu(3, "kaam_status")], "tool_use"),
        ([txt("ho gaya, teeno ke jawaab upar hain.")], "end_turn"),
    ]))
    from app import chats
    monkeypatch.setattr(chats, "enabled", lambda: False)
    import app.agent.santosh as s
    bar = _Barrier()
    seen = []

    async def fake_run_tool(name, args, ctx, settings, mcp_route=None):
        seen.append(name)
        bar.count += 1
        if bar.count >= 3:
            bar.evt.set()                    # opens only if all three really run together
        await asyncio.wait_for(bar.evt.wait(), timeout=2.0)
        return {"ok": True, "data": name}

    monkeypatch.setattr(s, "_run_tool", fake_run_tool)
    t0 = time.monotonic()
    out = asyncio.run(s.run_turn(conv, "teen cheezein dekho", tenant_id="default"))
    took = time.monotonic() - t0
    assert "ho gaya" in out
    assert bar.count == 3 and bar.evt.is_set()          # they truly overlapped (serial never opens the barrier)
    assert len(seen) == 3
    last = brain.seen[-1]["messages"][-1]["content"]
    ids = [b["tool_use_id"] for b in last if b.get("type") == "tool_result"]
    assert ids == ["t1", "t2", "t3"]                    # model order, not completion order
    assert took < 5.0                                   # parallel: well under 3 x the 2 s barrier timeout


def test_serial_path_kept_for_anything_not_clearly_safe(bz, monkeypatch):  # noqa: F811
    """A mixed step (a PC tool + anything else) runs EXACTLY like before: one after another, in order."""
    conv = bz["conv"]
    brain = _set_brain(monkeypatch, FakeBrain([
        ([tu(1, "pc_screenshot"), tu(2, "send_whatsapp", to="x", text="hi")], "tool_use"),
        ([txt("dono ho gaye.")], "end_turn"),
    ]))
    from app import chats
    monkeypatch.setattr(chats, "enabled", lambda: False)
    import app.agent.santosh as s
    seen, ended = [], []

    async def fake_run_tool(name, args, ctx, settings, mcp_route=None):
        seen.append(name)
        await asyncio.sleep(0.05)
        ended.append(name)
        return {"ok": True, "data": name}

    monkeypatch.setattr(s, "_run_tool", fake_run_tool)
    out = asyncio.run(s.run_turn(conv, "PC aur whatsapp", tenant_id="default"))
    assert "dono ho gaye" in out
    assert seen == ["pc_screenshot", "send_whatsapp"] and ended == ["pc_screenshot", "send_whatsapp"]
    assert brain.seen[-1]["messages"][-1]["content"][0]["tool_use_id"] == "t1"


# ---------------- 3. the cache covers the system prompt ----------------

def test_cache_covers_the_system_prompt_too():
    from app.agent.cache import shape
    kw = {"model": "m", "max_tokens": 10, "system": "TUM HOOLA HO. Rules yahan hain.",
          "tools": [{"name": "a"}, {"name": "b"}],
          "messages": [{"role": "user", "content": "hi"}]}
    shaped = shape(kw, True)
    assert shaped["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert shaped["system"][0]["text"] == "TUM HOOLA HO. Rules yahan hain."     # byte-identical words
    assert shaped["tools"][-1]["cache_control"] == {"type": "ephemeral"}
    assert shaped["messages"][-1]["content"][0]["cache_control"] == {"type": "ephemeral"}
    assert shape(kw, False) == kw                                              # off: untouched
    assert kw["system"] == "TUM HOOLA HO. Rules yahan hain."                   # the input was never mutated


# ---------------- 4. a stopped job reports too ----------------

def test_stopped_job_reports_in_her_voice(fu, monkeypatch):  # noqa: F811
    conv = fu["conv"]
    from app.config import get_settings as _gs
    monkeypatch.setattr(_gs(), "agent_wake_turns", False)   # v0.191: pins the one-shot FALLBACK path (auto-restored)

    async def fake_line(r, settings):
        return "Long reel ka kaam band kar diya gaya hai."

    monkeypatch.setattr(kf, "_model_line", fake_line)
    kw.observe(conv, "video_job", {"id": "vS", "status": "stopped", "name": "Long reel"})
    tick_drain()
    assert fu["notices"] and "band kar diya gaya" in fu["notices"][0][1]
    from app.db import Message, session
    with session() as sdb:   # the dry line did NOT go out as a message (the report replaced it)
        msgs = sdb.scalars(select(Message).where(Message.conversation_id == conv)).all()
    assert not [m for m in msgs if "⏹" in (m.display or "")]


def test_stopped_enqueue_gate_and_canned_line():
    from app.kaam_followup import _canned, enqueue
    job = {"key": "video_job:vQ", "kind": "video_job", "label": "Video edit", "title": "Roka hua kaam",
           "state": "stopped", "detail": "", "link": "", "pct": -1, "stage": "", "waiting_say": "", "push": False}
    assert enqueue("default", "conv_gate", job) is True            # stopped passes the gate now
    assert enqueue("default", "conv_gate", job) is False             # deduped per key + state
    waiting = dict(job, state="waiting")
    assert enqueue("default", "conv_gate", waiting) is False         # waiting still never reports (her baari = card)
    row = types.SimpleNamespace(label="Video edit", title="Roka hua kaam", state="stopped", detail="", link="")
    assert "band kar diya gaya" in _canned(row) and "bol dena" in _canned(row)


# ---------------- version ----------------

def test_version():
    from app.config import get_settings
    from app.main import APP_VERSION
    assert APP_VERSION == "0.223.0"
    assert get_settings().agent_parallel_tools is True
    assert get_settings().agent_ack_after_s == 5.0
