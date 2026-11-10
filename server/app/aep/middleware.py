"""HOOLA AEP middleware - the 24 (v0.559.0 HOOLA MIDDLEWARE, P5 of the AEP plan).
The langchain 1.x agents/middleware idea hand-built on the P4 create_agent after
re-reading upstream at the pinned commit aa2528fb980a290d2b06c83a1be43e60bc2348f9
(libs/langchain_v1/langchain/agents/middleware/types.py + the tier modules).
ZERO upstream code or imports (the port law that built P1 + P2 + P3 + P4).

What lives here:

THE HOOK TAXONOMY (types.py):
- AgentMiddleware: the base class - before_agent / before_model / after_model /
  after_agent (state hooks returning state updates) + wrap_model_call /
  wrap_tool_call (onion wrappers around ONE model call / ONE tool execution) +
  the a-* twins (honest NotImplementedError in the base - the house walks run
  sync hooks on both lanes via to_thread; an async-only hook is refused at
  build, never mid-run) + name / tools / state_schema / transformers.
- ModelRequest: what a model call is ABOUT to be - model, messages, system_message,
  tool_choice, tools, response_format, state, runtime, model_settings - and
  .override(**kw): the immutable replace (direct attribute writes refused with
  the override() pointer).
- ModelResponse / ExtendedModelResponse: what came back - result messages +
  structured_response; the Extended form carries a Command(update) applied as an
  extra state update (goto/resume/graph refused - the upstream wording).
- ToolCallRequest: one tool execution - tool_call dict, tool, state, runtime.
- jump_to: a hook may return {"jump_to": "model" | "tools" | "end"} to reroute
  the loop; DECLARED per hook via hook_config(can_jump_to=[...]) - undeclared
  jumps are consumed and ignored (the honest house rule; upstream leaks them).
  The channel is ephemeral (cleared after every routing pass) so one hook fires
  one gate per arrival.
- the decorators (@before_model / @after_model / @before_agent / @after_agent /
  @wrap_model_call / @wrap_tool_call / @dynamic_prompt): a bare function becomes
  a one-hook middleware.

THE MIDDLEWARES IN TIERS (one class each, upstream semantics):
- SummarizationMiddleware : token-threshold history summarization (trigger
  clauses tokens/messages/fraction, keep policy messages/tokens/fraction, the
  AI/Tool pairs never split, the summary model retried 3x, the overflow
  middle-cut fallback when the summarizer itself fails).
- PIIMiddleware           : email / credit_card (Luhn) / ip / mac_address / url
  detectors + custom regex/callable; strategies block / redact / mask / hash;
  input (before_model) / output (after_model) / tool-results lanes + the live
  stream transformer (redaction in flight, not just at rest).
- ModelCallLimitMiddleware: thread/run model-call counters; exit end (jump with
  an honest AI message) or error (ModelCallLimitExceededError).
- ToolCallLimitMiddleware : per-tool-name thread/run counters; continue (error
  ToolMessages for the blocked calls), end (every pending call answered + jump)
  or error.
- ModelRetryMiddleware    : wrap_model_call retry with backoff + jitter;
  retry_on tuple/callable; on_failure error / continue (an honest AI message).
- ModelFallbackMiddleware : wrap_model_call fallback chain (primary then the
  fallbacks in order; interrupt/recursion propagate; all fail = last error).
- ToolErrorMiddleware     : wrap_tool_call - a selected exception becomes an
  error ToolMessage (on_error(exc, request) -> content; None re-raises).
- ToolRetryMiddleware     : wrap_tool_call retry with backoff; continue = error
  ToolMessage, error = re-raise.
- LLMToolEmulator         : wrap_tool_call - selected tools answered by an
  emulator model instead of executing (the emulation call is tagged internal).
- HumanInTheLoopMiddleware: after_model - gated tool calls park the walk on the
  P3 interrupt() seam with one HITLRequest; decisions approve / edit / reject /
  respond; edited args ride the private channel into the tool execution.
- TodoListMiddleware      : the write_todos tool + a todos channel + the system
  prompt rider.
- ContextEditingMiddleware: ClearToolUsesEdit - old tool outputs become
  placeholders past a token trigger (keep the newest N, exclude tools, optional
  input clearing), marked in response_metadata.
- FilesystemFileSearchMiddleware: glob + grep tools over a root path (stdlib
  pathlib/re, a size cap; ripgrep when present).
- ProviderToolSearchMiddleware: marks selected tools deferred behind provider
  server-side search - the house honest form: validated + tagged on the
  request, the provider wire itself is the P7 HUB's ledger.
- ShellToolMiddleware     : one bounded shell tool (subprocess, timeout, output
  cap, cwd, env override) - voice never sees it (the VOICE_TOOL_NAMES law).

THE UNIFICATION (nudge/curator/delegate/skills-primer collapse into hooks):
- NudgeMiddleware         : the house nudge as a before_model/wrap_model_call
  rider - a steering note joins the system message (her words stay hers).
- CuratorMiddleware       : the house curator as an after_agent fold - duplicate
  tool noise collapses, the lane is capped, folds are marked.
- DelegateMiddleware      : the house delegate_task as a middleware-registered
  tool + depth cap - one tool, N task prompts, bounded children, fail-open.
- SkillsPrimerMiddleware  : the house skills primer as a wrap_model_call rider -
  name/keyword-matched skill text joins the system message (hers win).

Honest divergences (the P8 parity audit owns the ledger):
- async-only hooks are refused at build (the house walks run sync hooks on both
  lanes); the a-* hook twins exist on the taxonomy and raise the upstream
  wording when only they are defined.
- response_format's structured node stays the P4 post-loop shape; a
  wrap_model_call override of response_format is honored on the request but the
  structured node still parses with the build-time runner.
- model_refusal / tool_selection / the private _trace_policy / _execution
  modules are the P8 audit's remaining ledger rows.

INERTNESS LAW: a fresh interpreter imports this module with zero threads, zero
env reads, zero files - the detectors compile regexes at import (no I/O) and
nothing else runs until a middleware is built and an agent invoked.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import subprocess
import time
import uuid
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Annotated, Any, Callable, Generic, Literal, TypeVar

from pydantic import BaseModel

from .graph import GraphInterrupt, GraphRecursionError, interrupt
from .messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    ToolMessage,
)
from .models import BaseChatModel
from .tools import BaseTool, tool as _tool_decorator

__all__ = [
    "AgentMiddleware",
    "ModelRequest",
    "ModelResponse",
    "ExtendedModelResponse",
    "ToolCallRequest",
    "hook_config",
    "before_agent",
    "before_model",
    "after_model",
    "after_agent",
    "wrap_model_call",
    "wrap_tool_call",
    "dynamic_prompt",
    "default_retry_on",
    "internal_call_metadata",
    "INTERNAL_CALL_METADATA_KEY",
    "SummarizationMiddleware",
    "PIIMiddleware",
    "PIIDetectionError",
    "ModelCallLimitMiddleware",
    "ModelCallLimitExceededError",
    "ToolCallLimitMiddleware",
    "ToolCallLimitExceededError",
    "ModelRetryMiddleware",
    "ModelFallbackMiddleware",
    "ToolErrorMiddleware",
    "ToolRetryMiddleware",
    "LLMToolEmulator",
    "HumanInTheLoopMiddleware",
    "TodoListMiddleware",
    "ContextEditingMiddleware",
    "ClearToolUsesEdit",
    "FilesystemFileSearchMiddleware",
    "ProviderToolSearchMiddleware",
    "ShellToolMiddleware",
    "NudgeMiddleware",
    "CuratorMiddleware",
    "DelegateMiddleware",
    "SkillsPrimerMiddleware",
]

ContextT = TypeVar("ContextT")
ResponseT = TypeVar("ResponseT")

JumpTo = Literal["tools", "model", "end"]

_EDITED_TOOL_CALLS_KEY = "hitl_edited_tool_calls"
EDITED_RESULT_PREFIX = "The reviewer edited the tool call before it ran. Result: "


# ---------------------------------------------------------------------------
# the shared lane helpers
# ---------------------------------------------------------------------------


def _ensure_ids(messages: list[Any]) -> list[Any]:
    """Ensure every message carries a unique id (the add_messages replace-by-id
    lane needs it; the summarization/HITL/curator rewrites rely on it)."""
    for m in messages:
        if isinstance(m, BaseMessage) and not getattr(m, "id", None):
            m.id = str(uuid.uuid4())
    return messages


def _rewrite_messages(messages: list[Any], mutate: Callable[[list[Any]], list[Any]] | None = None) -> list[Any]:
    """Return an update that rebuilds the whole messages lane: RemoveMessage
    (REMOVE_ALL) + the id-ensured (optionally mutated) list - the deterministic
    rewrite the lane-level middlewares share."""
    working = list(messages)
    if mutate is not None:
        working = mutate(working)
    return [RemoveMessage(id="remove_all"), *_ensure_ids(working)]


def _text_of(content: Any) -> str:
    if isinstance(content, str):
        return content
    try:
        return json.dumps(content, default=str)
    except TypeError:
        return str(content)


def _last_ai(messages: list[Any]) -> AIMessage | None:
    for m in reversed(messages):
        if isinstance(m, AIMessage):
            return m
    return None


# ---------------------------------------------------------------------------
# the untracked / ephemeral channel markers (the graph seam P5 needs)
# ---------------------------------------------------------------------------


def _untracked_value(left: Any, right: Any) -> Any:  # noqa: ARG001 - last value wins
    """Reducer for run-scoped channels: last value wins, and the graph strips
    the channel from checkpoints (the upstream UntrackedValue semantics - a run
    counter restarts every invoke even on a checkpointed thread)."""
    return right


_untracked_value.untracked = True  # type: ignore[attr-defined]


def _ephemeral_value(left: Any, right: Any) -> Any:  # noqa: ARG001
    """Reducer for jump_to: last value wins, untracked, AND the walk clears the
    channel after every routing pass (the upstream EphemeralValue semantics -
    one jump, one gate, no stale reroutes)."""
    return right


_ephemeral_value.untracked = True  # type: ignore[attr-defined]
_ephemeral_value.ephemeral = True  # type: ignore[attr-defined]


class MiddlewareState(dict):  # noqa: FURB189 - a marker type only
    """Marker base for middleware state schemas (documentation shape only; the
    house schemas are plain TypedDicts)."""


# ---------------------------------------------------------------------------
# ModelRequest / ModelResponse - the wrap lane's contract
# ---------------------------------------------------------------------------

_MODEL_REQUEST_KEYS = {
    "model", "messages", "system_message", "system_prompt", "tool_choice",
    "tools", "response_format", "state", "runtime", "model_settings",
}


@dataclass(init=False)
class ModelRequest:
    """What a model call is about to be (the upstream ModelRequest shape):
    everything wrap_model_call may inspect and .override()."""

    model: Any
    messages: list[Any]
    system_message: SystemMessage | None
    tool_choice: Any | None
    tools: list[Any] | None
    response_format: Any | None
    state: dict[str, Any]
    runtime: dict[str, Any]
    model_settings: dict[str, Any]

    def __init__(
        self,
        *,
        model: Any,
        messages: list[Any],
        system_message: SystemMessage | None = None,
        system_prompt: str | None = None,
        tool_choice: Any | None = None,
        tools: list[Any] | None = None,
        response_format: Any | None = None,
        state: dict[str, Any] | None = None,
        runtime: dict[str, Any] | None = None,
        model_settings: dict[str, Any] | None = None,
    ) -> None:
        if system_prompt is not None and system_message is not None:
            raise ValueError("Cannot specify both system_prompt and system_message")
        if system_prompt is not None:
            system_message = SystemMessage(content=system_prompt)
        object.__setattr__(self, "model", model)
        object.__setattr__(self, "messages", list(messages or []))
        object.__setattr__(self, "system_message", system_message)
        object.__setattr__(self, "tool_choice", tool_choice)
        object.__setattr__(self, "tools", list(tools) if tools is not None else None)
        object.__setattr__(self, "response_format", response_format)
        object.__setattr__(self, "state", state if state is not None else {"messages": []})
        object.__setattr__(self, "runtime", runtime if runtime is not None else {})
        object.__setattr__(self, "model_settings", model_settings or {})

    @property
    def system_prompt(self) -> str | None:
        return None if self.system_message is None else self.system_message.text

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(
            f"Direct attribute assignment to ModelRequest.{name} is not supported. "
            f"Use request.override({name}=...) instead to create a new request "
            "with the modified attribute.")

    def override(self, **overrides: Any) -> "ModelRequest":
        """Replace attributes immutably (the upstream law): returns a NEW
        ModelRequest with the given keys replaced; system_prompt converts."""
        bad = set(overrides) - _MODEL_REQUEST_KEYS
        if bad:
            raise ValueError(
                f"Unknown override keys {sorted(bad)} - allowed: {sorted(_MODEL_REQUEST_KEYS)}")
        if "system_prompt" in overrides and "system_message" in overrides:
            raise ValueError("Cannot specify both system_prompt and system_message")
        if "system_prompt" in overrides:
            sp = overrides.pop("system_prompt")
            overrides["system_message"] = None if sp is None else SystemMessage(content=sp)
        return replace(self, **overrides)


@dataclass
class ModelResponse(Generic[ResponseT]):
    """What a model call returned: the result messages + optional structured."""

    result: list[BaseMessage]
    structured_response: ResponseT | None = None


@dataclass
class ExtendedModelResponse(Generic[ResponseT]):
    """A model response plus a Command(update) applied as an EXTRA state update
    after the model node completes (messages ride the reducers alongside)."""

    model_response: ModelResponse[ResponseT]
    command: Any | None = None


def _normalize_model_result(out: Any) -> tuple[ModelResponse, dict[str, Any]]:
    """Accept ModelResponse | AIMessage | ExtendedModelResponse from a wrap
    handler; return (response, extra_update)."""
    if isinstance(out, ExtendedModelResponse):
        cmd = out.command
        if cmd is not None:
            goto = cmd.get("goto") or cmd.get("resume") or cmd.get("graph")
            if goto:
                raise NotImplementedError(
                    "Command goto/resume/graph is not yet supported in "
                    "wrap_model_call middleware. Use the jump_to state field "
                    "with before_model/after_model hooks instead.")
        resp, extra = out.model_response, dict(cmd.get("update") or {})
        return resp, extra
    if isinstance(out, ModelResponse):
        return out, {}
    if isinstance(out, BaseMessage):
        return ModelResponse(result=[out]), {}
    raise TypeError(
        f"a model-call handler must return ModelResponse / AIMessage / "
        f"ExtendedModelResponse, got {type(out).__name__}")


# ---------------------------------------------------------------------------
# ToolCallRequest - the wrap_tool_call contract
# ---------------------------------------------------------------------------


@dataclass
class ToolCallRequest:
    """One tool execution as wrap_tool_call sees it."""

    tool_call: dict[str, Any]
    tool: BaseTool | None
    state: dict[str, Any]
    runtime: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# AgentMiddleware - the hook taxonomy
# ---------------------------------------------------------------------------


def hook_config(can_jump_to: list[JumpTo] | None = None):
    """Decorator marking a before_*/after_* hook with its jump destinations."""

    def deco(fn: Callable) -> Callable:
        fn.__can_jump_to__ = list(can_jump_to or [])
        return fn

    return deco


def _can_jump_to(middleware: "AgentMiddleware", hook_name: str) -> list[JumpTo]:
    for name in (hook_name, "a" + hook_name):
        fn = getattr(type(middleware), name, None)
        target = getattr(fn, "__func__", fn)   # unwrap staticmethod
        if target is not None and hasattr(target, "__can_jump_to__"):
            return list(target.__can_jump_to__)
    return []


class AgentMiddleware(Generic[ContextT, ResponseT]):
    """Base middleware class: subclass and implement any hook to customize the
    one agent loop (the upstream AgentMiddleware shape, hand-built).

    Hooks (each returns a state-update dict or None, except the wraps):
      before_agent / after_agent  - once per agent invocation
      before_model / after_model  - around every model call inside the loop
      wrap_model_call(request, handler)  - the onion around ONE model call
      wrap_tool_call(request, handler)   - the onion around ONE tool execution
    """

    state_schema: Any = None
    tools: Any = ()
    transformers: Any = ()

    @property
    def name(self) -> str:
        return type(self).__name__

    # -- state hooks ----------------------------------------------------------

    def before_agent(self, state: dict, runtime: dict) -> dict | None:  # noqa: ARG002
        return None

    def before_model(self, state: dict, runtime: dict) -> dict | None:  # noqa: ARG002
        return None

    def after_model(self, state: dict, runtime: dict) -> dict | None:  # noqa: ARG002
        return None

    def after_agent(self, state: dict, runtime: dict) -> dict | None:  # noqa: ARG002
        return None

    async def abefore_agent(self, state: dict, runtime: dict) -> dict | None:  # noqa: ARG002
        return None

    async def abefore_model(self, state: dict, runtime: dict) -> dict | None:  # noqa: ARG002
        return None

    async def aafter_model(self, state: dict, runtime: dict) -> dict | None:  # noqa: ARG002
        return None

    async def aafter_agent(self, state: dict, runtime: dict) -> dict | None:  # noqa: ARG002
        return None

    # -- wrap hooks ------------------------------------------------------------

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Any],
    ) -> Any:  # noqa: ARG002
        msg = (
            "Synchronous implementation of wrap_model_call is not available. "
            "You are likely encountering this error because you defined only the "
            "async version (awrap_model_call) and invoked your agent in a "
            "synchronous context. To resolve this, either: (1) subclass "
            "AgentMiddleware and implement the synchronous wrap_model_call method, "
            "(2) use the @wrap_model_call decorator on a standalone sync function, "
            "or (3) invoke your agent asynchronously.")
        raise NotImplementedError(msg)

    async def awrap_model_call(self, request: ModelRequest, handler: Any) -> Any:  # noqa: ARG002
        msg = (
            "Asynchronous implementation of awrap_model_call is not available. "
            "You are likely encountering this error because you defined only the "
            "sync version (wrap_model_call) and invoked your agent in an "
            "asynchronous context. To resolve this, either: (1) subclass "
            "AgentMiddleware and implement the asynchronous awrap_model_call "
            "method, (2) use the @wrap_model_call decorator on a standalone async "
            "function, or (3) invoke your agent synchronously.")
        raise NotImplementedError(msg)

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage],
    ) -> ToolMessage | Any:  # noqa: ARG002
        msg = (
            "Synchronous implementation of wrap_tool_call is not available. "
            "You are likely encountering this error because you defined only the "
            "async version (awrap_tool_call). Subclass AgentMiddleware and "
            "implement the synchronous wrap_tool_call method, or use the "
            "@wrap_tool_call decorator on a standalone sync function.")
        raise NotImplementedError(msg)

    async def awrap_tool_call(self, request: ToolCallRequest, handler: Any) -> Any:  # noqa: ARG002
        msg = (
            "Asynchronous implementation of awrap_tool_call is not available. "
            "You are likely encountering this error because you defined only the "
            "sync version (wrap_tool_call). Subclass AgentMiddleware and implement "
            "the asynchronous awrap_tool_call method, or use the @wrap_tool_call "
            "decorator on a standalone async function.")
        raise NotImplementedError(msg)


def _has_hook(m: AgentMiddleware, hook: str) -> bool:
    return getattr(type(m), hook) is not getattr(AgentMiddleware, hook)


def _async_only(m: AgentMiddleware, hook: str) -> bool:
    """The a-hook defined while its sync twin is not - the house refuses it at
    build (an async-only handler cannot run under a sync walk)."""
    return _has_hook(m, "a" + hook) and not _has_hook(m, hook)


# ---------------------------------------------------------------------------
# the function decorators - a bare callable becomes a one-hook middleware
# ---------------------------------------------------------------------------


def _make_single_hook_mw(fn: Callable, hook: str, jump: list[JumpTo] | None) -> AgentMiddleware:
    class _Fn(AgentMiddleware):
        state_schema = None

        @property
        def name(self) -> str:
            return getattr(fn, "__name__", hook) or hook

    if jump:
        fn = hook_config(jump)(fn)
    setattr(_Fn, hook, staticmethod(fn))
    return _Fn()


def before_agent(_fn: Callable | None = None, *, can_jump_to: list[JumpTo] | None = None):
    def deco(fn: Callable) -> AgentMiddleware:
        return _make_single_hook_mw(fn, "before_agent", can_jump_to)

    return deco(_fn) if _fn is not None else deco


def before_model(_fn: Callable | None = None, *, can_jump_to: list[JumpTo] | None = None):
    def deco(fn: Callable) -> AgentMiddleware:
        return _make_single_hook_mw(fn, "before_model", can_jump_to)

    return deco(_fn) if _fn is not None else deco


def after_model(_fn: Callable | None = None, *, can_jump_to: list[JumpTo] | None = None):
    def deco(fn: Callable) -> AgentMiddleware:
        return _make_single_hook_mw(fn, "after_model", can_jump_to)

    return deco(_fn) if _fn is not None else deco


def after_agent(_fn: Callable | None = None, *, can_jump_to: list[JumpTo] | None = None):
    def deco(fn: Callable) -> AgentMiddleware:
        return _make_single_hook_mw(fn, "after_agent", can_jump_to)

    return deco(_fn) if _fn is not None else deco


def wrap_model_call(fn: Callable) -> AgentMiddleware:
    return _make_single_hook_mw(fn, "wrap_model_call", None)


def wrap_tool_call(fn: Callable) -> AgentMiddleware:
    return _make_single_hook_mw(fn, "wrap_tool_call", None)


def dynamic_prompt(fn: Callable) -> AgentMiddleware:
    """The @dynamic_prompt decorator: fn(request) -> str becomes the system
    message for every model call (the upstream shape)."""

    def wrapper(request: ModelRequest, handler: Callable[[ModelRequest], Any]) -> Any:
        return handler(request.override(system_message=SystemMessage(content=fn(request))))

    return _make_single_hook_mw(wrapper, "wrap_model_call", None)


# ---------------------------------------------------------------------------
# the shared retry helpers (the upstream _retry.py shape)
# ---------------------------------------------------------------------------

RetryOn = "tuple[type[Exception], ...] | Callable[[Exception], bool]"
OnFailure = "Literal['error', 'continue'] | Callable[[Exception], str]"


def validate_retry_params(max_retries: int, initial_delay: float,
                          max_delay: float, backoff_factor: float) -> None:
    if max_retries < 0:
        raise ValueError("max_retries must be >= 0")
    if initial_delay < 0:
        raise ValueError("initial_delay must be >= 0")
    if max_delay < 0:
        raise ValueError("max_delay must be >= 0")
    if backoff_factor < 0:
        raise ValueError("backoff_factor must be >= 0")


def default_retry_on(exc: BaseException) -> bool:
    """Retry everything except the walk's own control flow (an interrupt or a
    recursion stop is a RESULT, not a failure)."""
    if isinstance(exc, (GraphInterrupt, GraphRecursionError)):
        return False
    return isinstance(exc, Exception)


def should_retry_exception(exc: Exception, retry_on: Any) -> bool:
    if callable(retry_on):
        return bool(retry_on(exc))
    return isinstance(exc, retry_on)


def calculate_delay(retry_number: int, *, backoff_factor: float, initial_delay: float,
                    max_delay: float, jitter: bool) -> float:
    if backoff_factor == 0.0:
        delay = initial_delay
    else:
        delay = initial_delay * (backoff_factor ** retry_number)
    delay = min(delay, max_delay)
    if jitter and delay > 0:
        delay += delay * 0.25 * random.uniform(-1.0, 1.0)  # noqa: S311 - the ±25% jitter
        delay = max(0.0, delay)
    return delay


# ---------------------------------------------------------------------------
# the internal-call tag (the emulation model call stays out of the run tree)
# ---------------------------------------------------------------------------

INTERNAL_CALL_METADATA_KEY = "lc_internal_call"
_INTERNAL_CALL_TOKEN = uuid.uuid4().hex


def internal_call_metadata() -> dict[str, Any]:
    """Merge into a model call's config metadata to mark it internal."""
    return {INTERNAL_CALL_METADATA_KEY: _INTERNAL_CALL_TOKEN}


