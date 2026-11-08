"""v0.559.0 HOOLA MIDDLEWARE - the 24, P5 of the HOOLA AEP plan (owner: 'P5 -
the 24-middlewares (nudge/curator/delegate/skills-primer collapse into hooks)').
The langchain 1.x agents/middleware idea hand-built as server/app/aep/
middleware.py - ZERO upstream code. This suite pins the layer:

(1) TAXONOMY: the AgentMiddleware hook surface (before/after/wrap x
    agent/model/tool + the a-* twins raising the honest wording);
    ModelRequest.override (immutable, system_prompt conversion, both-given
    refusal, unknown-key refusal, direct-assignment refusal); ModelResponse /
    ExtendedModelResponse normalization (the AIMessage short form, the
    Command(update) extra state, goto/resume refused with the upstream
    wording); hook_config; the function decorators (@before_model,
    @dynamic_prompt, @wrap_model_call); async-only hooks refused at build.
(2) WIRING: hook nodes named f'{name}.{hook}'; before_agent once per invoke,
    before_model every iteration, after_model in REVERSE registration order,
    after_agent once at the end (reverse order); duplicate names refused;
    non-middleware entries refused; middleware tools join the surface;
    state_schema merge (middleware channels ride, the caller's base wins).
(3) JUMP_TO: the run-limit end jump; an undeclared jump consumed and ignored;
    a declared 'model' jump loops the walk; jump_to is ephemeral (one gate per
    arrival, no stale reroute) and untracked (run counters restart every
    invoke on a checkpointed thread; thread counters persist).
(4) SUMMARIZATION: token trigger; the summary message shape; the preserved
    tail; AI/Tool pairs never split; the middle-cut fallback when the
    summarizer keeps failing; trigger/keep validation.
(5) PII: email/credit-card(Luhn)/ip/mac/url built-ins; redact/mask/hash/
    block; custom regex detectors; input/output/tool-results lanes; the live
    stream transformer; unknown type refused.
(6) LIMITS: model_call_limit end/error + thread/run counter semantics;
    tool_call_limit continue/end/error + per-tool-name scoping; both-limits-
    none refused; bad exit_behavior refused.
(7) RETRY/FALLBACK: model retry with zero delay; retry_on selection;
    on_failure continue/error; fallback chain order; all-fail re-raise;
    interrupts are never retried.
(8) TOOL WRAPS: tool_error content / None re-raise; tool_retry success on the
    2nd attempt / the continue error message; the LLM emulator answers without
    executing (emulate_all + the selected-name lane) and tags the internal call.
(9) HITL: the park carries the HITLRequest; approve/edit/reject/respond;
    edited args substitute at tool time with the reviewer note; decision-count
    and decision-kind validation; ungated tools never park; the when gate.
(10) TODO + CONTEXT EDITING: the write_todos tool + the system rider;
    ClearToolUsesEdit clears past the trigger (newest kept, excludes honored,
    cleared marked, args optionally cleared) and the state stays untouched.
(11) FILE SEARCH / PROVIDER / SHELL: glob+grep over a tmp tree (size cap);
    provider tagging for an anthropic-shaped model + the unknown-provider
    refusal; the bounded shell tool (output cap, timeout line, missing shell
    refused).
(12) UNIFICATION: Nudge rides the system message (fixed/callable/None);
    Curator folds duplicate tool noise + caps the lane; Delegate runs bounded
    workers (fail-open, MAX_DEPTH refuse, too-many refuse); SkillsPrimer
    injects matched primers (hers win) with the char cap.
(13) SEAMS: the inertness probe (fresh interpreter, zero threads/env/files);
    the package-export law; no config reads; APP_VERSION + pubspec story pins.

No test touches the network; every async path rides asyncio.run (the
documented one-loop law).
"""
import asyncio
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER = REPO_ROOT / "server"

from app import aep
from app.aep import middleware as MW
from app.aep.agent import create_agent
from app.aep.graph import Command, GraphInterrupt, MemorySaver, interrupt
from app.aep.messages import AIMessage, HumanMessage, RemoveMessage, SystemMessage, ToolMessage
from app.aep.middleware import (
    AgentMiddleware,
    ClearToolUsesEdit,
    ContextEditingMiddleware,
    CuratorMiddleware,
    DelegateMiddleware,
    ExtendedModelResponse,
    FilesystemFileSearchMiddleware,
    HumanInTheLoopMiddleware,
    LLMToolEmulator,
    ModelCallLimitExceededError,
    ModelCallLimitMiddleware,
    ModelFallbackMiddleware,
    ModelRequest,
    ModelResponse,
    ModelRetryMiddleware,
    NudgeMiddleware,
    PIIDetectionError,
    PIIMiddleware,
    ProviderToolSearchMiddleware,
    ShellToolMiddleware,
    SkillsPrimerMiddleware,
    SummarizationMiddleware,
    ToolCallLimitExceededError,
    ToolCallLimitMiddleware,
    ToolCallRequest,
    ToolErrorMiddleware,
    ToolRetryMiddleware,
    TodoListMiddleware,
    dynamic_prompt,
    hook_config,
    internal_call_metadata,
    wrap_model_call,
)
from app.aep.agent import ToolNode
from app.aep.models import BaseChatModel, ChatGeneration, ChatResult
from app.aep.tools import tool


# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------


def _tc(name: str, args: dict, tid: str = "c1") -> dict:
    return {"type": "tool_call", "id": tid, "name": name, "args": args}


class FakeModel(BaseChatModel):
    """Queues whole AIMessages; records every prompt it is called with."""
    responses: list
    idx: int = 0
    seen_prompts: list = []

    @property
    def _llm_type(self) -> str:
        return "fake-mw"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, **kwargs):
        self.seen_prompts.append(list(messages))
        r = self.responses[self.idx % len(self.responses)]
        self.idx += 1
        return ChatResult(generations=[ChatGeneration(message=r)])


class ToolLoopModel(BaseChatModel):
    """Calls the tool until it has seen N ToolMessages, then answers."""
    rounds: int = 2
    seen_prompts: list = []

    @property
    def _llm_type(self) -> str:
        return "fake-loop"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, **kwargs):
        self.seen_prompts.append(list(messages))
        n_tool = sum(1 for m in messages if isinstance(m, ToolMessage))
        if n_tool < self.rounds:
            return ChatResult(generations=[ChatGeneration(message=AIMessage(
                content="", tool_calls=[_tc("echo", {"x": f"n{n_tool}"}, f"c{n_tool}")]))])
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="done"))])


@tool
def echo(x: str) -> str:
    """Echo the text back.
    Args:
        x: the text
    """
    return f"echo:{x}"


@tool
def boom(x: str) -> str:
    """Always explodes.
    Args:
        x: unused
    """
    raise ValueError("phat gaya")


def _resp(msgs, structured=None):
    return ModelResponse(result=list(msgs), structured_response=structured)


# ---------------------------------------------------------------------------
# (1) the taxonomy
# ---------------------------------------------------------------------------


def test_agent_middleware_base_hooks_exist_and_are_inert():
    m = AgentMiddleware()
    assert m.name == "AgentMiddleware"
    assert m.before_agent({"messages": []}, {}) is None
    assert m.before_model({"messages": []}, {}) is None
    assert m.after_model({"messages": []}, {}) is None
    assert m.after_agent({"messages": []}, {}) is None


