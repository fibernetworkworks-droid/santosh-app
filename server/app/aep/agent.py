"""HOOLA AEP agent - create_agent (v0.549.0 HOOLA AGENT, P4 of the AEP plan).
The langchain 1.x agents/factory.py idea hand-built on the P3 house graph after
re-reading upstream at the pinned commit aa2528fb980a290d2b06c83a1be43e60bc2348f9
(libs/langchain_v1/langchain/agents/factory.py + the langgraph ToolNode semantics).
ZERO upstream code or imports (the port law that built P1 + P2 + P3).

What lives here:

- ToolNode    : the tool executor - finds the tool_calls on the last AIMessage
                (or takes tool_call dicts directly), runs each tool, returns
                {"messages": [ToolMessage, ...]}. Failures become error
                ToolMessages (handle_tool_errors=True, the upstream default);
                GraphInterrupt/GraphRecursionError propagate (a tool may park
                the walk - the P5 human-in-the-loop seam).
- create_agent: the agent factory - a "model" node wired to a "tools" node in a
                loop: model -> (pending tool_calls ? tools : [structured ? END])
                and tools -> (all return_direct ? END : model). system_prompt
                rides the prompt (never the state); response_format adds the
                generate_structured_response node writing state
                ["structured_response"]; interrupt_before/after are static
                breakpoints built on the P3 interrupt()/Command(resume) seam;
                checkpointer = chat memory across invokes on one thread_id;
                store = cross-thread memory riding config["store"].

Surface notes (honest divergences, the P8 parity audit owns the ledger):
- model strings ("openai:gpt-5.5") need init_chat_model - the P7 HUB; refused
  here with a pointer, never guessed.
- response_format uses the post-loop structured node (the langgraph prebuilt
  shape) writing "structured_response"; upstream 1.x converts schemas into
  structured-output TOOLS / provider strategies - the strategy lane is P8.
- interrupt_after is built as before-node breakpoints on the NEXT node (tools'
  only parent is model, so after-model == before-tools; the tools->model hop is
  detected by a ToolMessage sitting last in state). One gate fires per arrival;
  both a before and an after breakpoint on the same arrival answer with ONE
  park in a fixed order (after checked before before).
- middleware (the 24) is P5; context_schema is accepted and inert until P5.

INERTNESS LAW: a fresh interpreter imports this module with zero threads, zero
env reads, zero files - nothing runs until create_agent builds a graph and the
graph is invoked.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Sequence, get_type_hints

from pydantic import BaseModel

from .graph import (
    END,
    START,
    CompiledStateGraph,
    GraphInterrupt,
    GraphRecursionError,
    StateGraph,
    interrupt,
)
from .messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from .models import BaseChatModel
from .runnable import Runnable, RunnableConfig
from .tools import BaseTool, ToolException, tool as _tool_decorator

__all__ = ["ToolNode", "create_agent", "create_react_agent"]

STRUCTURED_NODE = "generate_structured_response"
MODEL_NODE = "model"
TOOLS_NODE = "tools"


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    try:
        return json.dumps(content, default=str)
    except TypeError:
        return str(content)


def _as_tool(t: Any) -> BaseTool:
    """Tools arrive as BaseTool (used as-is), plain callables (@tool wrapped)
    or nothing else - dict (provider) tools are the P7 HUB's wire problem."""
    if isinstance(t, BaseTool):
        return t
    if callable(t):
        return _tool_decorator(t)
    raise TypeError(
        f"tool {t!r} is not a BaseTool/callable - dict (provider) tools are the "
        "P7 HUB's wire problem")


def _last_ai_and_tools(messages: list[Any]) -> tuple[AIMessage | None, list[ToolMessage]]:
    """The last AIMessage + the ToolMessages after it (upstream _fetch_last_ai_and_tool_messages)."""
    for i in range(len(messages) - 1, -1, -1):
        m = messages[i]
        if isinstance(m, AIMessage):
            return m, [x for x in messages[i + 1:] if isinstance(x, ToolMessage)]
    return None, []


