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
    Command,
    CompiledStateGraph,
    GraphInterrupt,
    GraphRecursionError,
    StateGraph,
    _is_command,
    interrupt,
)
from .messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from .models import BaseChatModel
from .runnable import Runnable, RunnableConfig
from .tools import BaseTool, ToolException, tool as _tool_decorator
from .middleware import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
    ToolCallRequest,
    _async_only,
    _can_jump_to,
    _ephemeral_value,
    _has_hook,
    _normalize_model_result,
)

__all__ = ["ToolNode", "create_agent", "create_react_agent"]

STRUCTURED_NODE = "generate_structured_response"
MODEL_NODE = "model"
TOOLS_NODE = "tools"

AGENT_RECURSION_LIMIT = 9_999
"""The agent's own super-step budget (the upstream factory pins 9_999 - a
middleware chain spends several super-steps per loop iteration; an explicit
cfg recursion_limit still wins)."""


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
    folds them in call order inside one node, the langgraph v0 behavior).
    wrap_tool_call: the composed middleware onion around EACH execution - a
    ToolMessage comes back as-is, a Command(update) merges as extra state."""

    def __init__(self, tools: Sequence[Any], *, name: str = TOOLS_NODE,
                 handle_tool_errors: bool | str = True,
                 messages_key: str = "messages",
                 wrap_tool_call: Any = None) -> None:
        as_tools = [_as_tool(t) for t in tools]
        self.tools_by_name: dict[str, BaseTool] = {}
        for t in as_tools:
            if t.name in self.tools_by_name:
                raise ValueError(f"duplicate tool name {t.name!r}")
            self.tools_by_name[t.name] = t
        self.name = name
        self.handle_tool_errors = handle_tool_errors
        self.messages_key = messages_key
        self.wrap_tool_call = wrap_tool_call

    def get_name(self, suffix: str | None = None) -> str:
        return f"{self.name}{suffix}" if suffix else self.name

    # -- execution -----------------------------------------------------------

    def _run_tool(self, tl: BaseTool, call: dict, config: dict | None,
                  catch: bool = True) -> ToolMessage:
        tcall_id = call.get("id") or ""
        tool_name = call.get("name")
        try:
            out = tl.invoke({"type": "tool_call", "name": tool_name,
                             "args": call.get("args") or {}, "id": tcall_id},
                            config)
        except (GraphInterrupt, GraphRecursionError):
            raise   # a tool may park the walk (the P5 HITL seam)
        except Exception as e:  # noqa: BLE001 - the error shape is the contract
            if not catch:
                raise   # inside a wrap onion the RAW error reaches the middleware
            if self.handle_tool_errors is False:
                raise   # the ORIGINAL error, the upstream contract
            return self._error_out(f"Error: {e}", tcall_id, tool_name)
        if isinstance(out, ToolMessage):
            return out
        return ToolMessage(content=_text(out), tool_call_id=tcall_id, name=tool_name)

    def _execute(self, call: dict, config: dict | None,
                 state: dict | None = None) -> tuple[list[ToolMessage], dict]:
        """One tool call through the wrap onion; returns (messages, extra)."""
        tcall_id = call.get("id") or ""
        tool_name = call.get("name")
        tl = self.tools_by_name.get(tool_name)
        if tl is None:
            if self.wrap_tool_call is not None:
                # the onion still sees unknown-name calls (it may answer them)
                request = ToolCallRequest(tool_call=dict(call), tool=None,
                                          state=dict(state or {}))
                out = self.wrap_tool_call(request, lambda _r: self._error_out(
                    f"Tool {tool_name!r} not found - known tools: "
                    f"{sorted(self.tools_by_name) or 'none'}", tcall_id, tool_name))
                return self._as_wrap_result(out)
            return [self._error_out(
                f"Tool {tool_name!r} not found - known tools: "
                f"{sorted(self.tools_by_name) or 'none'}", tcall_id, tool_name)], {}
        if self.wrap_tool_call is None:
            return [self._run_tool(tl, call, config)], {}
        request = ToolCallRequest(tool_call=dict(call), tool=tl, state=dict(state or {}))
        try:
            out = self.wrap_tool_call(request, lambda req: self._run_tool(
                tl, {**call, "args": (req.tool_call or {}).get("args")}, config,
                catch=False))
        except (GraphInterrupt, GraphRecursionError):
            raise
        except Exception as e:  # noqa: BLE001 - the onion let it through:
            if self.handle_tool_errors is False:
                raise   # the ORIGINAL error, the upstream contract
            return [self._error_out(f"Error: {e}", tcall_id, tool_name)], {}
        return self._as_wrap_result(out)

    def _as_wrap_result(self, out: Any) -> tuple[list[ToolMessage], dict]:
        if _is_command(out):
            upd = dict(out.get("update") or {})
            msgs = [m for m in (upd.pop("messages", None) or []) if isinstance(m, ToolMessage)]
            return msgs, upd
        if isinstance(out, ToolMessage):
            return [out], {}
        raise TypeError(
            f"wrap_tool_call must return a ToolMessage or Command(update), got {type(out).__name__}")

    def _error_out(self, content: str, tcall_id: str,
                   tool_name: str | None = None) -> ToolMessage:
        if self.handle_tool_errors is False:
            raise ToolException(content)
        if isinstance(self.handle_tool_errors, str):
            content = self.handle_tool_errors
        return ToolMessage(content=content, tool_call_id=tcall_id, name=tool_name,
                           status="error")

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
        state = input if isinstance(input, dict) else {}
        msgs: list[ToolMessage] = []
        extra: dict[str, Any] = {}
        for c in calls:
            m, ex = self._execute(c, config, state)
            msgs.extend(m)
            extra.update(ex)
        out: dict[str, Any] = {"messages": msgs}
        out.update(extra)
        return out

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
    context_schema: Any = None,  # noqa: ARG001 - the runtime context type
    middleware: Sequence[Any] | None = None,
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
    middleware : AgentMiddleware instances - the hook taxonomy runs as nodes
                (before_*/after_*) and onions (wrap_*); first in the list is
                the OUTERMOST wrap layer; middleware-declared tools join the
                tool surface; middleware state schemas merge under the base.
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
        raise TypeError("context_schema must be a type (the middleware runtime context)")
    mws = [m for m in (middleware or [])]
    for m in mws:
        if not isinstance(m, AgentMiddleware):
            raise TypeError(
                f"middleware entries must be AgentMiddleware instances, got {m!r}")
    mw_names = [m.name for m in mws]
    if len(set(mw_names)) != len(mw_names):
        raise AssertionError("Please remove duplicate middleware instances.")
    for m in mws:
        for hook in ("before_agent", "before_model", "after_model", "after_agent",
                     "wrap_model_call", "wrap_tool_call"):
            if _async_only(m, hook):
                raise NotImplementedError(
                    f"{m.name!r} defines only the async a{hook} - the house walks run "
                    f"sync hooks on both lanes (via to_thread); implement the sync twin")
    mw_tools = [t for m in mws for t in (m.tools or ())]
    tool_list = [_as_tool(t) for t in (tools or [])] + [_as_tool(t) for t in mw_tools]
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
    # middleware state schemas merge FIRST (registration order, first wins on a
    # conflict), the caller's base schema LAST (it wins over middleware - the
    # upstream _resolve_schemas law); jump_to rides whenever middleware does
    from typing import Annotated as _Ann, TypedDict as _TD
    from .graph import AgentState
    base = state_schema if state_schema is not None else AgentState

    def _schema_fields(s: Any) -> dict[str, Any]:
        if s is None:
            return {}
        if isinstance(s, dict):
            return dict(s)
        try:
            return dict(get_type_hints(s, include_extras=True))
        except Exception:  # noqa: BLE001 - local schemas fall back to raw annotations
            return dict(getattr(s, "__annotations__", {}) or {})

    fields: dict[str, Any] = {}
    for m in mws:
        for k, v in _schema_fields(m.state_schema).items():
            fields.setdefault(k, v)
    for k, v in _schema_fields(base).items():
        fields[k] = v
    if mws:
        fields["jump_to"] = _Ann[Any, _ephemeral_value]
    if struct_schema is not None:
        fields["structured_response"] = Any
    if struct_schema is not None or mws:
        schema = _TD("HoolaAgentState", fields, total=False)  # type: ignore[misc]
    else:
        schema = base

    # -- the wrap onions ------------------------------------------------------------
    mw_wrap_model = [m for m in mws if _has_hook(m, "wrap_model_call")]
    mw_wrap_tool = [m for m in mws if _has_hook(m, "wrap_tool_call")]

    def _inner_model_call(req: ModelRequest, cfg: dict | None) -> ModelResponse:
        m2 = req.model
        msgs = ([req.system_message] if req.system_message is not None else []) + list(req.messages)
        if isinstance(m2, BaseChatModel):
            if m2 is model:
                runner = bound   # the build-time model rides its build-time binding
            else:
                # a wrap swapped the model (the fallback lane) - bind per call
                runner = m2.bind_tools(list(req.tools)) if req.tools else m2
        else:
            runner = m2
        ai = runner.invoke(msgs, cfg)
        return ModelResponse(result=[ai])

    def _run_model_onion(request: ModelRequest, cfg: dict | None) -> Any:
        handlers = [m.wrap_model_call for m in mw_wrap_model]  # first = OUTERMOST

        def go(i: int, req: ModelRequest) -> Any:
            if i == len(handlers):
                return _inner_model_call(req, cfg)
            return handlers[i](req, lambda r, _i=i + 1: go(_i, r))

        return go(0, request)

    # -- nodes -----------------------------------------------------------------------
    agent_name = name or "Agent"

    def model_node(state: dict, config: dict | None = None) -> dict:
        msgs = list(state.get("messages") or [])
        if TOOLS_NODE in ia and msgs and isinstance(msgs[-1], ToolMessage):
            # a ToolMessage last at model entry == the tools->model hop
            interrupt({"after": TOOLS_NODE, "next": MODEL_NODE})
        elif MODEL_NODE in ib:
            interrupt({"before": MODEL_NODE})
        if not mws:   # the P4 fast path - untouched behavior, no request object
            prompt = ([sys_msg] if sys_msg is not None else []) + msgs
            if debug:
                print(f"[{agent_name}] model <- {len(prompt)} messages")
            ai = bound.invoke(prompt, config)
            if debug:
                n = len(getattr(ai, "tool_calls", None) or [])
                print(f"[{agent_name}] model -> {n} tool calls")
            return {"messages": [ai]}
        runtime = {"config": config, "store": (config or {}).get("store"),
                   "context": None, "agent": agent_name}
        request = ModelRequest(
            model=model, messages=msgs, system_message=sys_msg,
            tool_choice=None, tools=list(tool_list) if tool_list else [],
            response_format=struct_schema, state=state, runtime=runtime)
        if debug:
            print(f"[{agent_name}] model <- {len(msgs)} messages "
                  f"(+{len(mw_wrap_model)} wrap layers)")
        resp, extra = _normalize_model_result(_run_model_onion(request, config))
        if debug:
            n = sum(len(getattr(m, "tool_calls", None) or []) for m in resp.result)
            print(f"[{agent_name}] model -> {n} tool calls")
        out: dict[str, Any] = {"messages": list(resp.result)}
        if resp.structured_response is not None:
            out["structured_response"] = resp.structured_response
        out.update(extra)
        return out

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

    # -- the middleware hook nodes ------------------------------------------------------
    def _make_hook_node(m: Any, hook: str):
        def node(state: dict, config: dict | None = None) -> dict:
            runtime = {"config": config, "store": (config or {}).get("store"),
                       "context": None, "agent": agent_name}
            out = getattr(m, hook)(state, runtime)
            if out is None:
                return {}
            if isinstance(out, Command):
                raise NotImplementedError(
                    "Command goto/resume is not yet supported in middleware hooks. "
                    "Use the jump_to state field with before_model/after_model hooks.")
            if not isinstance(out, dict):
                raise TypeError(
                    f"{m.name}.{hook} returned {type(out).__name__} - hooks return a "
                    "state-update dict or None")
            if "jump_to" in out and not _can_jump_to(m, hook):
                # an undeclared jump is consumed and ignored (the house rule)
                out = {k: v for k, v in out.items() if k != "jump_to"}
            return out
        node.__name__ = f"{m.name}_{hook}"
        return node

    def _resolve_jump(jump: Any) -> str | None:
        if jump == "model":
            return loop_entry
        if jump == "end":
            return exit_node
        if jump == "tools":
            return TOOLS_NODE
        return None

    def _add_mw_edge(builder: StateGraph, m: Any, hook: str, *,
                     default: str, model_destination: str, end_destination: str) -> None:
        _wire_mw_edge(builder, m, hook, default=default,
                      model_destination=model_destination,
                      end_destination=end_destination, resolve=_resolve_jump,
                      tools_present=TOOLS_NODE in builder._nodes)

    # -- routing -----------------------------------------------------------------------
    def route_after_model(state: dict) -> str:
        jump = _resolve_jump(state.get("jump_to"))
        if jump is not None:
            return jump
        msgs = list(state.get("messages") or [])
        last_ai, tool_msgs = _last_ai_and_tools(msgs)
        if last_ai is None:
            return STRUCTURED_NODE if struct_runner else exit_node
        answered = {t.tool_call_id for t in tool_msgs}
        if _pending_tool_calls(last_ai, answered):
            return TOOLS_NODE
        if last_ai.tool_calls:
            # upstream rule 6: calls exist but ALL are answered (middleware
            # injected artificial tool results) - the model sees them next
            return loop_entry
        return STRUCTURED_NODE if struct_runner else exit_node

    def route_from_tools(state: dict) -> str:
        msgs = list(state.get("messages") or [])
        last_ai, tool_msgs = _last_ai_and_tools(msgs)
        if last_ai is None or tool_node is None:
            return loop_entry
        answered = {t.tool_call_id for t in tool_msgs}
        executed = [tool_node.tools_by_name[c["name"]]
                    for c in last_ai.tool_calls or []
                    if c.get("name") in tool_node.tools_by_name
                    and (c.get("id") or "") in answered]
        if executed and all(t.return_direct for t in executed):
            return exit_node
        return loop_entry

    # -- the graph ------------------------------------------------------------------------
    builder = StateGraph(schema)
    builder.add_node(MODEL_NODE, model_node)
    if tool_node is not None:
        builder.add_node(TOOLS_NODE, tools_gate)
    if struct_runner is not None:
        builder.add_node(STRUCTURED_NODE, structured_node)

    mw_before_agent = [m for m in mws if _has_hook(m, "before_agent")]
    mw_before_model = [m for m in mws if _has_hook(m, "before_model")]
    mw_after_model = [m for m in mws if _has_hook(m, "after_model")]
    mw_after_agent = [m for m in mws if _has_hook(m, "after_agent")]
    for m in mws:
        for hook in ("before_agent", "before_model", "after_model", "after_agent"):
            if _has_hook(m, hook):
                builder.add_node(f"{m.name}.{hook}", _make_hook_node(m, hook))

    loop_entry = f"{mw_before_model[0].name}.before_model" if mw_before_model else MODEL_NODE
    exit_node = f"{mw_after_agent[-1].name}.after_agent" if mw_after_agent else END
    loop_exit = f"{mw_after_model[0].name}.after_model" if mw_after_model else MODEL_NODE

    entry_node = f"{mw_before_agent[0].name}.before_agent" if mw_before_agent else loop_entry
    builder.add_edge(START, entry_node)

    if tool_node is not None:
        builder.add_conditional_edges(loop_exit, route_after_model)
        builder.add_conditional_edges(TOOLS_NODE, route_from_tools)
    elif struct_runner is not None:
        builder.add_conditional_edges(loop_exit, route_after_model)
    elif mw_after_model:
        def route_after_model_no_tools(state: dict) -> str:
            jump = _resolve_jump(state.get("jump_to"))
            if jump is not None and jump != TOOLS_NODE:
                return jump
            return exit_node
        builder.add_conditional_edges(loop_exit, route_after_model_no_tools)
    else:
        builder.add_edge(loop_exit, exit_node)
    if struct_runner is not None:
        builder.add_edge(STRUCTURED_NODE, exit_node)

    # before_agent chain (registration order), the last one enters the loop
    _chain_edges(mw_before_agent, "before_agent", builder, loop_entry, exit_node, tail_default=loop_entry, resolve=_resolve_jump, tools_present=TOOLS_NODE in builder._nodes)

    # before_model chain (registration order), the last one calls the model
    _chain_edges(mw_before_model, "before_model", builder, loop_entry, exit_node, tail_default=MODEL_NODE, resolve=_resolve_jump, tools_present=TOOLS_NODE in builder._nodes)

    # after_model chain (REVERSE registration order - the upstream law):
    # model -> last.after_model -> ... -> first.after_model (= the loop exit)
    if mw_after_model:
        builder.add_edge(MODEL_NODE, f"{mw_after_model[-1].name}.after_model")
        _chain_edges(list(reversed(mw_after_model)), "after_model", builder,
                     loop_entry, exit_node, tail_default=None, resolve=_resolve_jump,
                     tools_present=TOOLS_NODE in builder._nodes)

    # after_agent chain (REVERSE registration order): the walk exits INTO
    # exit_node (= last.after_agent) and unwinds to first.after_agent -> END
    if mw_after_agent:
        _chain_edges(list(reversed(mw_after_agent)), "after_agent", builder,
                     loop_entry, exit_node, tail_default=END, resolve=_resolve_jump,
                     tools_present=TOOLS_NODE in builder._nodes)

    # the tool-wrap onion rides the ToolNode (first middleware = outermost)
    if tool_node is not None and mw_wrap_tool:
        tool_node.wrap_tool_call = _compose_tool_onion(mw_wrap_tool)

    compiled = builder.compile(checkpointer=checkpointer, store=store, name=agent_name)
    compiled.default_limit = AGENT_RECURSION_LIMIT
    return compiled


def _wire_mw_edge(builder: StateGraph, m: Any, hook: str, *, default: str,
                  model_destination: str, end_destination: str,
                  resolve: Callable, tools_present: bool) -> None:
    """One middleware edge: static when the hook declares no jumps, else a
    conditional that resolves state['jump_to'] (model/tools/end) first."""
    can = _can_jump_to(m, hook)
    name = f"{m.name}.{hook}"
    if "tools" in can and not tools_present:
        raise ValueError(
            f"{name} declares can_jump_to ['tools'] but this agent has no tools node")
    if not can:
        builder.add_edge(name, default)
        return

    def jump_edge(state: dict, _default: str = default) -> str:
        return resolve(state.get("jump_to")) or _default

    builder.add_conditional_edges(name, jump_edge)


def _chain_edges(chain: list[Any], hook: str, builder: StateGraph,
                 loop_entry: str, exit_node: str, *, tail_default: str | None,
                 resolve: Callable, tools_present: bool) -> None:
    """Wire a middleware chain: m[i] -> m[i+1] (jump-aware), the last node to
    tail_default."""
    for m1, m2 in zip(chain, chain[1:]):
        _wire_mw_edge(builder, m1, hook, default=f"{m2.name}.{hook}",
                      model_destination=loop_entry, end_destination=exit_node,
                      resolve=resolve, tools_present=tools_present)
    if chain and tail_default is not None:
        _wire_mw_edge(builder, chain[-1], hook, default=tail_default,
                      model_destination=loop_entry, end_destination=exit_node,
                      resolve=resolve, tools_present=tools_present)


def _compose_tool_onion(mws: list[Any]):
    """first in the middleware list = OUTERMOST tool wrapper."""
    def composed(request: ToolCallRequest, handler: Callable[[ToolCallRequest], Any]) -> Any:
        def go(i: int, req: ToolCallRequest) -> Any:
            if i == len(mws):
                return handler(req)
            return mws[i].wrap_tool_call(req, lambda r, _i=i + 1: go(_i, r))
        return go(0, request)
    return composed


create_react_agent = create_agent
"""The langgraph prebuilt alias (upstream create_react_agent now delegates to
create_agent; the house keeps the name for the parity audit)."""