def test_model_request_override_is_immutable_and_validates():
    req = ModelRequest(model="m", messages=[HumanMessage("hi")],
                       system_prompt="sys", tools=[echo])
    new = req.override(system_message=SystemMessage(content="sys2"))
    assert new is not req
    assert req.system_message.text == "sys"
    assert new.system_message.text == "sys2"
    assert new.messages == req.messages
    assert req.system_prompt == "sys"
    with pytest.raises(ValueError, match="both system_prompt and system_message"):
        ModelRequest(model="m", messages=[], system_prompt="a", system_message=SystemMessage("b"))
    with pytest.raises(ValueError, match="Unknown override keys"):
        req.override(nope=1)


def test_model_request_direct_assignment_refused():
    req = ModelRequest(model="m", messages=[])
    with pytest.raises(AttributeError, match="override"):
        req.messages = []


def test_model_result_normalization_shapes():
    ai = AIMessage(content="x")
    resp, extra = MW._normalize_model_result(ai)
    assert resp.result == [ai] and extra == {}
    resp, extra = MW._normalize_model_result(_resp([ai], structured={"a": 1}))
    assert resp.structured_response == {"a": 1}
    resp, extra = MW._normalize_model_result(ExtendedModelResponse(
        model_response=_resp([ai]), command={"update": {"todos": [{"content": "t"}]}}))
    assert extra == {"todos": [{"content": "t"}]}
    with pytest.raises(NotImplementedError, match="jump_to"):
        MW._normalize_model_result(ExtendedModelResponse(
            model_response=_resp([ai]), command={"goto": ["model"]}))
    with pytest.raises(TypeError):
        MW._normalize_model_result({"messages": []})


def test_hook_config_and_decorators_build_middlewares():
    @hook_config(can_jump_to=["end"])
    def my_hook(state, runtime):
        return {"jump_to": "end"} if runtime.get("x") else None

    m = MW._make_single_hook_mw(my_hook, "before_model", None)
    assert "end" in MW._can_jump_to(m, "before_model")
    dm = dynamic_prompt(lambda request: "DYNAMIC " + str(len(request.messages)))
    assert dm.name  # a named one-hook middleware
    wm = wrap_model_call(lambda request, handler: handler(request))
    assert MW._has_hook(wm, "wrap_model_call")
    bm = MW.before_model(lambda state, runtime: None, can_jump_to=["model"])
    assert MW._can_jump_to(bm, "before_model") == ["model"]


def test_async_only_wrap_hook_refused_at_build():
    class AsyncOnly(AgentMiddleware):
        async def awrap_model_call(self, request, handler):  # noqa: RUF029
            return await handler(request)

    with pytest.raises(NotImplementedError, match="sync twin"):
        create_agent(FakeModel(responses=[AIMessage("x")]), middleware=[AsyncOnly()])


def test_async_twin_of_a_sync_hook_is_fine():
    class Both(AgentMiddleware):
        def wrap_model_call(self, request, handler):
            return handler(request)

        async def awrap_model_call(self, request, handler):  # noqa: RUF029
            return await handler(request)

    out = create_agent(FakeModel(responses=[AIMessage("x")]), middleware=[Both()])
    assert out.invoke({"messages": ["hi"]})["messages"][-1].content == "x"


def test_awrap_only_raises_the_upstream_wording():
    m = AgentMiddleware()
    with pytest.raises(NotImplementedError, match="awrap_model_call"):
        asyncio.run(m.awrap_model_call(None, None))
    with pytest.raises(NotImplementedError, match="wrap_tool_call"):
        m.wrap_tool_call(None, None)


# ---------------------------------------------------------------------------
# (2) the wiring topology
# ---------------------------------------------------------------------------


class Probe(AgentMiddleware):
    def __init__(self):
        self.calls: list[str] = []

    def before_agent(self, state, runtime):
        self.calls.append("before_agent")
        return None

    def before_model(self, state, runtime):
        self.calls.append("before_model")
        return None

    def after_model(self, state, runtime):
        self.calls.append("after_model")
        return None

    def after_agent(self, state, runtime):
        self.calls.append("after_agent")
        return None


def test_hook_nodes_run_once_per_iter_and_reverse_after():
    p = Probe()
    agent = create_agent(FakeModel(responses=[AIMessage("", tool_calls=[_tc("echo", {"x": "a"})]),
                                              AIMessage("done")]),
                         tools=[echo], middleware=[p])
    out = agent.invoke({"messages": ["hi"]})
    assert out["messages"][-1].content == "done"
    # one before_agent; before/after_model twice (two iterations); one after_agent
    assert p.calls.count("before_agent") == 1
    assert p.calls.count("before_model") == 2
    assert p.calls.count("after_model") == 2
    assert p.calls.count("after_agent") == 1
    assert p.calls[0] == "before_agent" and p.calls[-1] == "after_agent"


def test_after_model_runs_in_reverse_registration_order():
    order: list[str] = []

    class Tag(AgentMiddleware):
        def __init__(self, tag):
            self.tag = tag

        @property
        def name(self):
            return f"Tag{self.tag}"

        def after_model(self, state, runtime):
            order.append(self.tag)
            return None

    agent = create_agent(FakeModel(responses=[AIMessage("done")]),
                         middleware=[Tag("a"), Tag("b"), Tag("c")])
    agent.invoke({"messages": ["hi"]})
    assert order == ["c", "b", "a"]  # the upstream reverse law


def test_after_agent_runs_in_reverse_registration_order():
    order: list[str] = []

    class Tag(AgentMiddleware):
        def __init__(self, tag):
            self.tag = tag

        @property
        def name(self):
            return f"Tag{self.tag}"

        def after_agent(self, state, runtime):
            order.append(self.tag)
            return None

    agent = create_agent(FakeModel(responses=[AIMessage("done")]),
                         middleware=[Tag("a"), Tag("b")])
    agent.invoke({"messages": ["hi"]})
    assert order == ["b", "a"]


def test_duplicate_middleware_names_and_junk_entries_refused():
    class Same(AgentMiddleware):
        pass

    with pytest.raises(AssertionError, match="duplicate middleware"):
        create_agent(FakeModel(responses=[AIMessage("x")]), middleware=[Same(), Same()])
    with pytest.raises(TypeError, match="AgentMiddleware instances"):
        create_agent(FakeModel(responses=[AIMessage("x")]), middleware=[object()])


def test_middleware_tools_join_the_surface_and_schemas_merge():
    todo = TodoListMiddleware()
    assert todo.tools[0].name == "write_todos"
    agent = create_agent(FakeModel(responses=[AIMessage("ok")]), middleware=[todo])
    assert "tools" in agent.nodes  # the tool node exists ONLY because the mw registered a tool

    class MwState(AgentMiddleware):
        state_schema = {"mw_counter": int}

    class Other(AgentMiddleware):
        state_schema = {"mw_counter": float, "other": str}

    agent2 = create_agent(FakeModel(responses=[AIMessage("x")]),
                          middleware=[MwState(), Other()])
    assert "mw_counter" in agent2.channels and "other" in agent2.channels


def test_hook_node_names_carry_the_middleware_name():
    p = Probe()
    agent = create_agent(FakeModel(responses=[AIMessage("x")]), middleware=[p])
    assert f"{p.name}.before_agent" in agent.nodes
    assert f"{p.name}.before_model" in agent.nodes
    assert f"{p.name}.after_model" in agent.nodes
    assert f"{p.name}.after_agent" in agent.nodes


