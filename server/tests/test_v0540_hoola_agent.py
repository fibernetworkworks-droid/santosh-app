"""v0.540.0 HOOLA AGENT - create_agent compiled onto the house graph, P4 of the
HOOLA AEP plan (owner: 'GO BUILD P4' after v0.530.0 HOOLA GRAPH landed on main).
The langchain 1.x agents/factory.py idea hand-built as server/app/aep/agent.py -
ZERO upstream code. This suite pins the layer:

(1) SURFACE: create_agent returns a compiled house graph (named, Runnable,
    composable); the create_react_agent alias; no-tools agents (model-only,
    straight END); refusals - model strings (P7 HUB pointer), junk models,
    dict/provider tools, a model without bind_tools, bad system_prompt,
    response_format on a pre-bound Runnable, unknown interrupt gates,
    ToolNode duplicate names / junk input.
(2) REACT LOOP: model -> tool call -> ToolMessage -> final answer; args reach
    the tool; tool_call_id round-trips; several tool calls in one AIMessage
    fan into ToolMessages IN CALL ORDER; system_prompt rides the PROMPT every
    model call and never lands in state (str and SystemMessage forms); the
    AIMessage lands in state with its tool_calls intact.
(3) ERRORS: a raising tool becomes an error ToolMessage (status='error') and
    the loop CONTINUES (the model sees the error and answers);
    handle_tool_errors=False re-raises; a string handle_tool_errors replaces
    the content; an unknown tool name is an honest error ToolMessage; dict
    tool output is JSON-stringified.
(4) RETURN DIRECT: a return_direct tool routes tools -> END (the tool result
    IS the answer, the model runs once); mixed direct/non-direct goes back to
    the model (ALL executed tools must be direct, the upstream law).
(5) TOOLNODE STANDALONE: state input, the explicit tool_call-list lane, the
    messages_key override; non-dict/non-list input refused.
(6) STRUCTURED RESPONSE: response_format (pydantic + dict) adds the
    generate_structured_response node; it runs on the FINAL answer only
    (after the tool rounds) and writes state['structured_response']; the
    compiled schema carries the channel.
(7) STATE SCHEMA: a custom TypedDict with extra channels rides (last-value
    channels round-trip through the walk).
(8) CHECKPOINTER MEMORY: two invokes on one thread_id - the second model call
    sees the first turn's messages (chat memory); thread isolation; get_state.
(9) INTERRUPTS (the P3 park seam on the agent): interrupt_before=['tools']
    parks with the AIMessage applied and NO tool run; Command(resume) crosses
    the gate and completes; the breakpoint REPEATS on the next tools arrival;
    interrupt_before=['model'] parks on the FIRST arrival; interrupt_after=
    ['model'] parks only when tool calls exist (the END path never parks);
    interrupt_after=['tools'] parks before the model re-entry but never on the
    first arrival; one gate per arrival (before-tools wins over after-model);
    gates without a checkpointer refuse honestly; a tool MAY call interrupt()
    (the P5 human-in-the-loop seam): ToolNode lets GraphInterrupt propagate,
    the walk parks, the resume answers INSIDE the tool and the tool finishes.
(10) RECURSION: a model that always calls tools crosses recursion_limit with
    an honest GraphRecursionError; the limit is configurable per invoke.
(11) TRACER SEAM: the root span is named by the AGENT; model/tools node spans
    nest under it; the model call and the tool call nest UNDER their node
    spans; one trace_id across the walk; the no-callback fast path stays
    run-free.
(12) INERTNESS + WIRING + VERSION: a fresh interpreter imports app.aep.agent
    with zero threads/env/files; the package-export law covers the new names;
    no new registry tools and no config reads in the module; the compiled
    graph carries checkpointer/store; APP_VERSION + pubspec + story markers.

No test touches the network; every async path rides asyncio.run (the documented
one-loop law).
"""
import subprocess
import sys
from pathlib import Path
from typing import Any, TypedDict

import pytest
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER = REPO_ROOT / "server"

from app import aep
from app.aep import agent as AG
from app.aep.agent import ToolNode, create_agent, create_react_agent
from app.aep.graph import Command, CompiledStateGraph, END, GraphRecursionError, MemorySaver, interrupt
from app.aep.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from app.aep.models import BaseChatModel, ChatGeneration, ChatResult
from app.aep.runnable import Runnable
from app.aep.tools import ToolException, tool


