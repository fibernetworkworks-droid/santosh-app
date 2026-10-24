"""v0.93 "Hoola is confusing between MERA PC browser and Hoola on browser": her words decide the place, in code."""
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


def _conv():
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id="default")
        s.add(c)
        s.flush()
        return c.id


def test_her_words_name_the_place():
    from app.agent.where import place
    cases = {
        "MERA PC BROWSER mein aadhaar download karo": "pc",
        "mere PC ke browser mein IRCTC kholo": "pc",
        "laptop pe chrome mein amazon kholo": "pc",
        "mere browser mein flipkart kholo": "pc",
        "मेरे पीसी पर आधार डाउनलोड करो": "pc",
        "user ke PC par Chrome mein UIDAI kholo": "pc",          # Gemini's words when it hands a job over
        "Hoola on browser mein check karo": "hoola",
        "apne browser mein PNR check karo": "hoola",
        "tumhare browser se karo": "hoola",
        "server pe hi try karo": "hoola",
        "अपने ब्राउज़र में खोलो": "hoola",
        "PC pe nahi, apne browser mein karo": "hoola",           # a place she says NO to doesn't count
        "apne browser mein nahi, mere PC pe karo": "pc",
        "phone pe kholo irctc": "phone",
        "IRCTC pe PNR check karo": "",                            # no place: Hoola picks (own browser by default)
        "computer operator se form bharo": "",                    # a feature name, not her computer
        "OTP phone pe aayega": "",
    }
    for text, want in cases.items():
        assert place(text) == want, text


def test_a_named_place_holds_for_short_follow_ups_only():
    from app.agent import where
    assert where.remember("c1", "mere PC pe IRCTC kholo") == "pc"
    assert where.remember("c1", "kal ki date") == "pc"                 # her short answer: same place
    assert where.remember("c1", "IRCTC pe Pune se Mumbai ki kal ki trains dekh ke batao sabse sasti") == ""   # new request
    assert where.remember("c1", "haan") == ""
    assert where.remember("c2", "apne browser mein karo") == "hoola"
    where._PLACE["c2"] = ("hoola", time.time() - where.KEEP_S - 1)
    assert where.remember("c2", "haan karo") == ""                     # 15 minutes later it's gone


def _record(monkeypatch, *names):
    from app.agent import tools
    calls = []
    for n in names:
        async def h(ctx, _n=n, **a):
            calls.append((_n, a))
            return {"status": "running", "session_id": "pcop_1" if _n == "pc_do" else "s1"}
        monkeypatch.setitem(tools.HANDLERS, n, h)
    return calls


def test_her_pc_wins_over_hoolas_browser(env, monkeypatch):
    from app.agent.tools import Ctx, dispatch
    calls = _record(monkeypatch, "pc_do", "browse_web", "open_on_phone")
    ctx = Ctx(tenant_id="default", conversation_id="c", place="pc")
    out = asyncio.run(dispatch("browse_web", {"task": "IRCTC par PNR 4512 check karo", "start_url": "irctc.co.in"}, ctx))
    assert calls[0][0] == "pc_do" and "Chrome on this PC" in calls[0][1]["task"]
    assert "https://irctc.co.in" in calls[0][1]["task"] and out["ran_as"] == "pc_do" and "HER PC" in out["place_note"]
    asyncio.run(dispatch("open_on_phone", {"url": "flipkart.com"}, ctx))
    assert calls[1][0] == "pc_do" and "https://flipkart.com" in calls[1][1]["task"]
    assert [c[0] for c in calls] == ["pc_do", "pc_do"]                 # Hoola's browser / phone never used


def test_hoolas_browser_is_never_her_pc(env, monkeypatch):
    from app.agent.tools import Ctx, ToolError, dispatch
    calls = _record(monkeypatch, "pc_do")
    ctx = Ctx(tenant_id="default", conversation_id="c", place="hoola")
    with pytest.raises(ToolError, match="YOUR OWN browser"):
        asyncio.run(dispatch("pc_do", {"task": "Chrome mein irctc.co.in kholo"}, ctx))
    asyncio.run(dispatch("pc_do", {"task": "Excel mein sales sheet kholo"}, ctx))   # not a website: allowed
    assert [c[0] for c in calls] == ["pc_do"]