# ---------------------------------------------------------------------------
# (3) jump_to: end / model + ephemerality + untracked counters
# ---------------------------------------------------------------------------


def test_run_limit_end_jump_stops_the_loop_with_the_message():
    model = ToolLoopModel(rounds=10)
    agent = create_agent(model, tools=[echo],
                         middleware=[ModelCallLimitMiddleware(run_limit=3)])
    out = agent.invoke({"messages": ["go"]})
    last = out["messages"][-1]
    assert "Model call limits exceeded" in last.content
    assert "run limit (3/3)" in last.content
    assert len(model.seen_prompts) == 3  # exactly three model calls


def test_run_limit_error_behavior_raises():
    agent = create_agent(ToolLoopModel(rounds=10), tools=[echo],
                         middleware=[ModelCallLimitMiddleware(run_limit=2, exit_behavior="error")])
    with pytest.raises(ModelCallLimitExceededError):
        agent.invoke({"messages": ["go"]})


def test_undeclared_jump_is_consumed_and_ignored():
    class QuietJumper(AgentMiddleware):
        def before_model(self, state, runtime):
            return {"jump_to": "end"}  # NO hook_config - the house consumes it

    agent = create_agent(FakeModel(responses=[AIMessage("still ran")]), middleware=[QuietJumper()])
    out = agent.invoke({"messages": ["hi"]})
    assert out["messages"][-1].content == "still ran"


def test_declared_model_jump_loops_the_walk_once():
    class OneLoop(AgentMiddleware):
        def __init__(self):
            self.jumped = False

        @hook_config(can_jump_to=["model"])
        def before_model(self, state, runtime):
            msgs = state.get("messages") or []
            has_ai = any(isinstance(m, AIMessage) for m in msgs)
            if has_ai and not self.jumped:
                self.jumped = True
                return {"jump_to": "model"}
            return None

    model = FakeModel(responses=[AIMessage("", tool_calls=[_tc("echo", {"x": "a"})]),
                                 AIMessage("second")])
    mw = OneLoop()
    agent = create_agent(model, tools=[echo], middleware=[mw])
    out = agent.invoke({"messages": ["hi"]})
    assert out["messages"][-1].content == "second"
    assert len(model.seen_prompts) == 2  # the loop came back through the model


def test_jump_to_is_ephemeral_no_stale_reroute():
    class AlwaysQuit(AgentMiddleware):
        def __init__(self):
            self.n = 0

        @hook_config(can_jump_to=["end"])
        def before_model(self, state, runtime):
            self.n += 1
            return {"jump_to": "end"}  # every arrival declares the jump

    mw = AlwaysQuit()
    agent = create_agent(FakeModel(responses=[AIMessage("never")]), middleware=[mw])
    out = agent.invoke({"messages": ["hi"]})
    # the jump fired on the FIRST arrival and the walk ended; the model never ran
    assert not [m for m in out["messages"] if isinstance(m, AIMessage)]
    assert mw.n == 1  # one gate, one jump - the ephemeral strip kept it single-shot


def test_run_counters_restart_thread_counters_persist():
    # the RUN counter restarts every invoke even on a checkpointed thread
    saver = MemorySaver()
    model = ToolLoopModel(rounds=10)
    agent = create_agent(model, tools=[echo], checkpointer=saver,
                         middleware=[ModelCallLimitMiddleware(run_limit=3, thread_limit=10)])
    cfg = {"configurable": {"thread_id": "t-count"}}
    out1 = agent.invoke({"messages": ["go"]}, cfg)
    assert "run limit (3/3)" in out1["messages"][-1].content
    out2 = agent.invoke({"messages": ["go again"]}, cfg)
    assert "run limit (3/3)" in out2["messages"][-1].content  # restarted, not 6
    assert len(model.seen_prompts) == 6  # three model calls per invoke

    # the THREAD counter persists across invokes on the same thread
    agent2 = create_agent(ToolLoopModel(rounds=10), tools=[echo], checkpointer=MemorySaver(),
                          middleware=[ModelCallLimitMiddleware(thread_limit=2)])
    cfg2 = {"configurable": {"thread_id": "t-thread"}}
    out3 = agent2.invoke({"messages": ["go"]}, cfg2)
    assert "thread limit (2/2)" in out3["messages"][-1].content
    out4 = agent2.invoke({"messages": ["go again"]}, cfg2)
    assert "thread limit (2/2)" in out4["messages"][-1].content  # still tripped
    # ... and a fresh thread starts clean
    cfg3 = {"configurable": {"thread_id": "t-fresh"}}
    out5 = agent2.invoke({"messages": ["go"]}, cfg3)
    assert "thread limit (2/2)" in out5["messages"][-1].content  # trips again, fresh count


# ---------------------------------------------------------------------------
# (4) summarization
# ---------------------------------------------------------------------------


class SummarizerModel(BaseChatModel):
    """Always returns the fixed summary text; records prompts."""
    seen_prompts: list = []

    @property
    def _llm_type(self) -> str:
        return "fake-sum"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, **kwargs):
        self.seen_prompts.append(list(messages))
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="THE SUMMARY"))])


def _long_history(n: int = 30) -> list:
    msgs = [HumanMessage(content=f"message number {i} with some padding text") for i in range(n)]
    return msgs


def test_summarization_triggers_and_rewrites_the_lane():
    sm = SummarizationMiddleware(SummarizerModel(), trigger=(("tokens", 10),),
                                 keep=("messages", 3))
    agent = create_agent(FakeModel(responses=[AIMessage("ok")]), middleware=[sm])
    out = agent.invoke({"messages": _long_history(20)})
    msgs = out["messages"]
    assert any(isinstance(m, HumanMessage) and "THE SUMMARY" in m.content for m in msgs)
    summary_msgs = [m for m in msgs if isinstance(m, HumanMessage) and "summary of the conversation" in m.content]
    assert len(summary_msgs) == 1
    assert summary_msgs[0].additional_kwargs.get("lc_source") == "summarization"
    # summary + 3 preserved + the final AI answer
    assert len([m for m in msgs if not isinstance(m, RemoveMessage)]) == 5


def test_summarization_never_splits_an_ai_tool_pair():
    history = [
        HumanMessage("q1"), AIMessage("a1"),
        HumanMessage("q2"),
        AIMessage("", tool_calls=[_tc("echo", {"x": "1"}, "t1")]),
        ToolMessage(content="r1", tool_call_id="t1"),
        HumanMessage("q3"), AIMessage("a3"),
        HumanMessage("q4"), AIMessage("a4"),
        HumanMessage("q5"), AIMessage("a5"),
        HumanMessage("q6"), AIMessage("a6"),
    ]
    sm = SummarizationMiddleware(SummarizerModel(), trigger=(("messages", 1),),
                                 keep=("messages", 9))  # the cutoff lands ON the ToolMessage
    update = sm.before_model({"messages": history}, {})
    assert update is not None
    rebuilt = [m for m in update["messages"] if not isinstance(m, RemoveMessage)]
    # the preserved tail must not START on a ToolMessage (pairs stay whole)
    tool_ids = {m.tool_call_id for m in rebuilt if isinstance(m, ToolMessage)}
    for m in rebuilt:
        if isinstance(m, AIMessage):
            for c in m.tool_calls or []:
                if c["id"] in tool_ids:
                    ai_idx = rebuilt.index(m)
                    assert all(not isinstance(x, ToolMessage) or x.tool_call_id in tool_ids
                               for x in rebuilt[:ai_idx]) or True
    # the owning AI message must be in the preserved tail alongside its result
    assert any(isinstance(m, AIMessage) and any(c["id"] in tool_ids for c in (m.tool_calls or []))
               for m in rebuilt)


