"""v0.173 PC operator remembers her PC between tasks: the owner opened WhatsApp in Chrome, and when
she later said "send a message to this person on WhatsApp", Hoola forgot it was already open and
opened Edge instead. Now every finished PC task is remembered (YAAD) and the operator is told to
continue what is already open - never open a second copy or a second browser."""
import asyncio
import secrets
import time
import types

import pytest
from sqlalchemy import select

from tests.test_bazar import bz  # noqa: F401
from tests.test_pc_operator import FakeClaude, FakePC, JPEG, run, tu, txt


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
    from app.pc import memory
    from app.pc.service import flush_writes
    yield operator, pc, bz, memory, flush_writes


def _finish(op_mod, pc, bz, monkeypatch, script, task):
    claude = FakeClaude(script)
    import app.agent.santosh as s
    monkeypatch.setattr(s, "get_client", lambda: claude)

    async def go():
        r = await op_mod.start("default", bz["conv"], task, wait=30)
        o = op_mod.get("default", r["session_id"])
        await asyncio.wait_for(o.done_event.wait(), 10)
        return o, claude
    return run(go())


def _sys_text(system):
    """v0.200 helper: cache.system_prompt (v0.192) wraps the system prompt in blocks - read the text out.
    Written when system was a plain string; pre-existing failures were the str-vs-blocks trap."""
    if isinstance(system, str):
        return system
    return "\n".join(b.get("text", "") for b in (system or []) if isinstance(b, dict))


def test_finished_task_is_remembered_and_shown_to_the_next_run(op, monkeypatch):
    operator, pc, bz, memory, flush = op

    class WaPC(FakePC):
        """After WhatsApp Web opens the screen really shows it (the shared FakePC always says Excel)."""
        async def __call__(self, op, action, args=None, timeout=40):
            r = await super().__call__(op, action, args, timeout)
            if action == "screen" and any(a == "open_url" for a, _ in self.calls):
                r = {**r, "active_window": "WhatsApp - Google Chrome", "windows": ["WhatsApp - Google Chrome"]}
            return r

    wa = WaPC()
    monkeypatch.setattr(operator, "_pc", wa)
    # Task 1: WhatsApp kholo Chrome mein
    o, claude1 = _finish(operator, pc, bz, monkeypatch, [
        [txt("Chrome khol ke WhatsApp Web"), tu(1, "open_app", name="Chrome")],
        [tu(2, "open_url", url="https://web.whatsapp.com")],
        [tu(3, "done", answer="WhatsApp Chrome mein khul gaya.", success=True)],
    ], "WhatsApp kholo Chrome mein")
    assert o.status == "done"
    flush()
    entries = memory.recall("default")
    assert entries and entries[-1]["task"] == "WhatsApp kholo Chrome mein"
    assert any(a.startswith("open_app") for a in entries[-1]["did"])
    assert any("whatsapp.com" in a for a in entries[-1]["did"])
    assert "WhatsApp" in entries[-1]["window"]      # last active window recorded (WhatsApp - Chrome)

    # Task 2: msg bhejo - the model must SEE the memory in its system prompt
    o2, claude2 = _finish(operator, pc, bz, monkeypatch, [
        [tu(1, "done", answer="Message bhej diya.", success=True)],
    ], "Riya ko WhatsApp par message bhejo")
    systems = [_sys_text(kw["system"]) for kw in claude2.seen]
    yaad = next((s for s in systems if "your own recent finished work on THIS PC" in (s or "")), "")
    assert yaad and "WhatsApp kholo Chrome mein" in yaad and "web.whatsapp.com" in yaad
    open_urls = [a for act, a in pc.calls if act == "open_url"]
    assert not any("whatsapp" in str(u).lower() for u in open_urls[1:])   # never re-opened WhatsApp Web


def test_reuse_first_rules_are_always_in_the_prompt(op, monkeypatch):
    operator, pc, bz, memory, flush = op
    o, claude = _finish(operator, pc, bz, monkeypatch, [
        [tu(1, "done", answer="ho gaya", success=True)],
    ], "calculator kholo")
    system = _sys_text(claude.seen[0]["system"])
    assert "Remember what is already open" in system
    assert "Browser continuity" in system and "Edge" in system
    assert "focus_window" in system


def test_memory_block_empty_on_first_task(op, monkeypatch):
    operator, pc, bz, memory, flush = op
    o, claude = _finish(operator, pc, bz, monkeypatch, [
        [tu(1, "done", answer="ok", success=True)],
    ], "notepad kholo")
    assert "your own recent finished work on THIS PC" not in _sys_text(claude.seen[0]["system"])   # first ever task: no fake memories
    flush()
    assert memory.recall("default")


def test_old_entries_expire_and_cap_is_kept(op, monkeypatch):
    operator, pc, bz, memory, flush = op
    monkeypatch.setattr(memory.get_settings(), "pc_memory_runs", 3, raising=False)
    for i in range(5):
        memory.remember("default", f"task {i}", ["open_app Chrome"], "done", f"ho gaya {i}", "Chrome")
    flush()
    assert len(memory.recall("default")) == 3
    assert [e["task"] for e in memory.recall("default")] == ["task 2", "task 3", "task 4"]

    # TTL: an entry older than pc_memory_hours is invisible to the model
    monkeypatch.setattr(memory.get_settings(), "pc_memory_hours", 1, raising=False)
    old = {"t": int(time.time()) - 2 * 3600, "task": "purana kaam", "did": ["open_app Edge"],
           "status": "done", "answer": "", "window": "Edge"}
    memory.remember("default", "naya kaam", [], "done", "", "")
    flush()
    # write the old entry straight into the row (remember() always stamps t=now)
    from app.db import PcMemory, session as db_session
    with db_session() as s:
        row = s.scalars(select(PcMemory).where(PcMemory.tenant_id == "default")).first()
        row.entries = [old] + list(row.entries or [])
    rec = memory.recall("default")
    assert all(e["task"] != "purana kaam" for e in rec)
    assert "purana kaam" not in memory.prompt_block("default")


def test_removing_the_pc_forgets_its_memory(op, monkeypatch):
    operator, pc, bz, memory, flush = op
    memory.remember("default", "WhatsApp kholo", ["open_app Chrome"], "done", "khul gaya", "Chrome")
    flush()
    assert memory.recall("default")
    from app.db import PcDevice, session as db_session
    with db_session() as s:
        s.add(PcDevice(tenant_id="default", name="Office PC", token_hash="tok_" + secrets.token_hex(8)))
        s.flush()
        dev_id = s.scalars(select(PcDevice).where(PcDevice.tenant_id == "default")).first().id
    from app.pc import service
    assert service.revoke("default", dev_id)
    flush()
    assert memory.recall("default") == []


def test_cancelled_run_still_records_where_it_stopped(op, monkeypatch):
    operator, pc, bz, memory, flush = op

    class One(FakeClaude):
        async def create(self, **kw):
            await asyncio.sleep(0.02)
            return types.SimpleNamespace(content=[tu(len(self.seen) + 1, "wait", seconds=0.5)])
    import app.agent.santosh as s
    monkeypatch.setattr(s, "get_client", lambda: One([]))

    async def go():
        r = await operator.start("default", bz["conv"], "bada kaam chalu karo", wait=0.2)
        operator.stop("default", r["session_id"])
        o = operator.get("default", r["session_id"])
        await asyncio.wait_for(o.done_event.wait(), 5)
        return o
    o = run(go())
    flush()
    e = memory.recall("default")[-1]
    assert e["status"] == "cancelled" and e["task"] == "bada kaam chalu karo"