def test_operator_asks_before_moving_her_browser_job_to_her_pc(env, monkeypatch):
    from app.agent import operator_tools
    from app.agent.tools import Ctx, dispatch
    from app.config import get_settings
    from app.operator import reach
    from app.operator import service as ops
    monkeypatch.setenv("OPERATOR_PREFLIGHT", "true")
    get_settings.cache_clear()
    reach.note_fail("myaadhaar.uidai.gov.in", "timed out")
    started, pc_tasks = [], []
    monkeypatch.setattr(ops, "start", lambda *a, **k: started.append(a) or {"id": "x", "status": "queued"})

    async def fake_pc_do(ctx, task, _wait=None, **_):
        pc_tasks.append(task)
        return {"session_id": "pcop_1", "status": "running"}
    import app.agent.pc_tools as pc_tools
    monkeypatch.setattr(pc_tools, "pc_do", fake_pc_do)
    conv = _conv()
    # she said "apne browser mein": UIDAI refuses the server -> she is ASKED, nothing moves to her PC by itself
    ctx = Ctx(tenant_id="default", conversation_id=conv, place="hoola")
    r = asyncio.run(dispatch("computer_operator", {"action": "start", "task": "Aadhaar download karo"}, ctx))
    assert r["status"] == "site_blocks_server" and r["say"].endswith("kar doon?") and not pc_tasks and not started
    # she said "mere PC pe": straight to her PC, and the words say it was HER choice (not "the site refuses")
    ctx = Ctx(tenant_id="default", conversation_id=conv, place="pc")
    r = asyncio.run(dispatch("computer_operator", {"action": "start", "task": "IRCTC se ticket ka PDF download karo"}, ctx))
    assert r["place"] == "pc" and "moved_to" not in r and r["say"].startswith("Aapke PC par") and len(pc_tasks) == 1
    # no place named + a site that works: Hoola's own browser, and it says so
    ctx = Ctx(tenant_id="default", conversation_id=conv)
    monkeypatch.setattr(reach, "probe", lambda host, **k: (True, ""))
    r = asyncio.run(operator_tools.computer_operator(ctx, "start", task="MSEDCL bill download karo"))
    assert started and r["place"] == "hoola" and "aapke PC par nahi" in r["say"]
    get_settings.cache_clear()


def test_her_pc_offline_is_said_as_her_pc(env, monkeypatch):
    from app.agent import operator_tools
    from app.agent.tools import Ctx, ToolError

    async def offline(ctx, task, _wait=None, **_):
        raise ToolError("Aapka PC offline hai.")
    import app.agent.pc_tools as pc_tools
    monkeypatch.setattr(pc_tools, "pc_do", offline)
    r = asyncio.run(operator_tools.computer_operator(Ctx(tenant_id="default", conversation_id="c"), "start",
                                                     task="form bharo", where="pc"))
    assert r["status"] == "pc_not_ready" and "Aapka PC" in r["say"] and "server" not in r["say"]


def test_chat_turn_carries_the_place_to_the_model_and_the_tools(env, monkeypatch):
    from app.agent import santosh, tools
    conv = _conv()
    seen, ran = {}, []

    async def think(brain, system, history, settings, tools=None):
        if "hist" not in seen:
            seen["hist"] = str(history[-1])
            return [{"type": "tool_use", "id": "t1", "name": "browse_web",
                     "input": {"task": "UIDAI se Aadhaar download karo"}}], "tool_use", brain
        return [{"type": "text", "text": "Aapke PC par Chrome mein shuru kar diya."}], "end_turn", brain

    async def pc(ctx, **a):
        ran.append(("pc_do", a))
        return {"status": "running", "session_id": "pcop_9"}

    async def web(ctx, **a):
        ran.append(("browse_web", a))
        return {"status": "running"}
    monkeypatch.setattr(santosh, "_think", think)
    monkeypatch.setattr(santosh.llm, "choose", lambda h: "claude")
    monkeypatch.setitem(tools.HANDLERS, "pc_do", pc)
    monkeypatch.setitem(tools.HANDLERS, "browse_web", web)
    asyncio.run(santosh.run_turn(conv, "MERA PC BROWSER mein Aadhaar download karo"))
    assert "HER PC" in seen["hist"] and [r[0] for r in ran] == ["pc_do"]


def test_call_reads_the_place_from_her_spoken_words():
    from app import voice
    from app.agent import where
    call = SimpleNamespace(conv="call1", user_buf="mere laptop pe chrome mein irctc kholo")
    assert voice.Call._place(call, "") == "pc"
    call.user_buf = "kal ki"                                         # next turn, short answer
    assert voice.Call._place(call, "") == "pc"
    call.user_buf = ""
    assert voice.Call._place(call, "apne browser mein PNR dekho") == "pc"     # what she said wins over Gemini's words
    where.forget("call1")
    assert voice.Call._place(call, "apne browser mein PNR dekho") == "hoola"


def test_names_are_never_mixed_in_what_hoola_reads():
    from app.agent import tools
    descs = {t["name"]: t["description"] for t in tools.TOOLS}
    assert "[Mera PC]" not in " ".join(descs.values())
    assert "HER PC" in descs["pc_do"] and "NOT her PC" in descs["browse_web"] and "NOT her PC" in descs["computer_operator"]
    assert tools.TOOL_LABELS["pc_do"].startswith("Aapke PC") and tools.TOOL_LABELS["browse_web"].startswith("Apne browser")
    from app.agent.prompts import SYSTEM
    assert "teen jagah" in SYSTEM and "aapka PC" in SYSTEM


def test_the_card_names_where_it_really_runs():
    from app import livework
    from app.agent import where
    assert where.shown("browse_web", {"task": "irctc kholo"}, "pc") == "pc_do"
    assert where.shown("pc_do", {"task": "Chrome mein irctc.co.in kholo"}, "hoola") == "pc_do"   # refused later, no raise here
    assert where.shown("browse_web", {"task": "x"}, "") == "browse_web"
    assert livework.scene_for("computer_operator") == "browser" and livework.scene_for("pc_do") == "pc"