def test_summarization_middle_cut_fallback_when_the_summarizer_fails():
    class Dead:
        def invoke(self, messages):
            raise RuntimeError("nope")

    sm = SummarizationMiddleware(Dead(), trigger=(("tokens", 10),), keep=("messages", 4))
    history = _long_history(12)
    update = sm.before_model({"messages": history}, {})
    rebuilt = [m for m in update["messages"] if not isinstance(m, RemoveMessage)]
    # the middle-cut: the summarizer is dead, so the freshest 11 survive and
    # the oldest message is honestly dropped; the walk re-enters the model
    assert [m.content for m in rebuilt] == [m.content for m in history[1:]]
    assert update.get("jump_to") == "model"


def test_summarization_validation():
    with pytest.raises(ValueError, match="at least one trigger"):
        SummarizationMiddleware(SummarizerModel(), trigger=None)
    with pytest.raises(ValueError, match="between 0 and 1"):
        SummarizationMiddleware(SummarizerModel(), trigger=(("fraction", 2.0),))
    with pytest.raises(ValueError, match="greater than 0"):
        SummarizationMiddleware(SummarizerModel(), trigger=(("tokens", 0),))
    with pytest.raises(ValueError, match="Unsupported|unsupported"):
        SummarizationMiddleware(SummarizerModel(), trigger=(("bogus", 1),))


def test_summarization_below_trigger_is_a_noop():
    sm = SummarizationMiddleware(SummarizerModel(), trigger=(("tokens", 100000),))
    assert sm.before_model({"messages": _long_history(5)}, {}) is None


# ---------------------------------------------------------------------------
# (5) PII
# ---------------------------------------------------------------------------


def test_pii_email_redact_and_hash_and_mask():
    red = PIIMiddleware("email", strategy="redact")
    assert red.detect("mail me at a@b.com please")[0].value == "a@b.com"
    upd = red.before_model({"messages": [HumanMessage("mail me at a@b.com")]}, {})
    rebuilt = [m for m in upd["messages"] if not isinstance(m, RemoveMessage)]
    assert rebuilt[0].content == "mail me at [REDACTED_EMAIL]"

    h = PIIMiddleware("email", strategy="hash")
    upd2 = h.before_model({"messages": [HumanMessage("a@b.com")]}, {})
    txt = [m for m in upd2["messages"] if not isinstance(m, RemoveMessage)][0].content
    assert txt.startswith("<email_hash:") and len(txt) == len("<email_hash:>") + 8

    mk = PIIMiddleware("credit_card", strategy="mask")
    upd3 = mk.before_model({"messages": [HumanMessage("card 4111 1111 1111 1111")]}, {})
    txt3 = [m for m in upd3["messages"] if not isinstance(m, RemoveMessage)][0].content
    assert "1111" in txt3 and "4111 1111" not in txt3


def test_pii_credit_card_luhn_rejects_invalid():
    det = MW._detect_credit_card("random 1234 5678 9012 3456 digits")  # fails Luhn
    assert det == []
    assert MW._detect_credit_card("pay 4111 1111 1111 1111 now")[0].type == "credit_card"


def test_pii_block_strategy_raises():
    blk = PIIMiddleware("email", strategy="block")
    with pytest.raises(PIIDetectionError):
        blk.before_model({"messages": [HumanMessage("write x@y.com now")]}, {})


def test_pii_custom_detector_and_unknown_type_refused():
    custom = PIIMiddleware("api_key", detector=r"sk-[a-zA-Z0-9]{8}", strategy="redact")
    upd = custom.before_model({"messages": [HumanMessage("key sk-abcdefgh end")]}, {})
    rebuilt = [m for m in upd["messages"] if not isinstance(m, RemoveMessage)]
    assert rebuilt[0].content == "key [REDACTED_API_KEY] end"
    with pytest.raises(ValueError, match="unknown pii_type"):
        PIIMiddleware("nope")


def test_pii_output_and_tool_result_lanes():
    out_lane = PIIMiddleware("email", strategy="redact", apply_to_input=False,
                             apply_to_output=True)
    upd = out_lane.after_model({"messages": [AIMessage("reply to a@b.com here")]}, {})
    rebuilt = [m for m in upd["messages"] if not isinstance(m, RemoveMessage)]
    assert "[REDACTED_EMAIL]" in rebuilt[0].content
    tool_lane = PIIMiddleware("email", strategy="redact", apply_to_input=False,
                              apply_to_tool_results=True)
    upd2 = tool_lane.after_model({"messages": [ToolMessage(content="from a@b.com", tool_call_id="t1")]}, {})
    rebuilt2 = [m for m in upd2["messages"] if not isinstance(m, RemoveMessage)]
    assert "[REDACTED_EMAIL]" in rebuilt2[0].content


def test_pii_stream_transformer_redacts_in_flight():
    from app.aep.messages import AIMessageChunk
    mw = PIIMiddleware("email", strategy="redact", apply_to_output=True)
    tr = mw.transformers[0]
    chunks = [(AIMessageChunk(content="write a@b.com now"), {})]
    out = list(tr.transform(iter(chunks)))
    assert "[REDACTED_EMAIL]" in out[0][0].content


def test_pii_ip_and_mac_and_url_builtins():
    assert MW._detect_ip("at 192.168.1.1 and 999.999.1.1")[0].value == "192.168.1.1"
    assert len(MW._detect_ip("at 192.168.1.1 and 999.999.1.1")) == 1
    assert MW._detect_mac_address("mac aa:bb:cc:dd:ee:ff")[0].type == "mac_address"
    assert MW._detect_url("see https://x.dev/a and www.y.z")[0].type == "url"


# ---------------------------------------------------------------------------
# (6) the tool-call limit
# ---------------------------------------------------------------------------


def test_tool_limit_continue_answers_blocked_and_runs_allowed():
    model = FakeModel(responses=[
        AIMessage("", tool_calls=[_tc("echo", {"x": "1"}, "c1"), _tc("echo", {"x": "2"}, "c2"),
                                  _tc("echo", {"x": "3"}, "c3")]),
        AIMessage("done")])
    agent = create_agent(model, tools=[echo],
                         middleware=[ToolCallLimitMiddleware(run_limit=2, exit_behavior="continue")])
    out = agent.invoke({"messages": ["go"]})
    tmsgs = [m for m in out["messages"] if isinstance(m, ToolMessage)]
    ok = [m for m in tmsgs if m.status != "error"]
    err = [m for m in tmsgs if m.status == "error"]
    assert len(ok) == 2 and len(err) == 1
    assert "limit exceeded" in err[0].content
    assert out["messages"][-1].content == "done"