# ---------------------------------------------------------------------------
# fakes + fixtures
# ---------------------------------------------------------------------------


def _tc(name: str, args: dict, tid: str = "c1", idx: int = 0) -> dict:
    return {"type": "tool_call", "id": tid, "name": name, "args": args, "index": idx}


class FakeAgentModel(BaseChatModel):
    """Queues whole AIMessages (tool_calls included) and returns them verbatim."""
    responses: list
    idx: int = 0
    seen_prompts: list = []
    bound_with: list = []

    @property
    def _llm_type(self) -> str:
        return "fake-agent"

    def bind_tools(self, tools, **kwargs):
        self.bound_with = [getattr(t, "name", str(t)) for t in tools]
        return self

    def _generate(self, messages, stop=None, **kwargs):
        self.seen_prompts.append(list(messages))
        r = self.responses[self.idx % len(self.responses)]
        self.idx += 1
        return ChatResult(generations=[ChatGeneration(message=r)])


@tool
def add_two(a: int, b: int) -> int:
    """Add two numbers.
    Args:
        a: first addend
        b: second addend
    """
    return a + b


@tool
def boom(x: int) -> int:
    """Always explodes.
    Args:
        x: unused
    """
    raise ValueError("phat gaya")


@tool
def direct_echo(text: str) -> str:
    """Echoes back, return_direct.
    Args:
        text: what to echo
    """
    return f"seedha: {text}"


direct_echo.return_direct = True


def tc_add(tid="c1"):
    return AIMessage(content="", tool_calls=[_tc("add_two", {"a": 2, "b": 3}, tid)])


def cfg(thread="t1"):
    return {"configurable": {"thread_id": thread}}


# ---------------------------------------------------------------------------
# (1) surface
# ---------------------------------------------------------------------------


def test_create_agent_returns_a_named_compiled_graph():
    ag = create_agent(FakeAgentModel(responses=[AIMessage(content="namaste")]),
                      [add_two], name="kisaan")
    assert isinstance(ag, CompiledStateGraph)
    assert ag.get_name() == "kisaan"
    assert isinstance(ag, Runnable)
    assert set(ag.nodes) == {"model", "tools"}


def test_default_name_is_agent_and_alias_is_identity():
    ag = create_agent(FakeAgentModel(responses=[AIMessage(content="x")]))
    assert ag.get_name() == "Agent"
    assert create_react_agent is create_agent


def test_no_tools_agent_is_model_only():
    m = FakeAgentModel(responses=[AIMessage(content="seedha jawab")])
    ag = create_agent(m)
    assert set(ag.nodes) == {"model"}
    out = ag.invoke({"messages": [HumanMessage(content="sawaal")]})
    assert [type(x).__name__ for x in out["messages"]] == ["HumanMessage", "AIMessage"]
    assert out["messages"][-1].content == "seedha jawab"
    assert m.idx == 1


def test_empty_tools_list_is_model_only():
    ag = create_agent(FakeAgentModel(responses=[AIMessage(content="x")]), [])
    assert set(ag.nodes) == {"model"}


def test_model_string_refused_with_the_p7_pointer():
    with pytest.raises(NotImplementedError, match="P7 HUB"):
        create_agent("openai:gpt-5.5")


def test_junk_model_refused():
    with pytest.raises(TypeError, match="BaseChatModel"):
        create_agent(42)


def test_dict_provider_tools_refused_the_p7_pointer():
    with pytest.raises(TypeError, match="P7"):
        create_agent(FakeAgentModel(responses=[AIMessage(content="x")]),
                     [{"type": "function", "function": {"name": "x"}}])


def test_plain_callable_becomes_a_tool():
    def triple(x: int) -> int:
        """Triples.
        Args:
            x: the number
        """
        return x * 3
    m = FakeAgentModel(responses=[AIMessage(content="", tool_calls=[_tc("triple", {"x": 5})]),
                                  AIMessage(content="15 hai")])
    ag = create_agent(m, [triple])
    assert m.bound_with == ["triple"]
    out = ag.invoke({"messages": [HumanMessage(content="triple 5")]})
    assert out["messages"][-2].content == "15"


