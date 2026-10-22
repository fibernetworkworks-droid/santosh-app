"""v0.104 "Browser work in PC is smooth, but suddenly Hoola launches its own browser in between": website work keeps its
place (her PC / Hoola's own browser) for the whole job, not only for short follow-ups of her words."""
import asyncio
import time
from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def _fresh():
    from app.agent import where
    where.forget()
    yield
    where.forget()


def test_work_on_her_pc_keeps_its_place_for_a_long_next_message():
    from app.agent import where
    assert where.remember("c1", "mere PC pe IRCTC kholo") == "pc"
    where.worked("c1", "pc_do", {"task": "Open irctc.co.in in Chrome and search trains Pune to Mumbai"})
    # her next message is long and names no place: before v0.102 this went back to "" (Hoola's own browser)
    long = "ab kal subah ki sabse sasti train dekh ke uska fare aur timing bata do please jaldi"
    assert where.remember("c1", long) == "pc"
    assert "HER PC" in where.note("pc", "c1") and "do NOT open your own browser" in where.note("pc", "c1")
    assert where.current("c1") == "pc"


def test_her_words_still_win_and_move_the_work():
    from app.agent import where
    where.worked("c2", "pc_do", {"task": "Open amazon.in in Chrome"})
    assert where.remember("c2", "ab apne browser mein flipkart check karo") == "hoola"
    assert where.working("c2") == ""                        # the PC place no longer holds
    where.worked("c2", "browse_web", {"task": "flipkart check"})
    assert where.working("c2") == "hoola"
    assert where.remember("c2", "aur uska rating bhi dekh ke batao kitne log ne review diya hai") == "hoola"


def test_work_place_ends_after_a_while_and_non_web_pc_work_does_not_stick():
    from app.agent import where
    where.worked("c3", "pc_do", {"task": "Tally mein aaj ki sale entry karo"})       # a desktop app, not a website
    assert where.working("c3") == ""
    where.worked("c3", "browse_web", {"task": "check PNR", "start_url": "irctc.co.in"})
    assert where.working("c3") == "hoola"
    where._WORK["c3"] = ("hoola", time.time() - where.WORK_KEEP_S - 1)
    assert where.working("c3") == ""
    assert where.remember("c3", "kuch aur bhi karna hai aaj shaam tak, list bana do mere liye") == ""


def test_dispatch_keeps_a_running_pc_job_on_her_pc(monkeypatch, env):
    """The model calls browse_web half way through a PC job: it must not open Hoola's own browser, and must not start a
    second PC job that would cancel the running one."""
    from app.agent import tools, where
    from app.pc import operator as pcop
    calls = []

    async def fake_browse(ctx, **kw):
        calls.append(("browse_web", kw))
        return {"status": "done"}

    async def fake_pc(ctx, **kw):
        calls.append(("pc_do", kw))
        return {"status": "running", "session_id": "pcop_x"}

    monkeypatch.setitem(tools.HANDLERS, "browse_web", fake_browse)
    monkeypatch.setitem(tools.HANDLERS, "pc_do", fake_pc)
    ctx = tools.Ctx(tenant_id="default", conversation_id="conv-pc")
    where.worked("conv-pc", "pc_do", {"task": "Open irctc.co.in in Chrome"})

    # a PC job is still running -> no new job, no own browser
    running = SimpleNamespace(id="pcop_live", tenant="default")
    monkeypatch.setattr(pcop, "running", lambda tenant: running)
    out = asyncio.run(tools.dispatch("browse_web", {"task": "check the fare", "start_url": "irctc.co.in"}, ctx))
    assert out["status"] == "pc_busy" and out["session_id"] == "pcop_live"
    assert calls == []

    # no PC job running -> the step runs on her PC (pc_do), never in Hoola's own browser
    monkeypatch.setattr(pcop, "running", lambda tenant: None)
    out = asyncio.run(tools.dispatch("browse_web", {"task": "check the fare", "start_url": "irctc.co.in"}, ctx))
    assert calls and calls[-1][0] == "pc_do" and "irctc.co.in" in calls[-1][1]["task"]
    assert out.get("ran_as") == "pc_do"
    assert all(c[0] != "browse_web" for c in calls)


def test_pc_failure_tells_the_model_to_ask_not_switch(monkeypatch, env):
    from app.agent import tools, where

    async def offline(ctx, **kw):
        raise tools.ToolError("Aapka PC offline hai.")

    monkeypatch.setitem(tools.HANDLERS, "pc_do", offline)
    where.worked("conv-off", "pc_do", {"task": "Open uidai.gov.in in Chrome"})
    ctx = tools.Ctx(tenant_id="default", conversation_id="conv-off")
    with pytest.raises(tools.ToolError) as e:
        asyncio.run(tools.dispatch("pc_do", {"task": "download aadhaar from uidai website"}, ctx))
    assert "Do NOT switch to your own browser" in str(e.value)


def test_hoola_browser_work_does_not_jump_to_her_pc(monkeypatch, env):
    from app.agent import tools, where
    where.worked("conv-h", "browse_web", {"task": "check PNR on irctc"})
    ctx = tools.Ctx(tenant_id="default", conversation_id="conv-h")
    with pytest.raises(tools.ToolError) as e:
        asyncio.run(tools.dispatch("pc_do", {"task": "open irctc.co.in website and check PNR"}, ctx))
    assert "YOUR OWN browser" in str(e.value)


def test_result_notes_refresh_the_place(monkeypatch):
    from app.agent import where
    where.touch("c9", "pc")
    where._WORK["c9"] = ("pc", time.time() - where.WORK_KEEP_S + 5)
    where.touch("c9", "pc")                     # a "(Result from HER PC ...)" note arrives
    assert where.working("c9") == "pc" and time.time() - where._WORK["c9"][1] < 2