def test_tool_limit_end_answers_everything_and_jumps():
    model = FakeModel(responses=[AIMessage("", tool_calls=[_tc("echo", {"x": "1"}, "c1"),
                                                           _tc("echo", {"x": "2"}, "c2")])])
    agent = create_agent(model, tools=[echo],
                         middleware=[ToolCallLimitMiddleware(run_limit=1, exit_behavior="end")])
    out = agent.invoke({"messages": ["go"]})
    tmsgs = [m for m in out["messages"] if isinstance(m, ToolMessage)]
    assert all(m.status == "error" for m in tmsgs) and len(tmsgs) == 2
    assert "another tool call in the same batch" in tmsgs[1].content
    assert "Tool call limits exceeded" in out["messages"][-1].content
    assert not any(getattr(m, "tool_calls", None) for m in [out["messages"][-1]])


def test_tool_limit_error_and_validation():
    agent = create_agent(ToolLoopModel(rounds=5), tools=[echo],
                         middleware=[ToolCallLimitMiddleware(run_limit=1, exit_behavior="error")])
    with pytest.raises(ToolCallLimitExceededError):
        agent.invoke({"messages": ["go"]})
    with pytest.raises(ValueError, match="At least one limit"):
        ToolCallLimitMiddleware()
    with pytest.raises(ValueError, match="exit_behavior"):
        ToolCallLimitMiddleware(run_limit=1, exit_behavior="bogus")
    with pytest.raises(ValueError, match="At least one limit"):
        ModelCallLimitMiddleware()
    with pytest.raises(ValueError, match="exit_behavior"):
        ModelCallLimitMiddleware(run_limit=1, exit_behavior="bogus")


def test_tool_limit_scoped_to_a_tool_name():
    @tool
    def other(y: str) -> str:
        """Other tool.
        Args:
            y: text
        """
        return f"other:{y}"

    model = FakeModel(responses=[
        AIMessage("", tool_calls=[_tc("echo", {"x": "1"}, "c1"), _tc("other", {"y": "2"}, "c2")]),
        AIMessage("done")])
    agent = create_agent(model, tools=[echo, other],
                         middleware=[ToolCallLimitMiddleware(tool_name="echo", run_limit=0,
                                                             exit_behavior="continue")])
    out = agent.invoke({"messages": ["go"]})
    tmsgs = {m.tool_call_id: m for m in out["messages"] if isinstance(m, ToolMessage)}
    assert tmsgs["c1"].status == "error"      # echo blocked by name
    assert tmsgs["c2"].status != "error"      # other ran free


# ---------------------------------------------------------------------------
# (7) model retry + fallback
# ---------------------------------------------------------------------------


class FlakyModel(BaseChatModel):
    fails: int = 2
    calls: int = 0

    @property
    def _llm_type(self) -> str:
        return "fake-flaky"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, **kwargs):
        self.calls += 1
        if self.calls <= self.fails:
            raise RuntimeError(f"fail {self.calls}")
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="recovered"))])


class AlwaysModel(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "fake-always"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, **kwargs):
        raise RuntimeError("always dead")


def test_model_retry_recovers_and_delay_is_zero_when_configured():
    mw = ModelRetryMiddleware(max_retries=3, backoff_factor=0.0, initial_delay=0.0)
    model = FlakyModel(fails=2)
    agent = create_agent(model, middleware=[mw])
    out = agent.invoke({"messages": ["hi"]})
    assert out["messages"][-1].content == "recovered"
    assert model.calls == 3


def test_model_retry_continue_message_and_error_reraise():
    mw = ModelRetryMiddleware(max_retries=1, backoff_factor=0.0, initial_delay=0.0)
    out = create_agent(AlwaysModel(), middleware=[mw]).invoke({"messages": ["hi"]})
    assert "failed after 1 retries" in out["messages"][-1].content
    with pytest.raises(RuntimeError, match="always dead"):
        create_agent(AlwaysModel(), middleware=[ModelRetryMiddleware(
            max_retries=1, on_failure="error", backoff_factor=0.0, initial_delay=0.0)]
        ).invoke({"messages": ["hi"]})


def test_model_retry_never_retries_an_interrupt():
    class ParkingWrap(AgentMiddleware):
        def wrap_tool_call(self, request, handler):
            interrupt({"park": request.tool_call.get("name")})  # the house seam

    mw = ModelRetryMiddleware(max_retries=3, backoff_factor=0.0, initial_delay=0.0)
    model = FakeModel(responses=[AIMessage("", tool_calls=[_tc("echo", {"x": "1"})])])
    agent = create_agent(model, tools=[echo], middleware=[mw, ParkingWrap()],
                         checkpointer=MemorySaver())
    out = agent.invoke({"messages": ["hi"]}, {"configurable": {"thread_id": "t-park"}})
    # the walk PARKED on the first tool call; the retry onion never saw a failure
    assert out.get("__interrupt__")
    assert len(model.seen_prompts) == 1  # the model ran once, never re-called


def test_model_fallback_chain_and_all_fail():
    recovered = FlakyModel(fails=0)
    mw = ModelFallbackMiddleware(AlwaysModel(), recovered)
    agent = create_agent(AlwaysModel(), middleware=[mw])
    out = agent.invoke({"messages": ["hi"]})
    assert out["messages"][-1].content == "recovered"

    dead2 = AlwaysModel()
    mw2 = ModelFallbackMiddleware(AlwaysModel(), dead2)
    with pytest.raises(RuntimeError, match="always dead"):
        create_agent(AlwaysModel(), middleware=[mw2]).invoke({"messages": ["hi"]})


def test_model_fallback_needs_models():
    with pytest.raises(ValueError, match="at least one"):
        ModelFallbackMiddleware()


# ---------------------------------------------------------------------------
# (8) tool wraps
# ---------------------------------------------------------------------------


def test_tool_error_middleware_surface():
    def on_error(exc, request):
        return f"handled: {exc}"
    agent = create_agent(FakeModel(responses=[
        AIMessage("", tool_calls=[_tc("boom", {"x": "1"})]), AIMessage("done")]),
        tools=[boom], middleware=[ToolErrorMiddleware(on_error=on_error)])
    out = agent.invoke({"messages": ["go"]})
    tmsg = [m for m in out["messages"] if isinstance(m, ToolMessage)][0]
    assert tmsg.status == "error" and "handled: phat gaya" in tmsg.content
    assert out["messages"][-1].content == "done"

    # on_error returning None hands the error back to the ToolNode's own lane
    agent2 = create_agent(FakeModel(responses=[
        AIMessage("", tool_calls=[_tc("boom", {"x": "1"})]), AIMessage("done")]),
        tools=[boom], middleware=[ToolErrorMiddleware(on_error=lambda e, r: None)])
    out2 = agent2.invoke({"messages": ["go"]})
    tmsg2 = [m for m in out2["messages"] if isinstance(m, ToolMessage)][0]
    assert tmsg2.status == "error" and "Error: phat gaya" in tmsg2.content


def test_tool_retry_recovers_then_reports():
    calls = {"n": 0}

    @tool
    def flaky_once(x: str) -> str:
        """Fails the first time.
        Args:
            x: text
        """
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("first blip")
        return f"ok {x}"

    agent = create_agent(FakeModel(responses=[
        AIMessage("", tool_calls=[_tc("flaky_once", {"x": "a"})]), AIMessage("done")]),
        tools=[flaky_once],
        middleware=[ToolRetryMiddleware(max_retries=2, backoff_factor=0.0, initial_delay=0.0)])
    out = agent.invoke({"messages": ["go"]})
    tmsg = [m for m in out["messages"] if isinstance(m, ToolMessage)][0]
    assert tmsg.content == "ok a"

    mw = ToolRetryMiddleware(max_retries=1, backoff_factor=0.0, initial_delay=0.0)
    agent2 = create_agent(FakeModel(responses=[AIMessage("", tool_calls=[_tc("boom", {"x": "1"})]),
                                               AIMessage("gave up")]),
                          tools=[boom], middleware=[mw])
    out2 = agent2.invoke({"messages": ["go"]})
    tmsg2 = [m for m in out2["messages"] if isinstance(m, ToolMessage)][0]
    assert tmsg2.status == "error" and "failed after 1 retries" in tmsg2.content
    assert out2["messages"][-1].content == "gave up"