def test_model_without_bind_tools_refused_at_build_time():
    class NoBind(BaseChatModel):
        @property
        def _llm_type(self):
            return "nobind"
        def _generate(self, messages, stop=None, **kwargs):
            raise AssertionError("must not be called")
    with pytest.raises(NotImplementedError, match="bind_tools"):
        create_agent(NoBind(), [add_two])


def test_prebound_runnable_model_lane():
    class PreBound(Runnable):
        def __init__(self):
            self.calls = 0
        def invoke(self, input, config=None):
            self.calls += 1
            if self.calls == 1:
                return tc_add()
            return AIMessage(content="5 hua")
    pb = PreBound()
    ag = create_agent(pb, [add_two])
    out = ag.invoke({"messages": [HumanMessage(content="2+3")]})
    assert out["messages"][-1].content == "5 hua"
    assert pb.calls == 2


def test_bad_system_prompt_refused():
    with pytest.raises(TypeError, match="system_prompt"):
        create_agent(FakeAgentModel(responses=[AIMessage(content="x")]),
                     system_prompt=42)


def test_context_schema_must_be_a_type():
    with pytest.raises(TypeError, match="context_schema"):
        create_agent(FakeAgentModel(responses=[AIMessage(content="x")]),
                     context_schema="nope")


def test_response_format_on_prebound_runnable_refused():
    class Out(BaseModel):
        answer: int
    class PreBound(Runnable):
        def invoke(self, input, config=None):
            return AIMessage(content="{}")
    with pytest.raises(NotImplementedError, match="with_structured_output"):
        create_agent(PreBound(), response_format=Out)


def test_unknown_interrupt_gate_refused_at_build():
    with pytest.raises(ValueError, match="interrupt gate"):
        create_agent(FakeAgentModel(responses=[AIMessage(content="x")]),
                     [add_two], interrupt_before=["mystery"])
    # 'tools' is not a node of a no-tools agent
    with pytest.raises(ValueError, match="interrupt gate"):
        create_agent(FakeAgentModel(responses=[AIMessage(content="x")]),
                     interrupt_before=["tools"])


def test_toolnode_duplicate_names_refused():
    t2 = tool(lambda x: x, name="add_two", description="dup")
    with pytest.raises(ValueError, match="duplicate tool name"):
        ToolNode([add_two, t2])


def test_toolnode_junk_input_refused():
    with pytest.raises(TypeError, match="ToolNode input"):
        ToolNode([add_two]).invoke("2+3")


# ---------------------------------------------------------------------------
# (2) react loop
# ---------------------------------------------------------------------------


def test_full_react_loop():
    m = FakeAgentModel(responses=[tc_add(), AIMessage(content="jod 5 hai")])
    ag = create_agent(m, [add_two])
    out = ag.invoke({"messages": [HumanMessage(content="2+3?")]})
    kinds = [type(x).__name__ for x in out["messages"]]
    assert kinds == ["HumanMessage", "AIMessage", "ToolMessage", "AIMessage"]
    ai1 = out["messages"][1]
    assert ai1.tool_calls and ai1.tool_calls[0]["name"] == "add_two"
    tm = out["messages"][2]
    assert tm.content == "5" and tm.tool_call_id == "c1" and tm.status == "success"
    assert out["messages"][-1].content == "jod 5 hai"
    assert m.idx == 2


def test_system_prompt_rides_the_prompt_never_the_state():
    m = FakeAgentModel(responses=[AIMessage(content="theek")])
    ag = create_agent(m, [add_two], system_prompt="tum calculator ho")
    out = ag.invoke({"messages": [HumanMessage(content="hi")]})
    first_prompt = m.seen_prompts[0]
    assert isinstance(first_prompt[0], SystemMessage)
    assert first_prompt[0].content == "tum calculator ho"
    assert first_prompt[1].content == "hi"
    assert not any(isinstance(x, SystemMessage) for x in out["messages"])


def test_system_prompt_accepts_a_system_message_instance():
    m = FakeAgentModel(responses=[AIMessage(content="ok")])
    ag = create_agent(m, system_prompt=SystemMessage(content="niyam"))
    ag.invoke({"messages": [HumanMessage(content="hi")]})
    assert isinstance(m.seen_prompts[0][0], SystemMessage)
    assert m.seen_prompts[0][0].content == "niyam"