class InternalCallTransformer:
    """The stream-lane contract for middleware-internal model calls: a callable
    transformer over (chunk, metadata) pairs that drops chunks tagged internal
    (the house stream seam; the emulation lane uses it)."""

    @staticmethod
    def transform(chunks: Any) -> Any:
        for chunk, meta in chunks:
            if isinstance(meta, dict) and meta.get(INTERNAL_CALL_METADATA_KEY) == _INTERNAL_CALL_TOKEN:
                continue
            yield chunk, meta


# ---------------------------------------------------------------------------
# TIER 1 - SummarizationMiddleware
# ---------------------------------------------------------------------------

DEFAULT_SUMMARY_PROMPT = """You are a context extraction assistant. Your sole
objective is to extract the highest-quality, most relevant context from the
conversation history below; it will REPLACE that history. Structure the summary
in sections: SESSION INTENT, SUMMARY (choices, conclusions, rejected options
and why), ARTIFACTS (files/resources created or changed, with paths), NEXT
STEPS. Respond ONLY with the extracted context.

<messages>
{messages}
</messages>"""

_DEFAULT_MESSAGES_TO_KEEP = 20
_DEFAULT_TRIM_TOKEN_LIMIT = 4000
_DEFAULT_FALLBACK_MESSAGE_COUNT = 15