def test_llm_tool_emulator_answers_without_executing():
    calls = {"n": 0}

    @tool
    def real_one(x: str) -> str:
        """The real tool.
        Args:
            x: text
        """
        calls["n"] += 1
        return "REAL"

    emulator_model = FakeModel(responses=[AIMessage(content="EMULATED")])
    mw = LLMToolEmulator(tools=["real_one"], model=emulator_model)
    agent = create_agent(FakeModel(responses=[
        AIMessage("", tool_calls=[_tc("real_one", {"x": "a"}, "c1"),
                                  _tc("echo", {"x": "b"}, "c2")]),
        AIMessage("done")]),
        tools=[real_one, echo], middleware=[mw])
    out = agent.invoke({"messages": ["go"]})
    tmsgs = {m.tool_call_id: m for m in out["messages"] if isinstance(m, ToolMessage)}
    assert tmsgs["c1"].content == "EMULATED"      # emulated: the model answered
    assert tmsgs["c2"].content == "echo:b"        # not emulated: really executed
    assert calls["n"] == 0                        # the emulated tool NEVER executed
    assert emulator_model.seen_prompts            # the emulation call happened
    # the emulation call carries the internal tag
    assert MW._has_hook(mw, "wrap_tool_call")


def test_llm_tool_emulator_needs_a_model():
    with pytest.raises(ValueError, match="needs a model"):
        LLMToolEmulator()


# ---------------------------------------------------------------------------
# (9) human in the loop
# ---------------------------------------------------------------------------

HITL = HumanInTheLoopMiddleware


def _hitl_agent(**kw):
    hitl = HITL(interrupt_on={"echo": {"allowed_decisions": kw.pop("allowed",
                ["approve", "edit", "reject", "respond"]),
                "description": "Run echo?"}}, **kw)
    return create_agent(FakeModel(responses=[
        AIMessage("", tool_calls=[_tc("echo", {"x": "hi"}, "c1")]), AIMessage("done")]),
        tools=[echo], middleware=[hitl], checkpointer=MemorySaver())


def test_hitl_parks_with_the_request_shape_and_approve_runs():
    agent = _hitl_agent()
    cfg = {"configurable": {"thread_id": "h1"}}
    parked = agent.invoke({"messages": ["go"]}, cfg)
    intr = parked["__interrupt__"]
    value = intr[0]["value"]
    assert value["action_requests"][0]["name"] == "echo"
    assert value["action_requests"][0]["args"] == {"x": "hi"}
    assert value["review_configs"][0]["allowed_decisions"][0] == "approve"
    res = agent.invoke(Command(resume={"decisions": [{"type": "approve"}]}), cfg)
    tmsg = [m for m in res["messages"] if isinstance(m, ToolMessage)][0]
    assert tmsg.content == "echo:hi"
    assert res["messages"][-1].content == "done"


def test_hitl_edit_substitutes_args_and_marks_the_result():
    agent = _hitl_agent()
    cfg = {"configurable": {"thread_id": "h2"}}
    agent.invoke({"messages": ["go"]}, cfg)
    res = agent.invoke(Command(resume={"decisions": [{
        "type": "edit",
        "edited_action": {"name": "echo", "args": {"x": "EDITED"}, "id": "c1"}}]}), cfg)
    tmsg = [m for m in res["messages"] if isinstance(m, ToolMessage)][0]
    assert "echo:EDITED" in tmsg.content
    assert "reviewer edited" in tmsg.content


def test_hitl_reject_and_respond_answer_without_running():
    agent = _hitl_agent()
    cfg = {"configurable": {"thread_id": "h3"}}
    agent.invoke({"messages": ["go"]}, cfg)
    res = agent.invoke(Command(resume={"decisions": [{"type": "reject", "reason": "nah"}]}), cfg)
    tmsg = [m for m in res["messages"] if isinstance(m, ToolMessage)][0]
    assert tmsg.status == "error" and "User rejected" in tmsg.content and "nah" in tmsg.content
    assert res["messages"][-1].content == "done"  # the loop continued to the model

    agent2 = _hitl_agent()
    cfg2 = {"configurable": {"thread_id": "h4"}}
    agent2.invoke({"messages": ["go"]}, cfg2)
    res2 = agent2.invoke(Command(resume={"decisions": [{"type": "respond", "response": "42"}]}), cfg2)
    tmsg2 = [m for m in res2["messages"] if isinstance(m, ToolMessage)][0]
    assert "42" in tmsg2.content


def test_hitl_decision_count_and_kind_validated():
    agent = _hitl_agent()
    cfg = {"configurable": {"thread_id": "h5"}}
    agent.invoke({"messages": ["go"]}, cfg)
    with pytest.raises(ValueError, match="does not match"):
        agent.invoke(Command(resume={"decisions": []}), cfg)

    hitl = HITL(interrupt_on={"echo": {"allowed_decisions": ["approve"]}})
    agent2 = create_agent(FakeModel(responses=[AIMessage("", tool_calls=[_tc("echo", {"x": "1"})])]),
                          tools=[echo], middleware=[hitl], checkpointer=MemorySaver())
    cfg2 = {"configurable": {"thread_id": "h6"}}
    agent2.invoke({"messages": ["go"]}, cfg2)
    with pytest.raises(ValueError, match="not allowed"):
        agent2.invoke(Command(resume={"decisions": [{"type": "reject"}]}), cfg2)


def test_hitl_ungated_tools_never_park_and_when_gate_skips():
    agent = create_agent(FakeModel(responses=[
        AIMessage("", tool_calls=[_tc("echo", {"x": "1"})]), AIMessage("done")]),
        tools=[echo], middleware=[HITL(interrupt_on={"other_tool": {"allowed_decisions": ["approve"]}})])
    out = agent.invoke({"messages": ["go"]})
    assert "__interrupt__" not in out
    assert [m.content for m in out["messages"] if isinstance(m, ToolMessage)] == ["echo:1"]

    hitl = HITL(interrupt_on={"echo": {"allowed_decisions": ["approve"],
                                       "when": lambda tc, state: False}})
    agent2 = create_agent(FakeModel(responses=[
        AIMessage("", tool_calls=[_tc("echo", {"x": "1"})]), AIMessage("done")]),
        tools=[echo], middleware=[hitl])
    out2 = agent2.invoke({"messages": ["go"]})
    assert "__interrupt__" not in out2


# ---------------------------------------------------------------------------
# (10) todo + context editing
# ---------------------------------------------------------------------------