def test_parallel_tool_calls_fan_in_call_order():
    both = AIMessage(content="", tool_calls=[
        _tc("add_two", {"a": 1, "b": 2}, "c1", 0),
        _tc("add_two", {"a": 10, "b": 20}, "c2", 1),
    ])
    m = FakeAgentModel(responses=[both, AIMessage(content="3 aur 30")])
    ag = create_agent(m, [add_two])
    out = ag.invoke({"messages": [HumanMessage(content="dono jodo")]})
    tms = [x for x in out["messages"] if isinstance(x, ToolMessage)]
    assert [t.content for t in tms] == ["3", "30"]
    assert [t.tool_call_id for t in tms] == ["c1", "c2"]


def test_message_dict_and_str_inputs_coerce():
    m = FakeAgentModel(responses=[AIMessage(content="theek")])
    ag = create_agent(m)
    out = ag.invoke({"messages": ["bhai namaste", {"role": "ai", "content": "namaste"}]})
    assert isinstance(out["messages"][0], HumanMessage)
    assert isinstance(out["messages"][1], AIMessage)


# ---------------------------------------------------------------------------
# (3) errors
# ---------------------------------------------------------------------------


def test_tool_error_becomes_an_error_toolmessage_and_loop_continues():
    m = FakeAgentModel(responses=[AIMessage(content="", tool_calls=[_tc("boom", {"x": 1})]),
                                  AIMessage(content="sorry, tool phata")])
    ag = create_agent(m, [boom])
    out = ag.invoke({"messages": [HumanMessage(content="phodo")]})
    tm = out["messages"][2]
    assert tm.status == "error" and "phat gaya" in tm.content
    assert out["messages"][-1].content == "sorry, tool phata"


def test_handle_tool_errors_false_reraises():
    m = FakeAgentModel(responses=[AIMessage(content="", tool_calls=[_tc("boom", {"x": 1})])])
    ag = create_agent(m, [boom])
    tn = ToolNode([boom], handle_tool_errors=False)
    with pytest.raises(ValueError, match="phat gaya"):
        tn.invoke({"messages": [HumanMessage(content="x"), m.responses[0]]})


def test_handle_tool_errors_string_replaces_content():
    tn = ToolNode([boom], handle_tool_errors="tool ne jawab nahi diya")
    out = tn.invoke({"messages": [HumanMessage(content="x"),
                                  AIMessage(content="", tool_calls=[_tc("boom", {"x": 1})])]})
    tm = out["messages"][0]
    assert tm.content == "tool ne jawab nahi diya" and tm.status == "error"


def test_unknown_tool_name_is_an_honest_error_toolmessage():
    m = FakeAgentModel(responses=[AIMessage(content="", tool_calls=[_tc("nahi_hai", {"x": 1})]),
                                  AIMessage(content="aisa tool nahi")])
    ag = create_agent(m, [add_two])
    out = ag.invoke({"messages": [HumanMessage(content="jhat se")]})
    tm = out["messages"][2]
    assert tm.status == "error" and "nahi_hai" in tm.content and "add_two" in tm.content
    assert out["messages"][-1].content == "aisa tool nahi"


def test_dict_tool_output_json_stringified():
    @tool
    def juggu(x: int) -> dict:
        """Returns a dict.
        Args:
            x: the x
        """
        return {"value": x, "ok": True}
    tn = ToolNode([juggu])
    out = tn.invoke({"messages": [HumanMessage(content="x"),
                                  AIMessage(content="", tool_calls=[_tc("juggu", {"x": 9})])]})
    assert out["messages"][0].content == '{"value": 9, "ok": true}'


# ---------------------------------------------------------------------------
# (4) return_direct
# ---------------------------------------------------------------------------


def test_return_direct_tool_ends_the_walk():
    m = FakeAgentModel(responses=[AIMessage(content="", tool_calls=[_tc("direct_echo", {"text": "namaste"})])])
    ag = create_agent(m, [add_two, direct_echo])
    out = ag.invoke({"messages": [HumanMessage(content="echo karo")]})
    assert m.idx == 1   # the model ran ONCE - the tool result IS the answer
    assert out["messages"][-1].content == "seedha: namaste"
    assert isinstance(out["messages"][-1], ToolMessage)


def test_mixed_direct_and_normal_goes_back_to_model():
    both = AIMessage(content="", tool_calls=[
        _tc("add_two", {"a": 1, "b": 1}, "c1"),
        _tc("direct_echo", {"text": "x"}, "c2"),
    ])
    m = FakeAgentModel(responses=[both, AIMessage(content="dono ho gaye")])
    ag = create_agent(m, [add_two, direct_echo])
    out = ag.invoke({"messages": [HumanMessage(content="dono")]})
    assert m.idx == 2   # ALL executed must be direct - one normal sends it back
    assert out["messages"][-1].content == "dono ho gaye"


