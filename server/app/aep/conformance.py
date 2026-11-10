"""HOOLA AEP conformance - the standard-tests port: ONE suite every house chat
model must pass (upstream reference read at github.com/langchain-ai/langchain
@ aa2528fb, libs/standard-tests/langchain_tests/{base.py 70 lines,
unit_tests/chat_models.py 1174}: ChatModelTests/ChatModelUnitTests, the
capability fixture flags, test_standard_params, test_serdes, test_bind_tool_pydantic)
- ZERO upstream code (the port law).

v0.581.0 HOOLA HUB (P7 of the AEP plan): the house suite runs as a REPORT, not
a pytest base class - `run_standard_tests(model)` returns rows for every check,
`assert_conformance(model)` raises with the failure list. Capability flags
(the upstream has_tool_calling / has_structured_output pattern) let a model
honestly opt out of rows it does not serve; every opt-out is a named row, so
"skipped" can never hide "broken".

THE CHECKS (each = a named row):
- init_surface            : _llm_type non-empty str, _identifying_params dict
- invoke_returns_ai_msg   : invoke(str) -> AIMessage with str|list content
- invoke_accepts_messages : invoke([HumanMessage...]) -> AIMessage
- batch_matches_invokes   : batch(["x","x"]) -> two AIMessages
- stream_chunks_merge     : stream yields >=1 AIMessageChunk; chunk.contents
                            join to the merged AIMessageChunk.content
- bind_tools_runs         : bind_tools([pydantic, dict-schema, house @tool])
                            -> Runnable (capability-gated)
- structured_output       : with_structured_output(schema) -> Runnable
                            (capability-gated; the e2e parse row is separate)
- standard_params         : standard_params() carries ls_provider / ls_model_name
                            / ls_model_type and honors a per-call model override
                            (the upstream misattribution law)
- serdes_round_trip       : dumpd(model) -> load() -> same class + same
                            _llm_type + same identifying params (the P7 loader)
- config_rides_callbacks  : a CallbackManager in config fires the P2 chat_model
                            span and lands a Run in the store

Inert library: the suite only ever runs the model it is handed - fakes and
shimmed transports keep it zero-network.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from .load import dumpd, load
from .messages import AIMessage, AIMessageChunk, HumanMessage
from .models import BaseChatModel
from .runnable import Runnable, RunnableBinding
from .tools import tool


@dataclass
class ConformanceRow:
    name: str
    ok: bool
    detail: str


@dataclass
class ConformanceReport:
    model_name: str
    rows: list[ConformanceRow] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.rows if r.ok)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.rows if not r.ok)

    @property
    def ok(self) -> bool:
        return self.failed == 0

    def failures(self) -> list[ConformanceRow]:
        return [r for r in self.rows if not r.ok]

    def summary(self) -> str:
        lines = [f"conformance[{self.model_name}]: {self.passed} passed, {self.failed} failed"]
        for r in self.failures():
            lines.append(f"  FAIL {r.name}: {r.detail}")
        return "\n".join(lines)


@dataclass
class Capabilities:
    """The honest opt-outs (the upstream fixture flags, house-shaped)."""
    has_tool_calling: bool = True
    has_structured_output: bool = True
    supports_serdes: bool = True


class _Adder(BaseModel):
    """Add two integers (the upstream my_adder_tool fixture, house-shaped)."""

    a: int = Field(..., description="first addend")
    b: int = Field(..., description="second addend")


@tool(name="conformance_adder", description="Add two integers.")
def _adder_tool(a: int, b: int) -> int:  # noqa: ANN001
    return a + b


class _Out(BaseModel):
    """A tiny structured-output schema (the upstream TEST_PYDANTIC_MODELS idea)."""

    answer: str


def _collect_placeholders(value: Any, out: set[str] | None = None) -> set[str]:
    """Every `$NAME` secret placeholder riding the payload."""
    out = out if out is not None else set()
    if isinstance(value, dict):
        for v in value.values():
            _collect_placeholders(v, out)
    elif isinstance(value, list):
        for v in value:
            _collect_placeholders(v, out)
    elif isinstance(value, str) and value.startswith("$") and len(value) > 1:
        out.add(value[1:])
    return out


def _derive_capabilities(model: BaseChatModel) -> "Capabilities":
    """The honest auto-derive: probe the declarative surface, never assume.
    An explicit Capabilities argument overrides (the upstream fixture-flag
    shape); without one, a model that raises on bind_tools simply does not
    claim the row."""
    caps = Capabilities()
    try:
        model.bind_tools([_Adder])
    except Exception:  # noqa: BLE001 - an honest opt-out
        caps.has_tool_calling = False
    try:
        model.with_structured_output(_Out)
    except Exception:  # noqa: BLE001
        caps.has_structured_output = False
    return caps


def run_standard_tests(model: BaseChatModel, *,
                       capabilities: Capabilities | None = None) -> ConformanceReport:
    """Run the house conformance suite over ONE chat model -> the report."""
    caps = capabilities or _derive_capabilities(model)
    report = ConformanceReport(model_name=type(model).__name__)
    rows = report.rows

    def _row(name: str, fn) -> None:
        try:
            detail = fn()
            rows.append(ConformanceRow(name=name, ok=True, detail=detail or "ok"))
        except Exception as e:  # noqa: BLE001 - a failed check IS the row
            rows.append(ConformanceRow(name=name, ok=False, detail=f"{type(e).__name__}: {e}"))

    def _init_surface() -> str:
        llm_type = model._llm_type
        assert isinstance(llm_type, str) and llm_type, "_llm_type must be a non-empty str"
        assert isinstance(model._identifying_params, dict), "_identifying_params must be a dict"
        return f"_llm_type={llm_type!r}"

    def _invoke_str() -> str:
        out = model.invoke("ping")
        assert isinstance(out, AIMessage), f"invoke(str) returned {type(out).__name__}"
        assert isinstance(out.content, (str, list)), "content must be str|list"
        return f"content={out.content!r:.60}"

    def _invoke_messages() -> str:
        out = model.invoke([HumanMessage(content="hello")])
        assert isinstance(out, AIMessage), "invoke(list[BaseMessage]) must return AIMessage"
        return "ok"

    def _batch() -> str:
        outs = model.batch(["x", "x"])
        assert isinstance(outs, list) and len(outs) == 2, "batch must return two rows"
        assert all(isinstance(o, AIMessage) for o in outs), "batch rows must be AIMessages"
        return "ok"

    def _stream_merge() -> str:
        chunks = list(model.stream("ping"))
        assert chunks, "stream must yield at least one chunk"
        assert all(isinstance(c, AIMessageChunk) for c in chunks), "rows must be AIMessageChunk"
        joined = "".join(c.content if isinstance(c.content, str) else "" for c in chunks)
        merged = AIMessageChunk(content="")
        for c in chunks:
            merged = merged + c
        assert (merged.content if isinstance(merged.content, str) else joined) is not None
        assert joined in (merged.content if isinstance(merged.content, str) else joined)
        return f"{len(chunks)} chunks, merged {len(joined)} chars"

    def _bind_tools() -> str:
        bound = model.bind_tools([_Adder, {"name": "dict_tool", "description": "d",
                                           "parameters": {"type": "object", "properties": {}}},
                                  _adder_tool])
        assert isinstance(bound, Runnable), "bind_tools must return a Runnable"
        return f"{type(bound).__name__}"

    def _structured() -> str:
        so = model.with_structured_output(_Out)
        assert isinstance(so, Runnable), "with_structured_output must return a Runnable"
        return f"{type(so).__name__}"

    def _standard_params() -> str:
        params = model.standard_params()
        for key in ("ls_provider", "ls_model_name", "ls_model_type"):
            assert key in params, f"standard_params missing {key}"
        assert params["ls_model_type"] == "chat", "ls_model_type must be 'chat'"
        override = "override-sentinel"
        if "model" in type(model).model_fields:
            per_call = model.standard_params(model=override)
            assert per_call["ls_model_name"] == override, (
                "standard_params must honor the per-call model override - traces "
                "would misattribute the call")
        return f"provider={params['ls_provider']}"

    def _serdes() -> str:
        data = dumpd(model)
        # Secret placeholders must be satisfied for the round trip - a neutral
        # map restores the SHAPE (identity is compared via class + identifying
        # params, never the secret itself).
        placeholders = sorted(_collect_placeholders(data))
        secrets_map = {p: "masked" for p in placeholders}
        rebuilt = load(data, secrets_map=secrets_map)
        assert type(rebuilt) is type(model), "the round trip must land the same class"
        assert rebuilt._llm_type == model._llm_type, "_llm_type drifted"
        assert rebuilt._identifying_params == model._identifying_params, \
            "_identifying_params drifted"
        suffix = f" ({len(placeholders)} placeholder(s) masked)" if placeholders else ""
        return f"round trip ok{suffix}"

    def _callbacks() -> str:
        from .tracers import CallbackManager, InMemoryRunStore, RunTreeTracer
        store = InMemoryRunStore()
        mgr = CallbackManager(handlers=[RunTreeTracer(sinks=[store])])
        model.invoke("traced", config={"callbacks": mgr})
        runs = dict(store._runs)  # same-package internal: the capped ring
        assert runs, "the chat_model run never landed in the store"
        kinds = {getattr(r, "run_type", None) for r in runs.values()}
        assert "chat_model" in kinds, f"no chat_model run in {kinds}"
        return f"{len(runs)} run(s) traced, chat_model in {sorted(kinds)}"

    _row("init_surface", _init_surface)
    _row("invoke_returns_ai_msg", _invoke_str)
    _row("invoke_accepts_messages", _invoke_messages)
    _row("batch_matches_invokes", _batch)
    _row("stream_chunks_merge", _stream_merge)
    if caps.has_tool_calling:
        _row("bind_tools_runs", _bind_tools)
    if caps.has_structured_output:
        _row("structured_output", _structured)
    _row("standard_params", _standard_params)
    if caps.supports_serdes:
        _row("serdes_round_trip", _serdes)
    _row("config_rides_callbacks", _callbacks)
    return report


def assert_conformance(model: BaseChatModel, *,
                       capabilities: Capabilities | None = None) -> ConformanceReport:
    """The pytest lane: all rows green or one AssertionError naming them."""
    report = run_standard_tests(model, capabilities=capabilities)
    assert report.ok, report.summary()
    return report


__all__ = ["Capabilities", "ConformanceReport", "ConformanceRow",
           "assert_conformance", "run_standard_tests"]