def _approx_token_counter(messages: Any) -> int:
    """The house approximate counter: ~4 chars per token over the text view
    (the upstream count_tokens_approximately shape, chars/4)."""
    total = 0
    for m in messages:
        total += len(_text_of(getattr(m, "content", m))) // 4 + 8
    return total


def _coerce_trigger(trigger: Any) -> tuple[tuple[str, Any], ...]:
    if trigger is None:
        return ()
    clauses = trigger if isinstance(trigger, (list, tuple)) and (
        not trigger or isinstance(trigger[0], (list, tuple))) else [trigger]
    out: list[tuple[str, Any]] = []
    for clause in clauses:
        if not isinstance(clause, (list, tuple)) or len(clause) != 2:
            raise ValueError(f"trigger clauses are ('tokens'|'messages'|'fraction', value), got {clause!r}")
        kind, value = clause
        if kind not in ("tokens", "messages", "fraction"):
            raise ValueError(f"unsupported trigger kind {kind!r}")
        if kind == "fraction" and not 0 < value <= 1:
            raise ValueError(f"fractional trigger values must be between 0 and 1, got {value}")
        if kind in ("tokens", "messages") and value <= 0:
            raise ValueError(f"{kind} trigger thresholds must be greater than 0, got {value}")
        out.append((kind, value))
    return tuple(out)


def _coerce_keep(keep: Any) -> tuple[str, Any]:
    kind, value = keep if isinstance(keep, (list, tuple)) and len(keep) == 2 else ("messages", keep)
    if kind not in ("messages", "tokens", "fraction"):
        raise ValueError(f"unsupported keep kind {kind!r}")
    if kind == "fraction" and not 0 < value <= 1:
        raise ValueError(f"fractional keep values must be between 0 and 1, got {value}")
    if kind in ("messages", "tokens") and value <= 0:
        raise ValueError(f"{kind} keep thresholds must be greater than 0, got {value}")
    return (kind, value)


class SummarizationMiddleware(AgentMiddleware):
    """Token-threshold history summarization (the upstream summarization.py
    shape): before a model call, when a trigger clause is met, the older part of
    the conversation is summarized into ONE HumanMessage and the lane is
    rebuilt - RemoveMessage(REMOVE_ALL) + summary + preserved tail. The cutoff
    never splits an AI/Tool pair (the safe-cutoff walk)."""

    def __init__(
        self,
        model: Any = None,
        *,
        trigger: Any = (("tokens", 4000),),
        keep: Any = ("messages", _DEFAULT_MESSAGES_TO_KEEP),
        token_counter: Callable | None = None,
        summary_prompt: str = DEFAULT_SUMMARY_PROMPT,
        trim_tokens_to_summarize: int | None = _DEFAULT_TRIM_TOKEN_LIMIT,
        max_summary_attempts: int = 3,
    ) -> None:
        self.model = model
        self.trigger_clauses = _coerce_trigger(trigger)
        if not self.trigger_clauses:
            raise ValueError("at least one trigger clause is required")
        self.keep = _coerce_keep(keep)
        self.token_counter = token_counter or _approx_token_counter
        self.summary_prompt = summary_prompt
        self.trim_tokens_to_summarize = trim_tokens_to_summarize
        self.max_summary_attempts = max(1, int(max_summary_attempts))

    # -- the trigger -----------------------------------------------------------

    def _should_summarize(self, messages: list[Any]) -> bool:
        total = self.token_counter(messages)
        for kind, value in self.trigger_clauses:
            if kind == "messages" and len(messages) >= value:
                return True
            if kind == "tokens" and total >= value:
                return True
            if kind == "fraction":
                cap = self._profile_limit()
                if cap is not None and total >= int(cap * value):
                    return True
        return False

    def _profile_limit(self) -> int | None:
        model = self.model
        profile = getattr(model, "profile", None)
        if isinstance(profile, dict):
            cap = profile.get("max_input_tokens")
            if isinstance(cap, int):
                return cap
        return None

    # -- the cutoff (AI/Tool pairs never split) ----------------------------------

    @staticmethod
    def _find_safe_cutoff_point(messages: list[Any], cutoff: int) -> int:
        """If the cut lands on/inside a run of ToolMessages, move the cutoff back
        to include their owning AIMessage (the pair stays whole)."""
        if cutoff >= len(messages) or not isinstance(messages[cutoff], ToolMessage):
            return cutoff
        ids: set[str] = set()
        idx = cutoff
        while idx < len(messages) and isinstance(messages[idx], ToolMessage):
            ids.add(messages[idx].tool_call_id)
            idx += 1
        j = cutoff - 1
        while j >= 0:
            m = messages[j]
            if isinstance(m, ToolMessage):
                j -= 1
                continue
            if isinstance(m, AIMessage) and any(c.get("id") in ids for c in (m.tool_calls or [])):
                return j
            return cutoff
        return 0

    def _determine_cutoff(self, messages: list[Any]) -> int:
        if len(messages) <= 1:
            return 0
        kind, value = self.keep
        if kind == "messages":
            target = len(messages) - int(value)
        else:
            cap = self._profile_limit() if kind == "fraction" else None
            budget = int(cap * value) if cap is not None else (int(value) if kind == "tokens" else 0)
            if budget <= 0:
                target = len(messages) - _DEFAULT_MESSAGES_TO_KEEP
            else:
                target = len(messages)
                acc = 0
                for i in range(len(messages) - 1, -1, -1):
                    acc += self.token_counter([messages[i]])
                    if acc > budget:
                        break
                    target = i
                else:
                    return 0
        if target <= 0:
            return 0
        return self._find_safe_cutoff_point(messages, target)

    # -- the summary ----------------------------------------------------------

    def _summary_text(self, messages: list[Any]) -> str:
        if self.model is None:
            raise ValueError("SummarizationMiddleware needs a model (or a callable summary_model)")
        selected = list(messages)
        if self.trim_tokens_to_summarize is not None:
            budget = self.trim_tokens_to_summarize
            acc, kept = 0, []
            for m in reversed(selected):
                cost = self.token_counter([m])
                if acc + cost > budget and kept:
                    break
                acc += cost
                kept.append(m)
            selected = list(reversed(kept))
        prompt = self.summary_prompt.replace("{messages}", _text_of(selected))
        last: Exception | None = None
        for _ in range(self.max_summary_attempts):
            try:
                out = self.model.invoke([HumanMessage(content=prompt)])
                text = getattr(out, "text", None) or _text_of(getattr(out, "content", out))
                if isinstance(out, str):
                    text = out
                if not str(text).strip():
                    raise ValueError("empty summary")
                return str(text)
            except (GraphInterrupt, GraphRecursionError):
                raise
            except Exception as e:  # noqa: BLE001 - retry, then the middle-cut
                last = e
        raise RuntimeError(f"summarization failed after {self.max_summary_attempts} attempts: {last}")

    @staticmethod
    def _build_new_messages(summary: str) -> list[HumanMessage]:
        return [HumanMessage(
            content=f"Here is a summary of the conversation to date:\n\n{summary}",
            additional_kwargs={"lc_source": "summarization"})]

    # -- the hook --------------------------------------------------------------

    @hook_config(can_jump_to=["model", "end"])
    def before_model(self, state: dict, runtime: dict) -> dict | None:
        messages = list(state.get("messages") or [])
        if not self._should_summarize(messages):
            return None
        cutoff = self._determine_cutoff(messages)
        if cutoff <= 0:
            return None
        to_summarize, preserved = messages[:cutoff], messages[cutoff:]
        try:
            summary = self._summary_text(to_summarize)
        except RuntimeError:
            # the overflow middle-cut: the summarizer failed - keep the freshest
            # tail instead (the upstream fallback shape) and say so
            keep_n = min(len(messages) - 1, _DEFAULT_FALLBACK_MESSAGE_COUNT)
            kept = messages[len(messages) - keep_n:]
            return {"messages": _rewrite_messages(messages, lambda ms: kept),
                    "jump_to": "model"}
        new_msgs = self._build_new_messages(summary)
        return {"messages": [RemoveMessage(id="remove_all"), *new_msgs,
                             *_ensure_ids(preserved)]}