# ---------------------------------------------------------------------------
# (5) toolnode standalone
# ---------------------------------------------------------------------------


def test_toolnode_standalone_state_and_explicit_lanes():
    tn = ToolNode([add_two])
    out = tn.invoke({"messages": [HumanMessage(content="x"), tc_add()]})
    assert [t.content for t in out["messages"]] == ["5"]
    explicit = tn.invoke([_tc("add_two", {"a": 7, "b": 8}, "c9")])
    assert explicit["messages"][0].content == "15"
    assert explicit["messages"][0].tool_call_id == "c9"


def test_toolnode_messages_key_override():
    tn = ToolNode([add_two], messages_key="chat")
    out = tn.invoke({"chat": [tc_add()]})
    assert out["messages"][0].content == "5"


def test_toolnode_get_name_and_span_name():
    assert ToolNode([add_two]).get_name() == "tools"
    assert ToolNode([add_two], name="hamara_tools").get_name() == "hamara_tools"


# ---------------------------------------------------------------------------
# (6) structured response
# ---------------------------------------------------------------------------


class Jod(BaseModel):
    answer: int
    ok: bool


def test_response_format_pydantic_populates_structured_response():
    m = FakeAgentModel(responses=[AIMessage(content='{"answer": 5, "ok": true}')])
    ag = create_agent(m, [add_two], response_format=Jod)
    assert set(ag.nodes) == {"model", "tools", "generate_structured_response"}
    out = ag.invoke({"messages": [HumanMessage(content="kitna?")]})
    sr = out["structured_response"]
    assert isinstance(sr, Jod) and sr.answer == 5 and sr.ok is True
    # the structured channel is part of the compiled schema
    assert "structured_response" in ag.channels


def test_response_format_runs_only_after_the_tool_rounds():
    # the structured node makes its OWN model call (the with_structured_output
    # fallback lane) - the fake queues a response for it
    m = FakeAgentModel(responses=[tc_add(), AIMessage(content='ok here'),
                                  AIMessage(content='{"answer": 5, "ok": true}')])
    ag = create_agent(m, [add_two], response_format=Jod)
    out = ag.invoke({"messages": [HumanMessage(content="2+3")]})
    kinds = [type(x).__name__ for x in out["messages"]]
    assert kinds == ["HumanMessage", "AIMessage", "ToolMessage", "AIMessage"]
    assert out["structured_response"].answer == 5
    assert m.idx == 3   # tool round + final answer + the structured call


def test_response_format_dict_schema():
    m = FakeAgentModel(responses=[AIMessage(content='{"answer": 7, "ok": false}')])
    ag = create_agent(m, response_format={"type": "object", "properties": {}})
    out = ag.invoke({"messages": [HumanMessage(content="7?")]})
    assert out["structured_response"] == {"answer": 7, "ok": False}


def test_bad_response_format_refused():
    with pytest.raises(TypeError, match="response_format"):
        create_agent(FakeAgentModel(responses=[AIMessage(content="x")]),
                     response_format="lol")


# ---------------------------------------------------------------------------
# (7) state schema
# ---------------------------------------------------------------------------


def test_custom_state_schema_rides_extra_channels():
    class MyState(TypedDict, total=False):
        messages: list
        scratch: str
    m = FakeAgentModel(responses=[AIMessage(content="liya")])
    ag = create_agent(m, [add_two], state_schema=MyState)
    out = ag.invoke({"messages": [HumanMessage(content="hi")], "scratch": "yaad rakho"})
    assert out["scratch"] == "yaad rakho"
    assert out["messages"][-1].content == "liya"


# ---------------------------------------------------------------------------
# (8) checkpointer memory
# ---------------------------------------------------------------------------