def _pending_tool_calls(last_ai: AIMessage, answered: set[str]) -> list[dict]:
    return [c for c in (last_ai.tool_calls or [])
            if (c.get("id") or "") not in answered]


# ---------------------------------------------------------------------------
# ToolNode
# ---------------------------------------------------------------------------


class ToolNode(Runnable):
    """Executes the pending tool calls of the last AIMessage (or an explicit
    list of tool_call dicts). One node, sequential execution - deterministic
    order, one loop law (upstream fans the calls out via Send; the house walk
    folds them in call order inside one node, the langgraph v0 behavior)."""

    def __init__(self, tools: Sequence[Any], *, name: str = TOOLS_NODE,
                 handle_tool_errors: bool | str = True,
                 messages_key: str = "messages") -> None:
        as_tools = [_as_tool(t) for t in tools]
        self.tools_by_name: dict[str, BaseTool] = {}
        for t in as_tools:
            if t.name in self.tools_by_name:
                raise ValueError(f"duplicate tool name {t.name!r}")
            self.tools_by_name[t.name] = t
        self.name = name
        self.handle_tool_errors = handle_tool_errors
        self.messages_key = messages_key

    def get_name(self, suffix: str | None = None) -> str:
        return f"{self.name}{suffix}" if suffix else self.name

    # -- execution -----------------------------------------------------------

    def _execute(self, call: dict, config: dict | None) -> ToolMessage:
        tcall_id = call.get("id") or ""
        tool_name = call.get("name")
        tl = self.tools_by_name.get(tool_name)
        if tl is None:
            return self._error_out(
                f"Tool {tool_name!r} not found - known tools: "
                f"{sorted(self.tools_by_name) or 'none'}", tcall_id)
        try:
            out = tl.invoke({"type": "tool_call", "name": tool_name,
                             "args": call.get("args") or {}, "id": tcall_id},
                            config)
        except (GraphInterrupt, GraphRecursionError):
            raise   # a tool may park the walk (the P5 HITL seam)
        except Exception as e:  # noqa: BLE001 - the error shape is the contract
            if self.handle_tool_errors is False:
                raise   # the ORIGINAL error, the upstream contract
            return self._error_out(f"Error: {e}", tcall_id)
        if isinstance(out, ToolMessage):
            return out
        return ToolMessage(content=_text(out), tool_call_id=tcall_id)

    def _error_out(self, content: str, tcall_id: str) -> ToolMessage:
        if self.handle_tool_errors is False:
            raise ToolException(content)
        if isinstance(self.handle_tool_errors, str):
            content = self.handle_tool_errors
        return ToolMessage(content=content, tool_call_id=tcall_id, status="error")

    # -- Runnable contract -----------------------------------------------------

    def invoke(self, input: Any, config: RunnableConfig | None = None) -> dict:  # noqa: A002,A003
        if isinstance(input, dict):
            calls = self._calls_from_state(input)
        elif isinstance(input, (list, tuple)):
            calls = list(input)   # the explicit lane: tool_call dicts, pre-fanned
        else:
            raise TypeError(
                f"ToolNode input must be a state dict or a list of tool_calls, "
                f"got {type(input).__name__}")
        msgs = [self._execute(c, config) for c in calls]
        return {"messages": msgs}

    def _calls_from_state(self, state: dict) -> list[dict]:
        messages = state.get(self.messages_key) or []
        last_ai, tool_msgs = _last_ai_and_tools(list(messages))
        if last_ai is None:
            return []
        answered = {t.tool_call_id for t in tool_msgs}
        return _pending_tool_calls(last_ai, answered)


# ---------------------------------------------------------------------------
# create_agent
# ---------------------------------------------------------------------------


