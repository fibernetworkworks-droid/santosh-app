"""v0.886 her 13 Nov 14:48 chat turn died with 'Event loop is closed': the GLM door kept ONE httpx client for the whole
process, tied to whichever event loop used it first. A call made inside asyncio.run (a connector in a worker thread) left
it bound to a loop that then closed, and every later chat call on the main loop failed. Now one client per loop."""
import asyncio

from app.agent import llm


def test_a_client_from_a_closed_loop_is_never_reused():
    llm.set_http(None)
    first = asyncio.run(_get())                 # a short-lived loop (like a connector's asyncio.run)
    second = asyncio.run(_get())                # another loop: must get its own client
    assert first is not second

    async def twice():
        return llm._client(), llm._client()
    a, b = asyncio.run(twice())
    assert a is b                               # one client per loop, reused inside it


def test_set_http_still_wins():
    class Fake:
        is_closed = False
    f = Fake()
    llm.set_http(f)
    try:
        assert asyncio.run(_get()) is f
    finally:
        llm.set_http(None)


async def _get():
    return llm._client()


def test_research_calls_without_tools_never_get_every_tool(monkeypatch):
    """Her 13:58 log: 'glm call 50.8s msgs=1 tools=630 cap=600' - the research planner asks with no tools, the bridge
    turned [] into None and None means the whole registry (253k tokens, 51 s, one call)."""
    import types
    from app.agent import research_tools, santosh
    seen = {}

    async def fake_think(brain, system, history, settings, tools=None, live=None, max_tokens=None):
        seen["tools"] = tools
        return [{"type": "text", "text": "ok"}], "end_turn", brain
    monkeypatch.setattr(santosh, "_think", fake_think)
    ctx = types.SimpleNamespace(tenant_id="t", conversation_id="c", actor="owner")
    deps = research_tools._deps(ctx, types.SimpleNamespace())
    llm_call = deps["llm"] if isinstance(deps, dict) else getattr(deps, "llm")
    asyncio.run(llm_call("sys", [{"role": "user", "content": "plan"}], [], 600))
    assert seen["tools"] == []