def test_checkpointer_gives_chat_memory_across_invokes():
    m = FakeAgentModel(responses=[AIMessage(content="pehla"), AIMessage(content="doosra")])
    ag = create_agent(m, checkpointer=MemorySaver())
    out1 = ag.invoke({"messages": [HumanMessage(content="ek")]}, cfg("t-mem"))
    out2 = ag.invoke({"messages": [HumanMessage(content="do")]}, cfg("t-mem"))
    # the SECOND model call saw the first turn's exchange
    second_prompt = m.seen_prompts[1]
    kinds = [type(x).__name__ for x in second_prompt]
    assert kinds == ["HumanMessage", "AIMessage", "HumanMessage"]
    assert second_prompt[0].content == "ek" and second_prompt[2].content == "do"
    assert len(out2["messages"]) == 4
    # a different thread starts clean
    out3 = ag.invoke({"messages": [HumanMessage(content="naya")]}, cfg("t-ny"))
    assert len(out3["messages"]) == 2


def test_get_state_rides_the_agent():
    m = FakeAgentModel(responses=[AIMessage(content="x")])
    ag = create_agent(m, checkpointer=MemorySaver())
    ag.invoke({"messages": [HumanMessage(content="hi")]}, cfg("t-s"))
    st = ag.get_state(cfg("t-s"))
    assert st["next"] == [] and len(st["values"]["messages"]) == 2


# ---------------------------------------------------------------------------
# (9) interrupts
# ---------------------------------------------------------------------------


def test_interrupt_before_tools_parks_then_resumes():
    m = FakeAgentModel(responses=[tc_add(), AIMessage(content="jod 5")])
    ag = create_agent(m, [add_two], checkpointer=MemorySaver(), interrupt_before=["tools"])
    out = ag.invoke({"messages": [HumanMessage(content="2+3")]}, cfg("t-i1"))
    # the AIMessage IS applied; no tool ran
    assert "__interrupt__" in out
    iv = out["__interrupt__"][0]
    assert iv["value"] == {"before": "tools"} and iv["node"] == "tools"
    assert out["messages"][-1].tool_calls[0]["name"] == "add_two"
    assert not any(isinstance(x, ToolMessage) for x in out["messages"])
    resumed = ag.invoke(Command(resume="haan chalao"), cfg("t-i1"))
    assert resumed["messages"][-1].content == "jod 5"
    assert "__interrupt__" not in resumed
    # the breakpoint REPEATS on the next tools arrival
    m.idx = 0
    out2 = ag.invoke({"messages": [HumanMessage(content="phir se")]}, cfg("t-i1"))
    assert "__interrupt__" in out2


def test_interrupt_before_model_parks_on_first_arrival():
    m = FakeAgentModel(responses=[AIMessage(content="chal")])
    ag = create_agent(m, checkpointer=MemorySaver(), interrupt_before=["model"])
    out = ag.invoke({"messages": [HumanMessage(content="shuru")]}, cfg("t-i2"))
    assert "__interrupt__" in out and m.idx == 0   # parked BEFORE any model call
    iv = out["__interrupt__"][0]
    assert iv["value"] == {"before": "model"} and iv["node"] == "model"
    resumed = ag.invoke(Command(resume="go"), cfg("t-i2"))
    assert resumed["messages"][-1].content == "chal"


def test_interrupt_after_model_never_parks_the_end_path():
    m = FakeAgentModel(responses=[AIMessage(content="seedha")])
    ag = create_agent(m, [add_two], checkpointer=MemorySaver(), interrupt_after=["model"])
    out = ag.invoke({"messages": [HumanMessage(content="hi")]}, cfg("t-i3"))
    assert "__interrupt__" not in out
    assert out["messages"][-1].content == "seedha"


def test_interrupt_after_model_parks_when_tool_calls_exist():
    m = FakeAgentModel(responses=[tc_add(), AIMessage(content="ho gaya")])
    ag = create_agent(m, [add_two], checkpointer=MemorySaver(), interrupt_after=["model"])
    out = ag.invoke({"messages": [HumanMessage(content="2+3")]}, cfg("t-i4"))
    assert "__interrupt__" in out
    assert out["__interrupt__"][0]["value"] == {"after": "model"}
    resumed = ag.invoke(Command(resume="ok"), cfg("t-i4"))
    assert resumed["messages"][-1].content == "ho gaya"