def create_agent(
    model: BaseChatModel | Runnable,
    tools: Sequence[Any] | None = None,
    *,
    system_prompt: str | SystemMessage | None = None,
    response_format: type[BaseModel] | dict[str, Any] | None = None,
    state_schema: Any = None,
    context_schema: Any = None,  # noqa: ARG001 - inert until P5 (middleware context)
    checkpointer: Any = None,
    store: Any = None,
    interrupt_before: list[str] | None = None,
    interrupt_after: list[str] | None = None,
    debug: bool = False,
    name: str | None = None,
) -> CompiledStateGraph:
    """The agent loop as a compiled house graph (upstream agents/factory.py:892).

    model     : a BaseChatModel (bind_tools is applied at BUILD time - an
                unsupported model fails at build, never mid-run) or a pre-bound
                Runnable returning AIMessages.
    tools     : BaseTools / callables; None or [] = a model-only agent.
    system_prompt : str or SystemMessage - rides the PROMPT every model call,
                never persisted into state.
    response_format : a pydantic model or dict schema - the final answer is
                re-generated under the schema into state["structured_response"].
    state_schema  : a TypedDict extending AgentState (extra channels ride).
    checkpointer  : chat memory + the interrupt park/resume substrate.
    store         : cross-thread memory riding config["store"].
    interrupt_before/after : static breakpoints on "model"/"tools".
    name      : the compiled graph's display name (the P2 root span's name).
    """
    # -- model lane -----------------------------------------------------------
    if isinstance(model, str):
        raise NotImplementedError(
            "model strings need init_chat_model - the P7 HUB; pass a chat model "
            "instance until then")
    if context_schema is not None and not isinstance(context_schema, type):
        raise TypeError("context_schema must be a type (it wakes up in P5)")
    tool_list = [_as_tool(t) for t in (tools or [])]
    tool_node = ToolNode(tool_list) if tool_list else None
    if isinstance(model, BaseChatModel):
        bound = model.bind_tools(tool_list) if tool_list else model
    elif isinstance(model, Runnable):
        bound = model   # the pre-bound lane: it already carries its tools
    else:
        raise TypeError(
            f"model must be a BaseChatModel or a pre-bound Runnable, "
            f"got {type(model).__name__}")

    # -- system prompt ----------------------------------------------------------
    if system_prompt is None:
        sys_msg: SystemMessage | None = None
    elif isinstance(system_prompt, SystemMessage):
        sys_msg = system_prompt
    elif isinstance(system_prompt, str):
        sys_msg = SystemMessage(content=system_prompt)
    else:
        raise TypeError("system_prompt must be a str or a SystemMessage")

    # -- interrupt breakpoints ----------------------------------------------------
    ib = list(interrupt_before or [])
    ia = list(interrupt_after or [])
    allowed = {MODEL_NODE} | ({TOOLS_NODE} if tool_node else set())
    for gate in ib + ia:
        if gate not in allowed:
            raise ValueError(
                f"interrupt gate {gate!r} is not a node of this agent "
                f"(nodes: {sorted(allowed)})")

    # -- structured response lane ---------------------------------------------------
    struct_schema: type[BaseModel] | dict[str, Any] | None = None
    struct_runner: Runnable | None = None
    if response_format is not None:
        if isinstance(response_format, type) and issubclass(response_format, BaseModel):
            struct_schema = response_format
        elif isinstance(response_format, dict):
            struct_schema = response_format
        else:
            raise TypeError(
                "response_format must be a pydantic model or a dict schema")
        if isinstance(model, BaseChatModel):
            struct_runner = model.with_structured_output(struct_schema)
        else:
            raise NotImplementedError(
                "response_format needs a BaseChatModel (with_structured_output); "
                "pre-bound Runnables bring their own structured lane")

    # -- the compiled schema -------------------------------------------------------
    base = state_schema if state_schema is not None else None
    if base is None:
        from .graph import AgentState
        base = AgentState
    if struct_schema is None:
        schema = base
    else:
        try:
            fields = dict(get_type_hints(base, include_extras=True))
        except Exception:  # noqa: BLE001 - local schemas fall back to raw annotations
            fields = dict(getattr(base, "__annotations__", {}) or {})
        fields["structured_response"] = Any
        from typing import TypedDict as _TD
        schema = _TD("HoolaAgentState", fields, total=False)  # type: ignore[misc]

    # -- nodes -----------------------------------------------------------------------
    agent_name = name or "Agent"

    def model_node(state: dict, config: dict | None = None) -> dict:
        msgs = list(state.get("messages") or [])
        if TOOLS_NODE in ia and msgs and isinstance(msgs[-1], ToolMessage):
            # a ToolMessage last at model entry == the tools->model hop
            interrupt({"after": TOOLS_NODE, "next": MODEL_NODE})
        elif MODEL_NODE in ib:
            interrupt({"before": MODEL_NODE})
        prompt = ([sys_msg] if sys_msg is not None else []) + msgs
        if debug:
            print(f"[{agent_name}] model <- {len(prompt)} messages")
        ai = bound.invoke(prompt, config)
        if debug:
            n = len(getattr(ai, "tool_calls", None) or [])
            print(f"[{agent_name}] model -> {n} tool calls")
        return {"messages": [ai]}

    def tools_gate(state: dict, config: dict | None = None) -> dict:
        if TOOLS_NODE in ib:
            interrupt({"before": TOOLS_NODE})
        elif MODEL_NODE in ia:
            interrupt({"after": MODEL_NODE})
        if debug:
            last_ai, _ = _last_ai_and_tools(list(state.get("messages") or []))
            print(f"[{agent_name}] tools <- {len(last_ai.tool_calls or [])} calls")
        out = tool_node.invoke(state, config)   # type: ignore[union-attr]
        if debug:
            print(f"[{agent_name}] tools -> {len(out.get('messages') or [])} results")
        return out

    def structured_node(state: dict, config: dict | None = None) -> dict:
        msgs = list(state.get("messages") or [])
        prompt = ([sys_msg] if sys_msg is not None else []) + msgs
        if debug:
            print(f"[{agent_name}] structured response ...")
        parsed = struct_runner.invoke(prompt, config)   # type: ignore[union-attr]
        return {"structured_response": parsed}

    # -- routing -----------------------------------------------------------------------
    def route_from_model(state: dict) -> str:
        msgs = list(state.get("messages") or [])
        last_ai, tool_msgs = _last_ai_and_tools(msgs)
        if last_ai is None:
            return STRUCTURED_NODE if struct_runner else END
        answered = {t.tool_call_id for t in tool_msgs}
        if _pending_tool_calls(last_ai, answered):
            return TOOLS_NODE
        return STRUCTURED_NODE if struct_runner else END

    def route_from_tools(state: dict) -> str:
        msgs = list(state.get("messages") or [])
        last_ai, tool_msgs = _last_ai_and_tools(msgs)
        if last_ai is None or tool_node is None:
            return MODEL_NODE
        answered = {t.tool_call_id for t in tool_msgs}
        executed = [tool_node.tools_by_name[c["name"]]
                    for c in last_ai.tool_calls or []
                    if c.get("name") in tool_node.tools_by_name
                    and (c.get("id") or "") in answered]
        if executed and all(t.return_direct for t in executed):
            return END
        return MODEL_NODE

    # -- the graph ------------------------------------------------------------------------
    builder = StateGraph(schema)
    builder.add_node(MODEL_NODE, model_node)
    builder.add_edge(START, MODEL_NODE)
    if tool_node is not None:
        builder.add_node(TOOLS_NODE, tools_gate)
        builder.add_conditional_edges(MODEL_NODE, route_from_model)
        builder.add_conditional_edges(TOOLS_NODE, route_from_tools)
    elif struct_runner is not None:
        builder.add_conditional_edges(MODEL_NODE, route_from_model)
    else:
        builder.add_edge(MODEL_NODE, END)
    if struct_runner is not None:
        builder.add_node(STRUCTURED_NODE, structured_node)
        builder.add_edge(STRUCTURED_NODE, END)
    return builder.compile(checkpointer=checkpointer, store=store, name=agent_name)


create_react_agent = create_agent
"""The langgraph prebuilt alias (upstream create_react_agent now delegates to
create_agent; the house keeps the name for the parity audit)."""