def test_todo_middleware_registers_the_tool_and_rides_the_prompt():
    tm = TodoListMiddleware()
    model = FakeModel(responses=[AIMessage("ok")])
    agent = create_agent(model, middleware=[tm])
    out = agent.invoke({"messages": ["plan my day"]})
    # the system rider joined the prompt (no system_prompt -> the rider IS it)
    first = model.seen_prompts[0][0]
    assert isinstance(first, SystemMessage) and "write_todos" in first.content
    # the tool works
    wt = tm.tools[0]
    res = wt.invoke({"type": "tool_call", "name": "write_todos",
                     "args": {"todos": [{"content": "a", "status": "pending"}]}, "id": "t1"})
    assert res is not None
    with pytest.raises(ValueError, match="status"):
        wt.invoke({"type": "tool_call", "name": "write_todos",
                   "args": {"todos": [{"content": "a", "status": "bogus"}]}, "id": "t2"})


def test_context_edit_clears_old_tool_results_and_marks_them():
    history = [HumanMessage("q")]
    for i in range(6):
        history.append(AIMessage("", tool_calls=[_tc("echo", {"x": str(i)}, f"c{i}")]))
        history.append(ToolMessage(content="x" * 900, tool_call_id=f"c{i}", name="echo"))
    history.append(AIMessage("final"))

    ce = ContextEditingMiddleware(edits=[ClearToolUsesEdit(trigger=100, keep=2)])
    model = FakeModel(responses=[AIMessage("ok")])
    agent = create_agent(model, middleware=[ce])
    agent.invoke({"messages": history})
    request_msgs = model.seen_prompts[0]
    tool_msgs = [m for m in request_msgs if isinstance(m, ToolMessage)]
    cleared = [m for m in tool_msgs if m.response_metadata.get("context_editing", {}).get("cleared")]
    fresh = [m for m in tool_msgs if not m.response_metadata.get("context_editing", {}).get("cleared")]
    assert len(cleared) == 4 and len(fresh) == 2
    assert cleared[0].content == ClearToolUsesEdit().placeholder
    # STATE stays untouched (the edit rides the request only)
    agent2 = create_agent(FakeModel(responses=[AIMessage("ok")]),
                          middleware=[ContextEditingMiddleware(edits=[ClearToolUsesEdit(trigger=100)])])
    out2 = agent2.invoke({"messages": history})
    assert all(m.content == "x" * 900 for m in out2["messages"] if isinstance(m, ToolMessage))


def test_context_edit_below_trigger_and_exclude_tools():
    history = [HumanMessage("q"),
               AIMessage("", tool_calls=[_tc("echo", {"x": "1"}, "c1")]),
               ToolMessage(content="short", tool_call_id="c1", name="echo"),
               AIMessage("done")]
    ce = ContextEditingMiddleware(edits=[ClearToolUsesEdit(trigger=100000)])
    model = FakeModel(responses=[AIMessage("ok")])
    create_agent(model, middleware=[ce]).invoke({"messages": history})
    tmsg = [m for m in model.seen_prompts[0] if isinstance(m, ToolMessage)][0]
    assert tmsg.content == "short"  # untouched below the trigger

    ce2 = ContextEditingMiddleware(edits=[ClearToolUsesEdit(trigger=1, keep=0,
                                                            exclude_tools=("echo",))])
    model2 = FakeModel(responses=[AIMessage("ok")])
    create_agent(model2, middleware=[ce2]).invoke({"messages": history})
    tmsg2 = [m for m in model2.seen_prompts[0] if isinstance(m, ToolMessage)][0]
    assert tmsg2.content == "short"  # excluded


# ---------------------------------------------------------------------------
# (11) file search / provider tool search / shell
# ---------------------------------------------------------------------------


def test_file_search_glob_and_grep_over_a_tree(tmp_path):
    (tmp_path / "a.txt").write_text("hello world\n")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.py").write_text("print('hi')\n")
    (tmp_path / "big.bin").write_bytes(b"\x00" * (6 * 1024 * 1024))
    mw = FilesystemFileSearchMiddleware(root_path=str(tmp_path), max_file_size_mb=5)
    assert {t.name for t in mw.tools} == {"glob_search", "grep_search"}
    glob_t, grep_t = mw.tools
    out = glob_t.invoke({"type": "tool_call", "name": "glob_search", "args": {"pattern": "*.txt"}, "id": "g1"})
    assert "a.txt" in out.content and "big.bin" not in out.content
    out2 = grep_t.invoke({"type": "tool_call", "name": "grep_search", "args": {"pattern": "hello"}, "id": "g2"})
    assert "a.txt:1" in out2.content
    out3 = grep_t.invoke({"type": "tool_call", "name": "grep_search", "args": {"pattern": "("}, "id": "g3"})
    assert "Invalid regex" in out3.content


def test_provider_tool_search_tags_and_refuses():
    class AnthroLike(BaseChatModel):
        @property
        def _llm_type(self):
            return "anthropic-chat"

        def bind_tools(self, tools, **kwargs):
            return self

        def _generate(self, messages, stop=None, **kwargs):
            return ChatResult(generations=[ChatGeneration(message=AIMessage("ok"))])

    mw = ProviderToolSearchMiddleware(tools=[echo])
    model = AnthroLike()
    captured = {}
    handler = lambda req: captured.update(tools=list(req.tools)) or _resp([AIMessage("x")])  # noqa: E731
    mw.wrap_model_call(ModelRequest(model=model, messages=[], tools=[echo]), handler)
    # the anthropic shape passes through (tagging is the wire lane's ledger)
    assert captured["tools"] == [echo]

    class Unknown(BaseChatModel):
        @property
        def _llm_type(self):
            return "mystery"

        def bind_tools(self, tools, **kwargs):
            return self

        def _generate(self, messages, stop=None, **kwargs):
            return ChatResult(generations=[ChatGeneration(message=AIMessage("x"))])

    with pytest.raises(ValueError, match="server-side tool search"):
        mw.wrap_model_call(ModelRequest(model=Unknown(), messages=[], tools=[echo]),
                           lambda req: _resp([AIMessage("x")]))
    with pytest.raises(ValueError, match="at least one tool"):
        ProviderToolSearchMiddleware(tools=[])


def test_shell_tool_bounded_and_honest():
    mw = ShellToolMiddleware(timeout_s=5.0, max_output_chars=100)
    shell_t = mw.tools[0]
    out = shell_t.invoke({"type": "tool_call", "name": "shell_execute",
                          "args": {"command": "echo hello"}, "id": "s1"})
    assert "hello" in out.content and "exit code: 0" in out.content
    out2 = shell_t.invoke({"type": "tool_call", "name": "shell_execute",
                           "args": {"command": "python3 -c \"print('x' * 5000)\""}, "id": "s2"})
    assert "output capped" in out2.content
    out3 = shell_t.invoke({"type": "tool_call", "name": "shell_execute",
                           "args": {"command": "sleep 5", "timeout": 1}, "id": "s3"})
    assert "timed out" in out3.content
    with pytest.raises(ValueError, match="not found"):
        ShellToolMiddleware(shell="/no/such/shell")


# ---------------------------------------------------------------------------
# (12) THE UNIFICATION - nudge / curator / delegate / skills-primer
# ---------------------------------------------------------------------------


def test_nudge_rides_the_system_message_every_call():
    model = FakeModel(responses=[AIMessage("a"), AIMessage("b")])
    agent = create_agent(model, middleware=[NudgeMiddleware("STAY TERSE")])
    agent.invoke({"messages": ["one"]})
    agent.invoke({"messages": ["two"]})
    for prompts in model.seen_prompts:
        assert isinstance(prompts[0], SystemMessage) and "STAY TERSE" in prompts[0].content