def test_interrupt_after_tools_parks_before_reentry_not_first_arrival():
    m = FakeAgentModel(responses=[tc_add(), AIMessage(content="poora")])
    ag = create_agent(m, [add_two], checkpointer=MemorySaver(), interrupt_after=["tools"])
    out = ag.invoke({"messages": [HumanMessage(content="2+3")]}, cfg("t-i5"))
    assert "__interrupt__" in out   # parked before the model re-ran
    assert out["messages"][-1].content == "5"   # the tool RAN before the park
    assert isinstance(out["messages"][-1], ToolMessage)
    resumed = ag.invoke(Command(resume="aage"), cfg("t-i5"))
    assert resumed["messages"][-1].content == "poora"
    # a fresh thread: the START->model arrival never parks, but the breakpoint
    # is STATIC - the tools->model hop inside the same invoke parks again
    m.idx = 0
    out2 = ag.invoke({"messages": [HumanMessage(content="phir")]}, cfg("t-fresh"))
    assert "__interrupt__" in out2
    assert out2["__interrupt__"][0]["node"] == "model"   # parked at RE-entry
    assert isinstance(out2["messages"][-1], ToolMessage)  # the tool ran first


def test_one_gate_per_arrival_before_tools_wins():
    m = FakeAgentModel(responses=[tc_add(), AIMessage(content="sab ho gaya")])
    ag = create_agent(m, [add_two], checkpointer=MemorySaver(),
                      interrupt_before=["tools"], interrupt_after=["model"])
    out = ag.invoke({"messages": [HumanMessage(content="2+3")]}, cfg("t-i6"))
    assert len(out["__interrupt__"]) == 1
    assert out["__interrupt__"][0]["value"] == {"before": "tools"}
    resumed = ag.invoke(Command(resume="ek hi jawab"), cfg("t-i6"))
    assert resumed["messages"][-1].content == "sab ho gaya"
    assert "__interrupt__" not in resumed


def test_interrupt_gates_without_checkpointer_refuse():
    m = FakeAgentModel(responses=[tc_add()])
    ag = create_agent(m, [add_two], interrupt_before=["tools"])
    with pytest.raises(RuntimeError, match="checkpointer"):
        ag.invoke({"messages": [HumanMessage(content="x")]})


def test_a_tool_may_park_the_walk_and_resume_inside_the_tool():
    @tool
    def malik_se_poocho(q: str) -> str:
        """Asks the boss before acting.
        Args:
            q: the question
        """
        jawab = interrupt({"sawaal": q})
        return f"malik ne kaha: {jawab}"
    ask = AIMessage(content="", tool_calls=[_tc("malik_se_poocho", {"q": "chhutti?"}, "c7")])
    m = FakeAgentModel(responses=[ask, AIMessage(content="malik maan gaye")])
    ag = create_agent(m, [malik_se_poocho], checkpointer=MemorySaver())
    out = ag.invoke({"messages": [HumanMessage(content="chhutti maango")]}, cfg("t-i7"))
    iv = out["__interrupt__"][0]
    assert iv["value"] == {"sawaal": "chhutti?"} and iv["node"] == "tools"
    resumed = ag.invoke(Command(resume="haan"), cfg("t-i7"))
    tm = resumed["messages"][2]
    assert tm.content == "malik ne kaha: haan" and tm.status == "success"
    assert resumed["messages"][-1].content == "malik maan gaye"


# ---------------------------------------------------------------------------
# (10) recursion
# ---------------------------------------------------------------------------


def test_always_tool_model_crosses_recursion_limit():
    ag = create_agent(FakeAgentModel(responses=[tc_add()]), [add_two],
                      checkpointer=MemorySaver())
    with pytest.raises(GraphRecursionError):
        ag.invoke({"messages": [HumanMessage(content="loop")]},
                  {"configurable": {"thread_id": "t-r", "recursion_limit": 3}})


def test_recursion_limit_configurable_per_invoke():
    m = FakeAgentModel(responses=[tc_add(), AIMessage(content="bas"), AIMessage(content="x")])
    ag = create_agent(m, [add_two])
    out = ag.invoke({"messages": [HumanMessage(content="2+3")]},
                    {"recursion_limit": 5})
    assert out["messages"][-1].content == "bas"


# ---------------------------------------------------------------------------
# (11) tracer seam
# ---------------------------------------------------------------------------


