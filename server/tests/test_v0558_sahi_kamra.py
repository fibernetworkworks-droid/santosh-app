"""v0.558 SAHI KAMRA (built as 0.557) - the owner, after deploying v0.556: "IS NOW ALL TASK WILL FLOW PROPERLY TO DEFINED MODEL OR NEED
MORE WORK". The rest of the routes were measured with the same recording model; two needed work:
1. a BIG ask (several things to make) thinks at effort xhigh from its first call, but that call kept the chat-size
   2,000 tokens - thinking tokens count against it (the cut-answer bug v0.429 fixed for hard asks). It gets the
   long-job room (agent_goal_max_tokens) now;
2. HER scheduled routines sent the FULL registry (~570 tools, ~740 KB, ~184k tokens) on every call. They are
   admitted like a chat turn now (core families + her words + tool_search); every gate is unchanged."""
import asyncio

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import FakeBrain, _set_brain, gz, txt  # noqa: F401


def _run(monkeypatch, conv, ask, **kw):
    from app.agent.santosh import run_turn
    brain = _set_brain(monkeypatch, FakeBrain([([txt("Theek hai.")], "end_turn")] * 12))
    asyncio.run(run_turn(conv, ask, tenant_id="default", **kw))
    return brain.seen[0]


def test_a_big_ask_thinks_with_real_room_from_its_first_call(gz, monkeypatch):  # noqa: F811
    kw = _run(monkeypatch, gz["conv"], "Meri bakery ke liye ye sab banao: website, 30 din ka Instagram plan, "
                                       "price list PDF, aur WhatsApp offer message")
    assert kw["model"] == "claude-sonnet-5-5" and kw.get("thinking")
    assert (kw.get("extra_body") or {}).get("output_config", {}).get("effort") == "xhigh"
    assert kw["max_tokens"] >= 16000


def test_a_routine_carries_an_admitted_tool_set_not_the_whole_registry(gz, monkeypatch):  # noqa: F811
    from app.agent import tools
    kw = _run(monkeypatch, gz["conv"], "Subah ka briefing: aaj ke reminders aur mausam batao", actor="routine")
    names = {t["name"] for t in kw["tools"]}
    assert len(names) < 200 < len(tools.TOOLS), len(names)
    assert "tool_search" in names                                   # any other family is one call away
    assert kw["max_tokens"] == 2000 and not kw.get("thinking")


def test_simple_chat_and_wake_turns_are_unchanged(gz, monkeypatch):  # noqa: F811
    kw = _run(monkeypatch, gz["conv"], "namaste")
    assert kw["model"] == "claude-sonnet-5-5" and kw["max_tokens"] == 2000 and not kw.get("thinking")
    kw = _run(monkeypatch, gz["conv"], "[Santosh worker update, not the user] Ek background kaam ka natija abhi aaya hai",
              actor="wake", save_user=False)
    assert kw["max_tokens"] == 2000 and len(kw["tools"]) < 200