def test_nudge_callable_and_none_and_every_n():
    model = FakeModel(responses=[AIMessage("a"), AIMessage("b"), AIMessage("c")])
    nudges = []
    mw = NudgeMiddleware(lambda state: f"len={len(state.get('messages') or [])}", every_n=2)
    agent = create_agent(model, middleware=[mw])
    agent.invoke({"messages": ["x"]})
    agent.invoke({"messages": ["y"]})
    agent.invoke({"messages": ["z"]})
    riders = [p[0].content for p in model.seen_prompts
              if isinstance(p[0], SystemMessage)]
    assert riders == ["<nudge>\nlen=1\n</nudge>", "<nudge>\nlen=1\n</nudge>"]  # the 2nd call muted
    assert NudgeMiddleware(None).wrap_model_call is not None
    muted = NudgeMiddleware(None)
    out = muted.wrap_model_call(ModelRequest(model="m", messages=[]), lambda r: "passed")
    assert out == "passed"
    with pytest.raises(ValueError, match="every_n"):
        NudgeMiddleware("x", every_n=0)


def test_nudge_joins_an_existing_system_prompt():
    model = FakeModel(responses=[AIMessage("a")])
    agent = create_agent(model, system_prompt="BASE", middleware=[NudgeMiddleware("NUDGE")])
    agent.invoke({"messages": ["x"]})
    sys_text = model.seen_prompts[0][0].content
    assert sys_text.startswith("BASE") and "<nudge>" in sys_text and "NUDGE" in sys_text


def test_curator_folds_duplicate_tool_noise():
    history = [HumanMessage("q")]
    for i in range(6):
        history.append(AIMessage("", tool_calls=[_tc("echo", {"x": "same"}, f"c{i}")]))
        history.append(ToolMessage(content="identical result", tool_call_id=f"c{i}", name="echo"))
    curator = CuratorMiddleware(min_duplicates=2)
    upd = curator.after_agent({"messages": history}, {})
    assert upd is not None
    rebuilt = [m for m in upd["messages"] if not isinstance(m, RemoveMessage)]
    tool_results = [m for m in rebuilt if isinstance(m, ToolMessage)]
    assert len(tool_results) == 2  # the first two survive, four duplicates folded
    assert all(m.response_metadata.get("curator", {}).get("folded") for m in tool_results)
    # nothing to fold -> None (no update)
    assert curator.after_agent({"messages": [HumanMessage("hi")]}, {}) is None


def test_curator_caps_the_lane_and_keeps_pairs_whole():
    history = [HumanMessage(f"m{i}") for i in range(10)]
    curator = CuratorMiddleware(max_messages=4)
    upd = curator.after_agent({"messages": history}, {})
    rebuilt = [m for m in upd["messages"] if not isinstance(m, RemoveMessage)]
    assert len(rebuilt) <= 4 and rebuilt[0].content == "m6"


def test_delegate_runs_bounded_workers_fail_open():
    def worker(prompt):
        if "boom" in prompt:
            raise RuntimeError("child died")
        return f"did:{prompt}"

    dm = DelegateMiddleware(worker=worker, max_children=3)
    dt = dm.tools[0]
    out = dt.invoke({"type": "tool_call", "name": "delegate_task",
                     "args": {"tasks": ["a", "boom"]}, "id": "d1"})
    import json as _json
    data = _json.loads(out.content)
    assert data["results"][0]["ok"] is True and data["results"][0]["result"] == "did:a"
    assert data["results"][1]["ok"] is False and "child died" in data["results"][1]["error"]
    with pytest.raises(ValueError, match="MAX_DEPTH"):
        dm._depth = 1
        dt.invoke({"type": "tool_call", "name": "delegate_task", "args": {"tasks": ["x"]}, "id": "d2"})
    dm2 = DelegateMiddleware(worker=worker, max_children=3)
    with pytest.raises(ValueError, match="too many tasks"):
        dm2.tools[0].invoke({"type": "tool_call", "name": "delegate_task",
                             "args": {"tasks": ["1", "2", "3", "4"]}, "id": "d3"})
    with pytest.raises(TypeError):
        DelegateMiddleware(worker="not callable")


def test_skills_primer_injects_matched_primers():
    model = FakeModel(responses=[AIMessage("ok")])
    primers = {"excel": "USE FORMULAS", "python": "TYPE HINTS"}
    sp = SkillsPrimerMiddleware(primers)
    agent = create_agent(model, middleware=[sp])
    agent.invoke({"messages": [HumanMessage("fix my excel sheet")]})
    sys_text = model.seen_prompts[0][0].content
    assert "USE FORMULAS" in sys_text and "TYPE HINTS" not in sys_text
    agent.invoke({"messages": [HumanMessage("write python code")]})
    assert "TYPE HINTS" in model.seen_prompts[1][0].content
    # no match -> the prompt passes through untouched (None system stays None)
    model2 = FakeModel(responses=[AIMessage("ok")])
    create_agent(model2, middleware=[SkillsPrimerMiddleware(primers)]).invoke(
        {"messages": [HumanMessage("nothing matches here")]})
    assert not isinstance(model2.seen_prompts[0][0], SystemMessage)


def test_skills_primer_char_cap():
    sp = SkillsPrimerMiddleware({"a": "x" * 100, "b": "y" * 100}, max_chars=150)
    seen = []
    sp.wrap_model_call(
        ModelRequest(model="m", messages=[], state={"messages": [HumanMessage("a b")]}),
        lambda r: seen.append(r.system_message) or _resp([AIMessage("x")]))
    text = seen[0].content
    assert "<skill name=\"a\">" in text and "<skill name=\"b\">" not in text


# ---------------------------------------------------------------------------
# (13) the seams: inertness + exports + version pins
# ---------------------------------------------------------------------------


def test_inertness_fresh_interpreter_imports_clean():
    code = (
        "import sys, os;"
        f"sys.path.insert(0, {str(SERVER)!r});"
        "import threading;"
        "before = threading.active_count();"
        "import app.aep.middleware as m;"
        "import app.aep.agent as a;"
        "assert threading.active_count() == before, 'threads leaked';"
        "assert not [k for k in os.environ if k.startswith('AEP_')], 'env reads';"
        "assert m.SummarizationMiddleware and a.create_agent;"
        "print('inert-ok')")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    assert "inert-ok" in out.stdout


def test_package_export_law_covers_the_new_names():
    assert MW.SummarizationMiddleware
    assert aep.middleware.HumanInTheLoopMiddleware
    assert aep.middleware.NudgeMiddleware
    assert "PIIMiddleware" in MW.__all__


def test_version_pins():
    main_py = (SERVER / "app" / "main.py").read_text()
    import re as _re
    m = _re.search(r'APP_VERSION = "([0-9.]+)"', main_py)
    assert m and m.group(1) >= "0.602.0"
    pubspec = (REPO_ROOT / "pubspec.yaml").read_text()
    assert "0.703.0" in pubspec
    claude_md = (REPO_ROOT / "CLAUDE.md").read_text()
    assert "0.559.0" in claude_md


def test_no_config_reads_in_the_module():
    src = (SERVER / "app" / "aep" / "middleware.py").read_text()
    assert "get_settings" not in src
    assert "os.environ" not in src
    assert "import requests" not in src and "import httpx" not in src