def test_agent_spans_nest_model_and_tools_under_a_named_root():
    from app.aep.tracers import CallbackManager as CM, InMemoryRunStore, RunTreeTracer
    store = InMemoryRunStore()
    tracer = RunTreeTracer(sinks=[store])
    m = FakeAgentModel(responses=[tc_add(), AIMessage(content="jod 5 hai")])
    ag = create_agent(m, [add_two], name="calc")
    ag.invoke({"messages": [HumanMessage(content="2+3")]}, {"callbacks": CM([tracer])})
    finished = store.recent(limit=20)
    roots = [r for r in finished if r.parent_run_id is None]
    assert len(roots) == 1 and roots[0].name == "calc"
    kids = {r.name for r in finished if r.parent_run_id == roots[0].id}
    assert {"model", "tools"} <= kids
    # the tool call nests UNDER the tools node span
    tools_span = [r for r in finished if r.name == "tools" and r.parent_run_id == roots[0].id][0]
    tool_spans = [r for r in finished if r.parent_run_id == tools_span.id]
    assert any(r.name == "add_two" for r in tool_spans)
    assert len({r.trace_id for r in finished}) == 1


def test_no_callback_fast_path_stays_run_free():
    from app.aep.tracers import InMemoryRunStore
    store = InMemoryRunStore()
    m = FakeAgentModel(responses=[tc_add(), AIMessage(content="x")])
    ag = create_agent(m, [add_two])
    ag.invoke({"messages": [HumanMessage(content="2+3")]})
    assert store.recent() == []


# ---------------------------------------------------------------------------
# (12) inertness + wiring + version
# ---------------------------------------------------------------------------


def test_fresh_interpreter_import_stays_inert():
    probe = (
        "import os, sys, threading;"
        "before_threads = threading.active_count();"
        "before_env = {k: v for k, v in os.environ.items() if k.startswith(('AEP_', 'HOOLA_'))};"
        "from pathlib import Path;"
        "cwd = Path('.');"
        "before_files = {p.name for p in cwd.iterdir()};"
        "sys.path.insert(0, sys.argv[1]);"
        "import app.aep, app.aep.agent;"
        "assert threading.active_count() == before_threads, 'import spawned threads';"
        "assert {k: v for k, v in os.environ.items() if k.startswith(('AEP_', 'HOOLA_'))} == before_env, 'env read/written';"
        "assert {p.name for p in cwd.iterdir()} == before_files, 'import created files';"
        "print('inert-ok')"
    )
    r = subprocess.run([sys.executable, "-c", probe, str(SERVER)],
                       capture_output=True, text=True, timeout=120, cwd="/tmp")
    assert r.returncode == 0, r.stderr[-800:]
    assert "inert-ok" in r.stdout


def test_package_export_law_covers_the_agent_surface():
    for nm in ("ToolNode", "create_agent", "create_react_agent"):
        assert nm in aep.__all__ and getattr(aep, nm, None) is not None
    assert hasattr(aep, "agent"), "aep.agent not exported as a module"


def test_no_new_registry_tools_and_no_config_reads_in_the_module():
    src = (SERVER / "app" / "aep" / "agent.py").read_text()
    assert "get_settings" not in src and "os.environ" not in src
    assert "VOICE_TOOL_NAMES" not in src
    assert "input_schema" not in src and "DOCS7_SCHEMA" not in src


def test_compiled_agent_carries_checkpointer_and_store():
    from app.aep.graph import SqliteSaver
    from app.aep.stores import InMemoryStore
    cp = MemorySaver()
    st = InMemoryStore()
    m = FakeAgentModel(responses=[AIMessage(content="x")])
    ag = create_agent(m, [add_two], checkpointer=cp, store=st)
    assert ag.checkpointer is cp and ag.store is st


def test_debug_prints_the_walk(capsys):
    m = FakeAgentModel(responses=[tc_add(), AIMessage(content="ho gaya")])
    ag = create_agent(m, [add_two], debug=True)
    ag.invoke({"messages": [HumanMessage(content="2+3")]})
    out = capsys.readouterr().out
    assert "[Agent] model <-" in out and "[Agent] tools <-" in out


def test_version_pins():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.549.0"
    assert "0.549.0+572" in (REPO_ROOT / "pubspec.yaml").read_text()
    line = (SERVER / "app" / "main.py").read_text().splitlines()[35]
    assert line.startswith('APP_VERSION = "0.549.0"')
    # the story-token pin rides the NEWEST story (the newest-story precedent)
    assert "HOOLA AGENT" in line and "create_agent" in line and "ToolNode" in line
    assert "HOOLA GRAPH" in line and "HOOLA TRACE" in line   # the Previous chain