# ---------------------------------------------------------------------------
# TIER 2 - PIIMiddleware (detectors + strategies + the stream transformer)
# ---------------------------------------------------------------------------


class PIIDetectionError(Exception):
    """Raised by the `block` strategy when PII is detected."""

    def __init__(self, pii_type: str, match_text: str) -> None:
        self.pii_type = pii_type
        self.match = match_text
        super().__init__(f"PII detected ({pii_type}): {match_text!r}")


@dataclass
class PIIMatch:
    start: int
    end: int
    value: str
    type: str


_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_MAC_RE = re.compile(r"\b([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")
_URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>\"']+" )
_CC_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")


def _luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = ord(ch) - 48
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def _detect_email(content: str) -> list[PIIMatch]:
    return [PIIMatch(m.start(), m.end(), m.group(), "email") for m in _EMAIL_RE.finditer(content)]


def _detect_credit_card(content: str) -> list[PIIMatch]:
    out = []
    for m in _CC_RE.finditer(content):
        digits = re.sub(r"\D", "", m.group())
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            out.append(PIIMatch(m.start(), m.end(), m.group(), "credit_card"))
    return out


def _detect_ip(content: str) -> list[PIIMatch]:
    import ipaddress
    out = []
    for m in re.finditer(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", content):
        try:
            ipaddress.ip_address(m.group())
        except ValueError:
            continue
        out.append(PIIMatch(m.start(), m.end(), m.group(), "ip"))
    return out


def _detect_mac_address(content: str) -> list[PIIMatch]:
    return [PIIMatch(m.start(), m.end(), m.group(), "mac_address") for m in _MAC_RE.finditer(content)]


def _detect_url(content: str) -> list[PIIMatch]:
    return [PIIMatch(m.start(), m.end(), m.group(), "url") for m in _URL_RE.finditer(content)]


_BUILTIN_DETECTORS: dict[str, Callable[[str], list[PIIMatch]]] = {
    "email": _detect_email,
    "credit_card": _detect_credit_card,
    "ip": _detect_ip,
    "mac_address": _detect_mac_address,
    "url": _detect_url,
}

_MASK_KEEP = {"credit_card": 4, "mac_address": 5}


def _apply_pii_strategy(content: str, matches: list[PIIMatch], strategy: str,
                        pii_type: str) -> str:
    """Replace matches per strategy; returns the new content."""
    if strategy == "block":
        if matches:
            raise PIIDetectionError(pii_type, matches[0].value)
        return content
    out = content
    for m in sorted(matches, key=lambda x: x.start, reverse=True):
        if strategy == "redact":
            rep = f"[REDACTED_{pii_type.upper()}]"
        elif strategy == "mask":
            keep = _MASK_KEEP.get(pii_type, 3)
            digits = re.sub(r"[^A-Za-z0-9@.]", "", m.value)
            tail = digits[-keep:] if keep and len(digits) > keep else ""
            rep = "*" * max(4, len(m.value) - len(tail)) + (tail if tail else "")
        elif strategy == "hash":
            digest = hashlib.sha256(m.value.encode()).hexdigest()[:8]
            rep = f"<{pii_type}_hash:{digest}>"
        else:
            raise ValueError(f"unknown PII strategy {strategy!r}")
        out = out[:m.start] + rep + out[m.end:]
    return out


class _PIIStreamTransformer:
    """Live redaction: a transformer over (chunk, metadata) pairs that scrubs
    AI text deltas IN FLIGHT (the upstream _PIIStreamTransformer shape)."""

    def __init__(self, middlewares: list["PIIMiddleware"]) -> None:
        self._mws = middlewares

    def transform(self, chunks: Any) -> Any:
        for chunk, meta in chunks:
            yield self._redact_chunk(chunk), meta

    def _redact_chunk(self, chunk: Any) -> Any:
        if isinstance(chunk, AIMessageChunk) or isinstance(chunk, AIMessage):
            content = getattr(chunk, "content", "")
            if isinstance(content, str) and content:
                new = content
                for mw in self._mws:
                    matches = mw.detect(new)
                    if matches:
                        new = _apply_pii_strategy(new, matches, mw.strategy, mw.pii_type)
                if new != content:
                    try:
                        chunk.content = new
                    except Exception:  # noqa: BLE001 - frozen chunks get a copy
                        return type(chunk)(content=new, id=chunk.id)
        return chunk


class PIIMiddleware(AgentMiddleware):
    """Detect and handle PII in conversations (the upstream pii.py shape):
    one middleware per pii_type + strategy; scans the input lane (before_model)
    and optionally the output lane (after_model) and the tool results."""

    def __init__(
        self,
        pii_type: str,
        *,
        strategy: str = "redact",
        detector: Callable[[str], list[PIIMatch]] | str | None = None,
        apply_to_input: bool = True,
        apply_to_output: bool = False,
        apply_to_tool_results: bool = False,
    ) -> None:
        self.pii_type = pii_type
        if strategy not in ("block", "redact", "mask", "hash"):
            raise ValueError(f"unknown PII strategy {strategy!r}")
        self.strategy = strategy
        if detector is None:
            if pii_type not in _BUILTIN_DETECTORS:
                raise ValueError(
                    f"unknown pii_type {pii_type!r} - built-ins: {sorted(_BUILTIN_DETECTORS)} "
                    "(or pass a custom detector)")
            self.detector = _BUILTIN_DETECTORS[pii_type]
        elif isinstance(detector, str):
            rx = re.compile(detector)
            self.detector = lambda content: [
                PIIMatch(m.start(), m.end(), m.group(), pii_type) for m in rx.finditer(content)]
        else:
            self.detector = detector
        self.apply_to_input = apply_to_input
        self.apply_to_output = apply_to_output
        self.apply_to_tool_results = apply_to_tool_results

    def detect(self, content: str) -> list[PIIMatch]:
        return self.detector(content)

    def _scrub(self, messages: list[Any], lane: str) -> list[Any] | None:
        touched = False
        out: list[Any] = []
        for m in messages:
            if isinstance(m, (HumanMessage,)) and lane == "input":
                new = _apply_pii_strategy(_text_of(m.content), self.detect(_text_of(m.content)),
                                          self.strategy, self.pii_type)
                if new != m.content:
                    m = HumanMessage(content=new, id=m.id)
                    touched = True
            elif isinstance(m, AIMessage) and lane == "output":
                new = _apply_pii_strategy(_text_of(m.content), self.detect(_text_of(m.content)),
                                          self.strategy, self.pii_type)
                if new != m.content:
                    m = AIMessage(content=new, id=m.id, tool_calls=m.tool_calls)
                    touched = True
            elif isinstance(m, ToolMessage) and lane == "tool_results":
                new = _apply_pii_strategy(_text_of(m.content), self.detect(_text_of(m.content)),
                                          self.strategy, self.pii_type)
                if new != m.content:
                    m = ToolMessage(content=new, tool_call_id=m.tool_call_id, id=m.id,
                                    status=m.status)
                    touched = True
            out.append(m)
        return out if touched else None

    def before_model(self, state: dict, runtime: dict) -> dict | None:  # noqa: ARG002
        if not self.apply_to_input:
            return None
        messages = list(state.get("messages") or [])
        scrubbed = self._scrub(messages, "input")
        if scrubbed is None:
            return None
        return {"messages": _rewrite_messages(messages, lambda ms: scrubbed)}

    def after_model(self, state: dict, runtime: dict) -> dict | None:  # noqa: ARG002
        if not (self.apply_to_output or self.apply_to_tool_results):
            return None
        messages = list(state.get("messages") or [])
        scrubbed = self._scrub(messages, "output") if self.apply_to_output else None
        if self.apply_to_tool_results:
            tool_lane = self._scrub(messages, "tool_results")
            if tool_lane is not None:
                scrubbed = tool_lane if scrubbed is None else scrubbed
        if scrubbed is None:
            return None
        return {"messages": _rewrite_messages(messages, lambda ms: scrubbed)}

    @property
    def transformers(self) -> tuple:  # type: ignore[override]
        if self.apply_to_output:
            return (_PIIStreamTransformer([self]),)
        return ()


# ---------------------------------------------------------------------------
# TIER 3 - the call limits
# ---------------------------------------------------------------------------


class ModelCallLimitExceededError(Exception):
    def __init__(self, thread_count: int, run_count: int,
                 thread_limit: int | None, run_limit: int | None) -> None:
        self.thread_count = thread_count
        self.run_count = run_count
        self.thread_limit = thread_limit
        self.run_limit = run_limit
        parts = []
        if thread_limit is not None:
            parts.append(f"thread limit ({thread_count}/{thread_limit})")
        if run_limit is not None:
            parts.append(f"run limit ({run_count}/{run_limit})")
        super().__init__(f"Model call limits exceeded: {', '.join(parts)}")


def _build_limit_exceeded_message(thread_count: int, run_count: int,
                                  thread_limit: int | None, run_limit: int | None) -> str:
    parts = []
    if thread_limit is not None:
        parts.append(f"thread limit ({thread_count}/{thread_limit})")
    if run_limit is not None:
        parts.append(f"run limit ({run_count}/{run_limit})")
    return f"Model call limits exceeded: {', '.join(parts)}"


class ModelCallLimitMiddleware(AgentMiddleware):
    """Track model calls and enforce limits (the upstream model_call_limit.py
    shape): thread counters persist on the thread, run counters restart every
    invoke; exit_behavior 'end' jumps with an honest AI message, 'error'
    raises ModelCallLimitExceededError."""

    state_schema = {
        "thread_model_call_count": int,
        "run_model_call_count": Annotated[int, _untracked_value],
    }

    def __init__(self, *, thread_limit: int | None = None, run_limit: int | None = None,
                 exit_behavior: str = "end") -> None:
        if thread_limit is None and run_limit is None:
            raise ValueError("At least one limit must be specified (thread_limit or run_limit)")
        if exit_behavior not in ("end", "error"):
            raise ValueError(f"Invalid exit_behavior: {exit_behavior}. Must be 'end' or 'error'")
        self.thread_limit = thread_limit
        self.run_limit = run_limit
        self.exit_behavior = exit_behavior

    @hook_config(can_jump_to=["end"])
    def before_model(self, state: dict, runtime: dict) -> dict | None:  # noqa: ARG002
        tc = state.get("thread_model_call_count") or 0
        rc = state.get("run_model_call_count") or 0
        if ((self.thread_limit is not None and tc >= self.thread_limit)
                or (self.run_limit is not None and rc >= self.run_limit)):
            if self.exit_behavior == "error":
                raise ModelCallLimitExceededError(tc, rc, self.thread_limit, self.run_limit)
            msg = _build_limit_exceeded_message(tc, rc, self.thread_limit, self.run_limit)
            return {"jump_to": "end", "messages": [AIMessage(content=msg)]}
        return None

    def after_model(self, state: dict, runtime: dict) -> dict | None:  # noqa: ARG002
        return {"thread_model_call_count": (state.get("thread_model_call_count") or 0) + 1,
                "run_model_call_count": (state.get("run_model_call_count") or 0) + 1}


class ToolCallLimitExceededError(Exception):
    def __init__(self, thread_count: int, run_count: int, thread_limit: int | None,
                 run_limit: int | None, tool_name: str | None) -> None:
        self.thread_count = thread_count
        self.run_count = run_count
        self.thread_limit = thread_limit
        self.run_limit = run_limit
        self.tool_name = tool_name
        scope = f" for {tool_name!r}" if tool_name else ""
        parts = []
        if thread_limit is not None:
            parts.append(f"thread limit ({thread_count}/{thread_limit})")
        if run_limit is not None:
            parts.append(f"run limit ({run_count}/{run_limit})")
        super().__init__(f"Tool call limits{scope} exceeded: {', '.join(parts)}")


def _tool_limit_tool_message(tool_name: str | None) -> str:
    return (f"Tool call limit exceeded for {tool_name!r}."
            if tool_name else "Tool call limit exceeded.")


class ToolCallLimitMiddleware(AgentMiddleware):
    """Per-tool-name call limits (the upstream tool_call_limit.py shape):
    thread counters persist, run counters restart; exit_behavior 'continue'
    answers blocked calls with error ToolMessages, 'end' answers EVERY pending
    call (the history stays valid) and jumps with an honest AI message,
    'error' raises ToolCallLimitExceededError."""

    state_schema = {
        "thread_tool_call_count": dict,
        "run_tool_call_count": Annotated[dict, _untracked_value],
    }

    def __init__(self, *, tool_name: str | None = None, thread_limit: int | None = None,
                 run_limit: int | None = None, exit_behavior: str = "continue") -> None:
        if thread_limit is None and run_limit is None:
            raise ValueError("At least one limit must be specified (thread_limit or run_limit)")
        if exit_behavior not in ("continue", "end", "error"):
            raise ValueError(
                f"Invalid exit_behavior: {exit_behavior!r}. Must be 'continue', 'end' or 'error'")
        self.tool_name = tool_name
        self.thread_limit = thread_limit
        self.run_limit = run_limit
        self.exit_behavior = exit_behavior

    @hook_config(can_jump_to=["end"])
    def after_model(self, state: dict, runtime: dict) -> dict | None:  # noqa: ARG002
        messages = list(state.get("messages") or [])
        last_ai = _last_ai(messages)
        if last_ai is None or not last_ai.tool_calls:
            return None
        key = self.tool_name or "__all__"
        thread_counts = dict(state.get("thread_tool_call_count") or {})
        run_counts = dict(state.get("run_tool_call_count") or {})
        tc = thread_counts.get(key, 0)
        rc = run_counts.get(key, 0)

        # a named limit scopes to THAT tool's calls; every other tool runs free
        relevant = [c for c in last_ai.tool_calls
                    if self.tool_name is None or c.get("name") == self.tool_name]
        allowed: list[dict] = [c for c in last_ai.tool_calls if c not in relevant]
        blocked: list[dict] = []
        ntc, nrc = tc, rc
        for call in relevant:
            if ((self.thread_limit is not None and ntc + 1 > self.thread_limit)
                    or (self.run_limit is not None and nrc + 1 > self.run_limit)):
                blocked.append(call)
                nrc += 1
            else:
                allowed.append(call)
                ntc += 1
                nrc += 1
        thread_counts[key] = ntc
        run_counts[key] = nrc
        update: dict[str, Any] = {"thread_tool_call_count": thread_counts,
                                  "run_tool_call_count": run_counts}
        if not blocked:
            return update if allowed else None

        if self.exit_behavior == "error":
            raise ToolCallLimitExceededError(
                ntc, nrc, self.thread_limit, self.run_limit, self.tool_name)

        artificial: list[BaseMessage] = [
            ToolMessage(content=_tool_limit_tool_message(self.tool_name),
                        tool_call_id=c.get("id") or "", name=c.get("name"),
                        status="error")
            for c in blocked]
        if self.exit_behavior == "end":
            blocked_ids = {c.get("id") for c in blocked}
            for c in last_ai.tool_calls:
                if c.get("id") not in blocked_ids:
                    artificial.append(ToolMessage(
                        content=("Execution stopped before this tool call could run because "
                                 "another tool call in the same batch exceeded the limit."),
                        tool_call_id=c.get("id") or "", name=c.get("name"), status="error"))
            thread_counts[key] = tc  # the blocked batch never counted at thread level
            update["thread_tool_call_count"] = thread_counts
            update["messages"] = [*artificial,
                                  AIMessage(content=f"Tool call limits exceeded: {_tool_limit_tool_message(self.tool_name)}")]
            update["jump_to"] = "end"
            return update
        update["messages"] = artificial  # continue: only the blocked calls answered
        return update


# ---------------------------------------------------------------------------
# TIER 4 - the model wraps: retry + fallback
# ---------------------------------------------------------------------------


class ModelRetryMiddleware(AgentMiddleware):
    """Retry failed model calls with backoff + jitter (the upstream
    model_retry.py shape): retry_on (tuple or callable) selects; on_failure
    'error' re-raises, 'continue' returns an honest AI message, a callable
    formats the message."""

    def __init__(self, *, max_retries: int = 2, retry_on: Any = default_retry_on,
                 on_failure: Any = "continue", backoff_factor: float = 2.0,
                 initial_delay: float = 1.0, max_delay: float = 8.0,
                 jitter: bool = True) -> None:
        validate_retry_params(max_retries, initial_delay, max_delay, backoff_factor)
        self.max_retries = max_retries
        self.retry_on = retry_on
        self.on_failure = on_failure
        self.backoff_factor = backoff_factor
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.jitter = jitter

    def _failure_message(self, exc: Exception) -> AIMessage:
        if callable(self.on_failure):
            return AIMessage(content=self.on_failure(exc))
        if self.on_failure == "error":
            raise exc
        return AIMessage(content=f"Model call failed after {self.max_retries} retries: {exc}")

    def wrap_model_call(self, request: ModelRequest,
                        handler: Callable[[ModelRequest], Any]) -> Any:
        last: Exception
        for attempt in range(self.max_retries + 1):
            try:
                return handler(request)
            except (GraphInterrupt, GraphRecursionError):
                raise
            except Exception as exc:  # noqa: BLE001 - the retry contract
                last = exc
                if not should_retry_exception(exc, self.retry_on):
                    if self.on_failure == "error" or callable(self.on_failure):
                        raise
                    return self._failure_message(exc)
                if attempt < self.max_retries:
                    time.sleep(calculate_delay(
                        attempt, backoff_factor=self.backoff_factor,
                        initial_delay=self.initial_delay, max_delay=self.max_delay,
                        jitter=self.jitter))
        if self.on_failure == "error":
            raise last
        return self._failure_message(last)


def _sanitize_request_for_fallback(request: ModelRequest, model: Any) -> ModelRequest:
    """Strip what a fallback model cannot accept (the upstream sanitizer idea,
    the house shape: model_settings ride per-model only)."""
    return request.override(model_settings={})


class ModelFallbackMiddleware(AgentMiddleware):
    """Try fallback models in order on errors (the upstream model_fallback.py
    shape): primary first (the handler's own model), then the fallbacks via
    request.override(model=...); interrupts/recursion propagate; all fail =
    the last error re-raised."""

    def __init__(self, primary: Any = None, *additional_models: Any) -> None:
        models = ([primary] if primary is not None else []) + list(additional_models)
        if not models:
            raise ValueError("ModelFallbackMiddleware needs at least one fallback model")
        self.models = list(models)

    def wrap_model_call(self, request: ModelRequest,
                        handler: Callable[[ModelRequest], Any]) -> Any:
        last: Exception
        try:
            return handler(request)
        except (GraphInterrupt, GraphRecursionError):
            raise
        except Exception as e:  # noqa: BLE001 - the fallback contract
            last = e
        for fallback_model in self.models:
            fallback_request = _sanitize_request_for_fallback(request, fallback_model)
            try:
                return handler(fallback_request.override(model=fallback_model))
            except (GraphInterrupt, GraphRecursionError):
                raise
            except Exception as e:  # noqa: BLE001
                last = e
                continue
        raise last


# ---------------------------------------------------------------------------
# TIER 5 - the tool wraps: error / retry / emulator
# ---------------------------------------------------------------------------


class ToolErrorMiddleware(AgentMiddleware):
    """Return selected tool-execution exceptions to the model as error
    ToolMessages (the upstream tool_error.py shape): on_error(exc, request)
    -> content (None re-raises the original)."""

    def __init__(self, on_error: Callable[[Exception, ToolCallRequest], str | None] | None = None) -> None:
        self.on_error = on_error

    def wrap_tool_call(self, request: ToolCallRequest,
                       handler: Callable[[ToolCallRequest], Any]) -> Any:
        try:
            return handler(request)
        except (GraphInterrupt, GraphRecursionError):
            raise
        except Exception as exc:  # noqa: BLE001 - the error contract
            if self.on_error is None:
                raise
            content = self.on_error(exc, request)
            if content is None:
                raise
            if isinstance(content, list):
                content = _text_of(content)
            return ToolMessage(content=str(content), tool_call_id=request.tool_call.get("id") or "",
                               name=request.tool_call.get("name"), status="error")


class ToolRetryMiddleware(AgentMiddleware):
    """Retry failed tool executions with backoff (the upstream tool_retry.py
    shape): continue = an error ToolMessage after the budget, error = re-raise."""

    def __init__(self, *, max_retries: int = 2, retry_on: Any = default_retry_on,
                 on_failure: Any = "continue", backoff_factor: float = 2.0,
                 initial_delay: float = 1.0, max_delay: float = 8.0,
                 jitter: bool = True) -> None:
        validate_retry_params(max_retries, initial_delay, max_delay, backoff_factor)
        self.max_retries = max_retries
        self.retry_on = retry_on
        self.on_failure = on_failure
        self.backoff_factor = backoff_factor
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.jitter = jitter

    def wrap_tool_call(self, request: ToolCallRequest,
                       handler: Callable[[ToolCallRequest], Any]) -> Any:
        last: Exception
        for attempt in range(self.max_retries + 1):
            try:
                return handler(request)
            except (GraphInterrupt, GraphRecursionError):
                raise
            except Exception as exc:  # noqa: BLE001
                last = exc
                if not should_retry_exception(exc, self.retry_on):
                    if self.on_failure == "error" or callable(self.on_failure):
                        raise
                    break
                if attempt < self.max_retries:
                    time.sleep(calculate_delay(
                        attempt, backoff_factor=self.backoff_factor,
                        initial_delay=self.initial_delay, max_delay=self.max_delay,
                        jitter=self.jitter))
        if self.on_failure == "error" or callable(self.on_failure):
            raise last
        content = (self.on_failure(last) if callable(self.on_failure)
                   else f"Tool failed after {self.max_retries} retries: {last}")
        return ToolMessage(content=str(content), tool_call_id=request.tool_call.get("id") or "",
                           name=request.tool_call.get("name"), status="error")


_EMULATION_PROMPT = (
    "You are emulating a tool call for testing purposes.\n\n"
    "Tool: {name}\n"
    "Description: {description}\n"
    "Arguments: {args}\n\n"
    "Generate a realistic response that this tool would return given these "
    "arguments. Return ONLY the tool's output, no explanation or preamble.")


class LLMToolEmulator(AgentMiddleware):
    """Emulate selected tools with an LLM instead of executing them (the
    upstream tool_emulator.py shape): tools=None emulates ALL tools, a list of
    names/tools narrows it; the emulation call is tagged internal."""

    transformers = (InternalCallTransformer,)

    def __init__(self, *, tools: list[Any] | None = None, model: Any = None) -> None:
        self.emulate_all = tools is None
        self.tools_to_emulate: set[str] = set()
        for t in (tools or []):
            self.tools_to_emulate.add(t if isinstance(t, str) else t.name)
        if model is None:
            raise ValueError(
                "LLMToolEmulator needs a model (pass model= explicitly - the "
                "implicit default provider was removed upstream too)")
        self.model = model

    def wrap_tool_call(self, request: ToolCallRequest,
                       handler: Callable[[ToolCallRequest], Any]) -> Any:
        name = request.tool_call.get("name")
        if not (self.emulate_all or name in self.tools_to_emulate):
            return handler(request)
        description = getattr(request.tool, "description", None) or "No description available"
        prompt = _EMULATION_PROMPT.format(name=name, description=description,
                                          args=request.tool_call.get("args"))
        response = self.model.invoke([HumanMessage(content=prompt)])
        content = getattr(response, "content", response)
        return ToolMessage(content=_text_of(content),
                           tool_call_id=request.tool_call.get("id") or "", name=name)


# ---------------------------------------------------------------------------
# TIER 6 - human in the loop (the P3 interrupt() seam inside after_model)
# ---------------------------------------------------------------------------

_HITL_REVIEWER = "human"


def _hitl_action_request(tool_call: dict, description: str) -> dict:
    return {"name": tool_call.get("name") or "", "args": dict(tool_call.get("args") or {}),
            "description": description or f"Run tool {tool_call.get('name')!r}",
            "id": tool_call.get("id") or ""}


def _hitl_answer_message(tool_call: dict, decision: dict) -> ToolMessage:
    kind = decision.get("type")
    reason = decision.get("reason") or decision.get("response") or ""
    if kind == "reject":
        content = (f"User rejected the tool call for `{tool_call.get('name')}` with reason: {reason}"
                   if reason else
                   f"User rejected the tool call for `{tool_call.get('name')}` with id {tool_call.get('id')}")
    elif kind == "respond":
        content = f"The human answered on behalf of `{tool_call.get('name')}`: {reason}"
    else:
        raise ValueError(f"unexpected decision kind {kind!r}")
    return ToolMessage(content=content, tool_call_id=tool_call.get("id") or "",
                       name=tool_call.get("name"), status="error" if kind == "reject" else "success")


class HumanInTheLoopMiddleware(AgentMiddleware):
    """Gate tool calls behind a human decision (the upstream
    human_in_the_loop.py shape, batched mode): after_model inspects the model's
    pending tool_calls; every gated call parks the walk ONCE on the P3
    interrupt() seam with one HITLRequest; the resume carries
    {"decisions": [...]} in call order - approve (the tool runs), edit (the
    reviewer's args replace the call's, marked in the tool result), reject /
    respond (an honest ToolMessage answers the call, the call is stripped from
    the AIMessage so the loop continues)."""

    state_schema = {
        _EDITED_TOOL_CALLS_KEY: Annotated[dict, _untracked_value],
    }

    def __init__(self, *, interrupt_on: dict[str, dict[str, Any]]) -> None:
        for name, cfg in interrupt_on.items():
            if not isinstance(cfg, dict) or not cfg.get("allowed_decisions"):
                raise ValueError(
                    f"interrupt_on[{name!r}] needs a non-empty allowed_decisions list")
            bad = set(cfg["allowed_decisions"]) - {"approve", "edit", "reject", "respond"}
            if bad:
                raise ValueError(f"interrupt_on[{name!r}]: unknown decision kinds {sorted(bad)}")
            if cfg.get("description") is not None and not isinstance(cfg["description"], (str, Callable)):
                raise ValueError(f"interrupt_on[{name!r}]: description must be a str or a callable")
        self.interrupt_on = interrupt_on

    def after_model(self, state: dict, runtime: dict) -> dict | None:  # noqa: ARG002
        messages = list(state.get("messages") or [])
        last_ai = _last_ai(messages)
        if last_ai is None or not last_ai.tool_calls:
            return None
        gated: list[tuple[int, dict, dict]] = []
        for idx, tc in enumerate(last_ai.tool_calls):
            cfg = self.interrupt_on.get(tc.get("name") or "")
            if cfg is None:
                continue
            when = cfg.get("when")
            if when is not None and not when(tc, state):
                continue
            gated.append((idx, tc, cfg))
        if not gated:
            return ({_EDITED_TOOL_CALLS_KEY: {}} if state.get(_EDITED_TOOL_CALLS_KEY) else None)
        action_requests = []
        review_configs = []
        for _idx, tc, cfg in gated:
            desc = cfg.get("description")
            if callable(desc):
                desc = desc(tc, state)
            action_requests.append(_hitl_action_request(tc, desc or ""))
            review_configs.append({"allowed_decisions": list(cfg["allowed_decisions"])})
        hitl_request = {"action_requests": action_requests, "review_configs": review_configs,
                        "reviewer": _HITL_REVIEWER}
        answer = interrupt(hitl_request)
        decisions = (answer or {}).get("decisions") if isinstance(answer, dict) else None
        if decisions is None:
            raise ValueError(
                "the human answer must be a dict {'decisions': [...]} with one decision "
                "per gated tool call")
        if len(decisions) != len(gated):
            raise ValueError(
                f"Number of human decisions ({len(decisions)}) does not match number of "
                f"hanging tool calls ({len(gated)}).")
        revised: list[dict] = []
        artificial: list[ToolMessage] = []
        edited: dict[str, dict] = {}
        di = 0
        for idx, tc in enumerate(last_ai.tool_calls):
            hit = next((g for g in gated if g[0] == idx), None)
            if hit is None:
                revised.append(dict(tc))
                continue
            _idx, _tc, cfg = hit
            decision = decisions[di] or {"type": "reject"}
            di += 1
            kind = decision.get("type")
            allowed = cfg["allowed_decisions"]
            if kind not in allowed:
                raise ValueError(
                    f"Unexpected human decision: {decision}. Decision type {kind!r} is not "
                    f"allowed for tool {tc.get('name')!r}. Expected one of {allowed}.")
            if kind in ("approve", "edit"):
                if kind == "edit":
                    edited[tc.get("id") or ""] = dict(decision.get("edited_action") or {})
                revised.append(dict(tc))
            else:
                revised.append(dict(tc))  # the call stays on the message; the
                artificial.append(_hitl_answer_message(tc, decision))  # answer closes it
        rebuilt = _rewrite_messages(messages, lambda ms: _replace_last_ai(ms, revised))
        return {"messages": [*rebuilt, *artificial], _EDITED_TOOL_CALLS_KEY: edited}

    def wrap_tool_call(self, request: ToolCallRequest,
                       handler: Callable[[ToolCallRequest], Any]) -> Any:
        """The execution half: substitute the reviewer's edited args at tool
        time and mark the result (reads the private channel off the state)."""
        edited = (request.state or {}).get(_EDITED_TOOL_CALLS_KEY) or {}
        tc = request.tool_call
        action = edited.get(tc.get("id") or "")
        if action:
            req = ToolCallRequest(
                tool_call={**tc, "args": dict((action or {}).get("args") or {})},
                tool=request.tool, state=request.state, runtime=request.runtime)
            out = handler(req)
            if isinstance(out, ToolMessage):
                return ToolMessage(content=f"{EDITED_RESULT_PREFIX}{out.content}",
                                   tool_call_id=out.tool_call_id, name=out.name,
                                   status=out.status)
            return out
        return handler(request)


def _replace_last_ai(messages: list[Any], revised_calls: list[dict]) -> list[Any]:
    """Return the lane with the LAST AIMessage carrying revised tool_calls."""
    out = list(messages)
    for i in range(len(out) - 1, -1, -1):
        if isinstance(out[i], AIMessage):
            try:
                out[i] = out[i].model_copy(update={"tool_calls": list(revised_calls)})
            except Exception:  # noqa: BLE001 - non-pydantic lookalikes get rebuilt
                out[i] = AIMessage(content=out[i].content, id=out[i].id,
                                   tool_calls=list(revised_calls))
            return out
    return out


# ---------------------------------------------------------------------------
# TIER 7 - todo (planning) + context editing
# ---------------------------------------------------------------------------


WRITE_TODOS_SYSTEM_PROMPT = (
    "Use the write_todos tool to plan and track multi-step work: one item per "
    "task, mark items in_progress before starting and completed when done. "
    "Skip the tool for trivial single-step asks.")

_WRITE_TODOS_DESCRIPTION = (
    "Use this tool to create and manage a structured task list for your current "
    "work session. Skip it when the request is trivial (fewer than 3 steps).")


class TodoListMiddleware(AgentMiddleware):
    """The write_todos planning tool (the upstream todo.py shape): a todos
    channel on the state + the tool + the system prompt rider."""

    state_schema = {"todos": list}

    def __init__(self, *, system_prompt: str = WRITE_TODOS_SYSTEM_PROMPT,
                 tool_description: str = _WRITE_TODOS_DESCRIPTION) -> None:
        self.system_prompt = system_prompt
        self.tool_description = tool_description

        def _write_todos(todos: list[dict]) -> str:
            if not isinstance(todos, list):
                raise ValueError("todos must be a list of {content, status} items")
            for t in todos:
                if not isinstance(t, dict) or "content" not in t:
                    raise ValueError("each todo needs a content")
                if t.get("status", "pending") not in ("pending", "in_progress", "completed"):
                    raise ValueError(f"unknown todo status {t.get('status')!r}")
            return "Updated todo list"

        self._impl = _write_todos
        self.tools = (
            _tool_decorator(_write_todos, name="write_todos", description=tool_description),)

    def wrap_model_call(self, request: ModelRequest,
                        handler: Callable[[ModelRequest], Any]) -> Any:
        if request.system_message is not None:
            merged = SystemMessage(
                content=f"{request.system_message.text}\n\n{self.system_prompt}")
        else:
            merged = SystemMessage(content=self.system_prompt)
        return handler(request.override(system_message=merged))


_DEFAULT_TOOL_PLACEHOLDER = "[Tool result cleared to reduce context]"


@dataclass(slots=True)
class ClearToolUsesEdit:
    """Clear old tool outputs past a token trigger (the upstream shape):
    keep the newest `keep` results, optionally clear the AI's args too."""

    trigger: int = 100_000
    clear_at_least: int = 0
    keep: int = 3
    clear_tool_inputs: bool = False
    exclude_tools: tuple[str, ...] = ()
    placeholder: str = _DEFAULT_TOOL_PLACEHOLDER

    def apply(self, messages: list[Any], *, count_tokens: Callable) -> tuple[list[Any], bool]:
        total = count_tokens(messages)
        if total <= self.trigger:
            return messages, False
        changed = False
        out = [m for m in messages]
        candidates = [(i, m) for i, m in enumerate(out) if isinstance(m, ToolMessage)]
        if self.keep >= len(candidates):
            candidates = []
        elif self.keep:
            candidates = candidates[: -self.keep]
        excluded = set(self.exclude_tools)
        cleared_tokens = 0
        for i, tm in candidates:
            if tm.response_metadata.get("context_editing", {}).get("cleared"):
                continue
            name = tm.name
            if name in excluded:
                continue
            ai = next((m for m in reversed(out[:i]) if isinstance(m, AIMessage)), None)
            if self.clear_tool_inputs and ai is not None:
                calls = [dict(c) for c in (ai.tool_calls or [])]
                for c in calls:
                    if c.get("id") == tm.tool_call_id:
                        c["args"] = {}
                        changed = True
                if calls != list(ai.tool_calls or []):
                    out[out.index(ai)] = AIMessage(content=ai.content, id=ai.id, tool_calls=calls)
            out[i] = ToolMessage(content=self.placeholder, tool_call_id=tm.tool_call_id,
                                 name=name, status=tm.status,
                                 response_metadata={**tm.response_metadata,
                                                    "context_editing": {"cleared": True}})
            cleared_tokens += count_tokens([tm])
            changed = True
        if self.clear_at_least and cleared_tokens < self.clear_at_least:
            return messages, False
        return out, changed


class ContextEditingMiddleware(AgentMiddleware):
    """Clear stale tool outputs past a token trigger (the upstream
    context_editing.py shape, the Anthropic clear_tool_uses_20250919 idea):
    applied on the request inside wrap_model_call - state stays untouched."""

    def __init__(self, *, edits: list[ClearToolUsesEdit] | None = None,
                 token_counter: Callable | None = None) -> None:
        self.edits = list(edits) if edits is not None else [ClearToolUsesEdit()]
        self.token_counter = token_counter or _approx_token_counter

    def wrap_model_call(self, request: ModelRequest,
                        handler: Callable[[ModelRequest], Any]) -> Any:
        messages = list(request.messages)
        for edit in self.edits:
            messages, changed = edit.apply(messages, count_tokens=self.token_counter)
            if not changed:
                break
        return handler(request.override(messages=messages))


# ---------------------------------------------------------------------------
# TIER 8 - file search + provider tool search + shell
# ---------------------------------------------------------------------------


class FilesystemFileSearchMiddleware(AgentMiddleware):
    """Glob + Grep tools over a root path (the upstream file_search.py shape,
    the stdlib lane): a size cap, binary files skipped, ripgrep when asked for
    and present."""

    def __init__(self, *, root_path: str = ".", use_ripgrep: bool = False,
                 max_file_size_mb: float = 5.0) -> None:
        self.root_path = str(Path(root_path).resolve())
        self.use_ripgrep = use_ripgrep
        self.max_file_size_mb = max_file_size_mb
        root = self.root_path
        cap = max_file_size_mb

        def _iter_files(base: str) -> list[Path]:
            rootp = Path(base)
            out: list[Path] = []
            capb = int(cap * 1024 * 1024)
            for p in sorted(rootp.rglob("*")):
                try:
                    if not p.is_file():
                        continue
                    if p.stat().st_size > capb:
                        continue
                    with open(p, "rb") as fh:
                        if b"\x00" in fh.read(1024):
                            continue
                    out.append(p)
                except OSError:
                    continue
            return out

        def glob_search(pattern: str, path: str = "/") -> str:
            """Fast pattern-based file search (fnmatch-style globs)."""
            base = root if path in ("/", ".", "") else str(Path(root, path.lstrip("/")))
            hits = [str(p.relative_to(root)) for p in _iter_files(base)
                    if p.match(pattern) or Path(p.name).match(pattern)]
            return "\n".join(hits) if hits else "No files found"

        def grep_search(pattern: str, path: str = "/") -> str:
            """Fast content search tool - regular expression over text files."""
            import re as _re
            try:
                rx = _re.compile(pattern)
            except _re.error as e:
                return f"Invalid regex: {e}"
            base = root if path in ("/", ".", "") else str(Path(root, path.lstrip("/")))
            lines: list[str] = []
            for p in _iter_files(base)[:2000]:
                try:
                    with open(p, encoding="utf-8", errors="replace") as fh:
                        for n, line in enumerate(fh, 1):
                            if rx.search(line):
                                lines.append(f"{p.relative_to(root)}:{n}: {line.rstrip()[:200]}")
                                if len(lines) >= 200:
                                    return "\n".join(lines)
                except OSError:
                    continue
            return "\n".join(lines) if lines else "No matches found"

        glob_search.__name__ = "glob_search"
        grep_search.__name__ = "grep_search"
        self.tools = (
            _tool_decorator(glob_search, name="glob_search"),
            _tool_decorator(grep_search, name="grep_search"),
        )


class ProviderToolSearchMiddleware(AgentMiddleware):
    """Mark selected tools deferred behind provider-native tool search (the
    upstream provider_tool_search.py idea, the honest house form): the wire
    itself is the P7 HUB's ledger - here the request is validated and the
    selected tools are tagged extras defer_loading so the wire lane can act."""

    _PROVIDERS = {"anthropic", "openai"}

    def __init__(self, *, tools: list[Any], defer_loading: bool = True) -> None:
        if not tools:
            raise ValueError("ProviderToolSearchMiddleware needs at least one tool to defer")
        self.defer_names: set[str] = set()
        for t in tools:
            self.defer_names.add(t if isinstance(t, str) else t.name)
        self.defer_loading = defer_loading

    @staticmethod
    def _provider_of(model: Any) -> str | None:
        lt = str(getattr(model, "_llm_type", "") or "")
        for p in ProviderToolSearchMiddleware._PROVIDERS:
            if p in lt.lower():
                return p
        return None

    def wrap_model_call(self, request: ModelRequest,
                        handler: Callable[[ModelRequest], Any]) -> Any:
        tools = list(request.tools or [])
        provider = self._provider_of(request.model)
        if provider is None:
            raise ValueError(
                "ProviderToolSearchMiddleware: the bound model's provider does not "
                "advertise server-side tool search - deferred tools would be "
                "unreachable (supported: anthropic, openai; the wire is the P7 HUB's)")
        tagged = []
        for t in tools:
            name = t if isinstance(t, str) else getattr(t, "name", "")
            if name in self.defer_names and self.defer_loading:
                if isinstance(t, dict):
                    tagged.append({**t, "extras": {**(t.get("extras") or {}),
                                                   "defer_loading": True}})
                    continue
                tagged.append(t)
            else:
                tagged.append(t)
        return handler(request.override(tools=tagged))


_DEFAULT_SHELL_DESCRIPTION = (
    "Run a shell command and return its output. Use for quick, read-only style "
    "checks; every run is bounded by a timeout and an output cap.")


class ShellToolMiddleware(AgentMiddleware):
    """One bounded shell tool (the upstream shell_tool.py idea, the house form):
    subprocess with a hard timeout, an output cap, a cwd and an env override -
    voice never sees it (the VOICE_TOOL_NAMES allowlist keeps it out of calls)."""

    def __init__(self, *, shell: str = "/bin/bash", timeout_s: float = 30.0,
                 max_output_chars: int = 8000, workdir: str | None = None,
                 env: dict[str, str] | None = None,
                 tool_description: str = _DEFAULT_SHELL_DESCRIPTION) -> None:
        import shutil
        if not shutil.which(shell):
            raise ValueError(f"shell {shell!r} not found on PATH")
        self.shell = shell
        self.timeout_s = timeout_s
        self.max_output_chars = max_output_chars
        self.workdir = workdir
        self.env = env

        def shell_execute(command: str, timeout: float = 0.0) -> str:
            """Execute one shell command; returns stdout+stderr with the exit code."""
            run_timeout = float(timeout or 0) or self.timeout_s
            try:
                proc = subprocess.run(  # noqa: S603 - the tool's own purpose
                    [self.shell, "-c", command],
                    capture_output=True, text=True, timeout=run_timeout,
                    cwd=self.workdir, env=self.env,
                )
            except subprocess.TimeoutExpired:
                return f"Command timed out after {run_timeout}s"
            out = (proc.stdout or "") + (proc.stderr or "")
            if len(out) > self.max_output_chars:
                out = out[: self.max_output_chars] + f"\n... [output capped at {self.max_output_chars} chars]"
            return f"{out}\n[exit code: {proc.returncode}]".strip()

        shell_execute.__name__ = "shell_execute"
        self.tools = (
            _tool_decorator(shell_execute, name="shell_execute",
                            description=tool_description),)


# ---------------------------------------------------------------------------
# THE UNIFICATION - nudge / curator / delegate / skills-primer collapse into
# middlewares on the one loop
# ---------------------------------------------------------------------------


class NudgeMiddleware(AgentMiddleware):
    """The house nudge as a hook: a steering note joins the system message on
    every model call (or every n-th - every_n); her own words stay hers. The
    nudge may be a fixed string, a callable(state) -> str|None, or None to
    mute."""

    def __init__(self, nudge: str | Callable | None = None, *, every_n: int = 1) -> None:
        if every_n < 1:
            raise ValueError("every_n must be >= 1")
        self.nudge = nudge
        self.every_n = every_n
        self._count = 0

    def _nudge_text(self, state: dict) -> str | None:
        if self.nudge is None:
            return None
        if callable(self.nudge):
            return self.nudge(state)
        return self.nudge

    def wrap_model_call(self, request: ModelRequest,
                        handler: Callable[[ModelRequest], Any]) -> Any:
        self._count += 1
        if self.every_n > 1 and (self._count - 1) % self.every_n != 0:
            return handler(request)
        text = self._nudge_text(request.state)
        if not text:
            return handler(request)
        merged = SystemMessage(
            content=(f"{request.system_message.text}\n\n{nudge_block(text)}"
                     if request.system_message is not None else nudge_block(text)))
        return handler(request.override(system_message=merged))


def nudge_block(text: str) -> str:
    return f"<nudge>\n{text}\n</nudge>"


class CuratorMiddleware(AgentMiddleware):
    """The house curator as a hook: after_agent folds the conversation the
    curator's way - duplicate tool-result noise collapses (same tool + same
    text), the lane is capped at max_messages with AI/Tool pairs kept whole,
    and folds are marked in the surviving messages."""

    def __init__(self, *, max_messages: int = 200, max_result_chars: int = 4000,
                 min_duplicates: int = 2) -> None:
        self.max_messages = max_messages
        self.max_result_chars = max_result_chars
        self.min_duplicates = min_duplicates

    def _fold(self, messages: list[Any]) -> list[Any]:
        out: list[Any] = []
        seen: dict[tuple, int] = {}
        for m in messages:
            if isinstance(m, ToolMessage):
                text = _text_of(m.content)
                if len(text) > self.max_result_chars:
                    m = ToolMessage(content=text[: self.max_result_chars] + "... [folded]",
                                    tool_call_id=m.tool_call_id, name=m.name,
                                    status=m.status, id=m.id)
                    text = _text_of(m.content)
                key = ("tool", m.name, text)
                seen[key] = seen.get(key, 0) + 1
                if seen[key] > self.min_duplicates:
                    continue  # the duplicate noise collapses
            out.append(m)
        if len(out) > self.max_messages:
            cut = self._safe_cut(out, len(out) - self.max_messages)
            out = out[cut:]
        return out

    @staticmethod
    def _safe_cut(messages: list[Any], target: int) -> int:
        cut = max(0, target)
        while cut < len(messages) and isinstance(messages[cut], ToolMessage):
            cut += 1
        return cut

    def after_agent(self, state: dict, runtime: dict) -> dict | None:  # noqa: ARG002
        messages = list(state.get("messages") or [])
        folded = self._fold(messages)
        if folded == messages:
            return None
        for m in folded:
            # the fold is marked on every surviving tool result (the lane was
            # curated this run)
            if isinstance(m, ToolMessage):
                m.response_metadata = {**m.response_metadata, "curator": {"folded": True}}
        return {"messages": _rewrite_messages(messages, lambda ms: folded)}


DELEGATE_TASK_DESCRIPTION = (
    "Hand task prompts to parallel workers. Each worker runs bounded and "
    "returns one result line; a failed worker is one failed result, never a "
    "crashed batch.")


class DelegateMiddleware(AgentMiddleware):
    """The house delegate_task as a middleware-registered tool (the
    coder/delegate shape, flat by default): one tool, N task prompts, each run
    through the worker callable, MAX_DEPTH=1 (children never re-delegate - the
    tool refuses inside a worker run), concurrency-capped sequential execution,
    fail-open per child."""

    MAX_DEPTH = 1

    def __init__(self, *, worker: Callable[[str], str], max_children: int = 3,
                 timeout_s: float = 120.0, tool_description: str = DELEGATE_TASK_DESCRIPTION) -> None:
        if not callable(worker):
            raise TypeError("worker must be a callable task_prompt -> result str")
        self.worker = worker
        self.max_children = max(1, int(max_children))
        self.timeout_s = timeout_s
        self._depth = 0

        def delegate_task(tasks: list[str]) -> str:
            """Hand task prompts to bounded parallel workers and merge results."""
            if not isinstance(tasks, list) or not tasks:
                raise ValueError("tasks must be a non-empty list of task prompts")
            if self._depth >= DelegateMiddleware.MAX_DEPTH:
                raise ValueError("a delegated worker cannot delegate again (MAX_DEPTH=1)")
            if len(tasks) > self.max_children:
                raise ValueError(
                    f"too many tasks: {len(tasks)} (max {self.max_children}) - split the batch")
            self._depth += 1
            results: list[dict] = []
            try:
                for i, task in enumerate(tasks):
                    started = time.time()
                    try:
                        out = self.worker(str(task))
                        results.append({"task": i, "ok": True, "result": str(out),
                                        "elapsed_s": round(time.time() - started, 2)})
                    except (GraphInterrupt, GraphRecursionError):
                        raise
                    except Exception as e:  # noqa: BLE001 - fail-open per child
                        results.append({"task": i, "ok": False, "error": str(e),
                                        "elapsed_s": round(time.time() - started, 2)})
            finally:
                self._depth -= 1
            return json.dumps({"results": results}, default=str)

        delegate_task.__name__ = "delegate_task"
        self.tools = (
            _tool_decorator(delegate_task, name="delegate_task",
                            description=tool_description),)


class SkillsPrimerMiddleware(AgentMiddleware):
    """The house skills primer as a hook: name/keyword-matched skill text joins
    the system message every model call. primers maps a skill name to its text
    (hers win: a user-provided primers dict is the ONLY source - the middleware
    invents nothing); `match` picks primers whose name or keywords appear in the
    conversation or in the caller-supplied matcher."""

    def __init__(self, primers: dict[str, str] | None = None, *,
                 match: Callable[[dict], list[str]] | None = None,
                 max_chars: int = 2000) -> None:
        self.primers = dict(primers or {})
        self.match = match or self._default_match
        self.max_chars = max_chars

    def _default_match(self, state: dict) -> list[str]:
        text = " ".join(_text_of(getattr(m, "content", "")) for m in (state.get("messages") or [])[-6:]
                        ).lower()
        hits = [name for name in self.primers if name.lower() in text]
        return hits

    def wrap_model_call(self, request: ModelRequest,
                        handler: Callable[[ModelRequest], Any]) -> Any:
        names = [n for n in self.match(request.state) if n in self.primers]
        if not names:
            return handler(request)
        blocks: list[str] = []
        total = 0
        for n in names:
            text = self.primers[n]
            if total + len(text) > self.max_chars:
                break
            blocks.append(f"<skill name=\"{n}\">\n{text}\n</skill>")
            total += len(text)
        if not blocks:
            return handler(request)
        primer = "\n\n".join(blocks)
        merged = SystemMessage(
            content=(f"{request.system_message.text}\n\n{primer}"
                     if request.system_message is not None else primer))
        return handler(request.override(system_message=merged))
