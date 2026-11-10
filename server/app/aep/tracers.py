"""HOOLA AEP tracers - the LangSmith layer self-hosted (v0.521.0 HOOLA TRACE, P2 of
the AEP plan). The langchain-core callbacks + tracers + event-stream idea and the
LangSmith run-tree idea hand-built (upstream reference: callbacks/manager.py
CallbackManager + BaseCallbackHandler, tracers/base.py BaseTracer, tracers/
event_stream.py astream_events v2, langsmith Run schema). ZERO upstream code or
imports (the port law that built P1).

What lives here:

- Run            : one execution node - id, name, run_type, inputs/outputs, error,
                   start/end, parent_run_id, trace_id, tags, metadata, child_ids.
                   The tree is the parent linkage; `tree(run_id)` nests children.
- BaseCallbackHandler : the on_* family (chain / chat model / llm token / tool /
                   text), every method a no-op by default, subscriber style.
- CallbackManager: carries the handler list + the parent_run_id down the config
                   channel ("callbacks"). A span start returns the CHILD manager -
                   that child is what children see in their config, which is how
                   the tree assembles itself with zero registry lookups.
- Span           : the fire-point seam used by Runnable / BaseChatModel / BaseTool.
                   Span.start fires *_start and yields the span; span.end /
                   span.error / span.token fire the closes. When the config carries
                   no callbacks the call sites never construct a Span - the P1
                   fast path is byte-identical and the import stays lazy.
- RunTreeTracer  : the handler that BUILDS the tree (runs dict + persistence to
                   sinks on every finished run).
- InMemoryRunStore: thread-safe capped ring (aep_trace_max_runs, default 500).
- astream_events : the event_stream.py v2 port - an async generator of event dicts
                   (on_chain_start / on_chat_model_start / on_llm_new_token /
                   on_chain_stream / on_chain_end / on_tool_start / on_tool_end,
                   each with run_id + parent_ids + data.input/output/chunk).

THE FLAG LAW (the P1 inertness note made real): the library here stays inert - a
fresh interpreter imports it with zero threads, zero env reads, zero files. What
the flag (aep_trace, default OFF) gates is PERSISTENCE: the vault sink in
vault_sink.py and the /api/aep/runs explorer route. Explicit opt-in tracers in
process are library behavior, exactly like P1's classes.

Redaction is the caller's law for sinks (see vault_sink.py): run IO can carry her
words, so strip_private + redact_secrets run BEFORE a row lands - redaction before
storage, the docs7 egress law pointed inward.
"""
from __future__ import annotations

import asyncio
import dataclasses
import json
import threading
import time
import uuid
from typing import Any, Callable, Iterator

# the langsmith run_type vocabulary (their public Run schema)
RUN_TYPES = ("chain", "llm", "chat_model", "tool", "retriever", "embeddings",
             "prompt", "parser", "agent")
DEFAULT_STORE_CAP = 500


# ---------------------------------------------------------------------------
# the run node
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class Run:
    """One execution node of the run tree (the LangSmith Run, reduced to what a
    self-hosted explorer needs)."""

    id: str
    name: str
    run_type: str
    inputs: Any = None
    outputs: Any = None
    error: str | None = None
    start_time: float = dataclasses.field(default_factory=time.time)
    end_time: float | None = None
    parent_run_id: str | None = None
    trace_id: str = ""
    tags: list[str] = dataclasses.field(default_factory=list)
    metadata: dict[str, Any] = dataclasses.field(default_factory=dict)
    child_ids: list[str] = dataclasses.field(default_factory=list)

    @property
    def ms(self) -> int:
        if self.end_time is None:
            return 0
        return int((self.end_time - self.start_time) * 1000)

    @property
    def status(self) -> str:
        if self.error is not None:
            return "error"
        return "ok" if self.end_time is not None else "running"

    def to_dict(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        d["ms"] = self.ms
        d["status"] = self.status
        return d


def dumps_safe(obj: Any) -> str:
    """JSON for run IO: BaseMessage / Serializable / pydantic shapes flattened, the
    rest str()-fallback - a tracer NEVER raises on odd payloads."""
    try:
        return json.dumps(_plain(obj), default=str, ensure_ascii=False)
    except Exception:  # noqa: BLE001 - telemetry is best-effort by contract
        return str(obj)[:2000]


def _plain(obj: Any, depth: int = 0) -> Any:
    if depth > 8:
        return str(obj)[:500]
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _plain(v, depth + 1) for k, v in list(obj.items())[:64]}
    if isinstance(obj, (list, tuple)):
        return [_plain(v, depth + 1) for v in list(obj)[:64]]
    to_dict = getattr(obj, "to_dict", None)          # BaseMessage / Serializable
    if callable(to_dict):
        try:
            return _plain(to_dict(), depth + 1)
        except Exception:  # noqa: BLE001
            pass
    model_dump = getattr(obj, "model_dump", None)    # pydantic
    if callable(model_dump):
        try:
            return _plain(model_dump(), depth + 1)
        except Exception:  # noqa: BLE001
            pass
    return str(obj)[:500]


# ---------------------------------------------------------------------------
# handlers + the manager
# ---------------------------------------------------------------------------


class BaseCallbackHandler:
    """Subscriber style: every method a no-op; override what you trace. A handler
    that raises is swallowed by the manager (telemetry never breaks the run)."""

    def on_chain_start(self, name: str, run_id: str, parent_run_id: str | None,
                       inputs: Any, tags: list[str], metadata: dict) -> None: ...
    def on_chain_stream(self, name: str, run_id: str, chunk: Any) -> None: ...
    def on_chain_end(self, name: str, run_id: str, outputs: Any) -> None: ...
    def on_chain_error(self, name: str, run_id: str, error: str) -> None: ...
    def on_chat_model_start(self, name: str, run_id: str, parent_run_id: str | None,
                            messages: Any, tags: list[str], metadata: dict) -> None: ...
    def on_llm_new_token(self, name: str, run_id: str, token: str) -> None: ...
    def on_llm_end(self, name: str, run_id: str, output: Any) -> None: ...
    def on_llm_error(self, name: str, run_id: str, error: str) -> None: ...
    def on_tool_start(self, name: str, run_id: str, parent_run_id: str | None,
                      inputs: Any, tags: list[str], metadata: dict) -> None: ...
    def on_tool_end(self, name: str, run_id: str, output: Any) -> None: ...
    def on_tool_error(self, name: str, run_id: str, error: str) -> None: ...
    def on_text(self, text: str, run_id: str) -> None: ...


class CallbackManager:
    """The config["callbacks"] carrier. `parent_run_id` is the span this manager
    belongs to; Span.start hands children a manager whose parent is the new run."""

    def __init__(self, handlers: list[BaseCallbackHandler] | None = None,
                 parent_run_id: str | None = None,
                 tags: list[str] | None = None,
                 metadata: dict[str, Any] | None = None) -> None:
        self.handlers: list[BaseCallbackHandler] = list(handlers or [])
        self.parent_run_id = parent_run_id
        self.tags = list(tags or [])
        self.metadata = dict(metadata or {})

    def child(self, run_id: str) -> "CallbackManager":
        return CallbackManager(self.handlers, parent_run_id=run_id,
                               tags=self.tags, metadata=self.metadata)

    def _fire(self, method: str, *args: Any) -> None:
        for h in self.handlers:
            try:
                getattr(h, method)(*args)
            except Exception:  # noqa: BLE001 - a broken handler never breaks the run
                continue

    # the fire surface used by Span
    def chain_start(self, name: str, run_id: str, inputs: Any) -> None:
        self._fire("on_chain_start", name, run_id, self.parent_run_id, inputs,
                   self.tags, self.metadata)

    def chain_stream(self, name: str, run_id: str, chunk: Any) -> None:
        self._fire("on_chain_stream", name, run_id, chunk)

    def chain_end(self, name: str, run_id: str, outputs: Any) -> None:
        self._fire("on_chain_end", name, run_id, outputs)

    def chain_error(self, name: str, run_id: str, error: str) -> None:
        self._fire("on_chain_error", name, run_id, error)

    def chat_model_start(self, name: str, run_id: str, messages: Any) -> None:
        self._fire("on_chat_model_start", name, run_id, self.parent_run_id, messages,
                   self.tags, self.metadata)

    def llm_new_token(self, name: str, run_id: str, token: str) -> None:
        self._fire("on_llm_new_token", name, run_id, token)

    def llm_end(self, name: str, run_id: str, output: Any) -> None:
        self._fire("on_llm_end", name, run_id, output)

    def llm_error(self, name: str, run_id: str, error: str) -> None:
        self._fire("on_llm_error", name, run_id, error)

    def tool_start(self, name: str, run_id: str, inputs: Any) -> None:
        self._fire("on_tool_start", name, run_id, self.parent_run_id, inputs,
                   self.tags, self.metadata)

    def tool_end(self, name: str, run_id: str, output: Any) -> None:
        self._fire("on_tool_end", name, run_id, output)

    def tool_error(self, name: str, run_id: str, error: str) -> None:
        self._fire("on_tool_error", name, run_id, error)

    # the retriever fire surface (P6: RUN_TYPES pre-declared the run type in P2;
    # the chain fallback below stays untouched for every other type)
    def retriever_start(self, name: str, run_id: str, query: Any) -> None:
        self._fire("on_retriever_start", name, run_id, self.parent_run_id, query,
                   self.tags, self.metadata)

    def retriever_end(self, name: str, run_id: str, documents: Any) -> None:
        self._fire("on_retriever_end", name, run_id, documents)

    def retriever_error(self, name: str, run_id: str, error: str) -> None:
        self._fire("on_retriever_error", name, run_id, error)

    def text(self, text: str, run_id: str) -> None:
        self._fire("on_text", text, run_id)


def callbacks_from_config(config: dict | None) -> CallbackManager | None:
    """The one read of the config channel. Anything handler-shaped is accepted."""
    mgr = (config or {}).get("callbacks")
    if mgr is None:
        return None
    if isinstance(mgr, CallbackManager):
        return mgr
    if isinstance(mgr, BaseCallbackHandler):
        return CallbackManager([mgr])
    if isinstance(mgr, (list, tuple)) and mgr:
        return CallbackManager(list(mgr))
    return None


# ---------------------------------------------------------------------------
# the fire-point seam
# ---------------------------------------------------------------------------


class Span:
    """One executing node. Created ONLY when the config carries callbacks - the
    no-callback path never builds a uuid, a dict copy or a manager."""

    __slots__ = ("run_id", "name", "run_type", "mgr", "child_cfg")

    def __init__(self, run_id: str, name: str, run_type: str,
                 mgr: CallbackManager, child_cfg: dict) -> None:
        self.run_id = run_id
        self.name = name
        self.run_type = run_type
        self.mgr = mgr
        self.child_cfg = child_cfg

    @classmethod
    def start(cls, cfg: dict, obj: Any, run_type: str, inputs: Any) -> "Span | None":
        mgr = callbacks_from_config(cfg)
        if mgr is None:
            return None
        run_id = uuid.uuid4().hex
        name = obj.get_name() if hasattr(obj, "get_name") else type(obj).__name__
        if run_type == "tool" and getattr(obj, "name", None):
            name = str(obj.name)   # a tool run is named by its TOOL name, not its class
        child = mgr.child(run_id)
        child_cfg = {**cfg, "callbacks": child}
        if run_type in ("llm", "chat_model"):
            mgr.chat_model_start(name, run_id, inputs)
        elif run_type == "tool":
            mgr.tool_start(name, run_id, inputs)
        elif run_type == "retriever":
            mgr.retriever_start(name, run_id, inputs)
        else:
            mgr.chain_start(name, run_id, inputs)
        return cls(run_id, name, run_type, mgr, child_cfg)

    def token(self, chunk: Any) -> None:
        """A streamed piece: on_llm_new_token on a model span, on_chain_stream on a chain."""
        if self.run_type in ("llm", "chat_model"):
            tok = chunk.get("text") if isinstance(chunk, dict) else str(getattr(chunk, "content", chunk))
            self.mgr.llm_new_token(self.name, self.run_id, str(tok)[:400])
        else:
            self.mgr.chain_stream(self.name, self.run_id, chunk)

    def end(self, output: Any) -> None:
        if self.run_type in ("llm", "chat_model"):
            self.mgr.llm_end(self.name, self.run_id, output)
        elif self.run_type == "tool":
            self.mgr.tool_end(self.name, self.run_id, output)
        elif self.run_type == "retriever":
            self.mgr.retriever_end(self.name, self.run_id, output)
        else:
            self.mgr.chain_end(self.name, self.run_id, output)

    def error(self, exc: BaseException) -> None:
        text = f"{type(exc).__name__}: {exc}"
        if self.run_type in ("llm", "chat_model"):
            self.mgr.llm_error(self.name, self.run_id, text)
        elif self.run_type == "tool":
            self.mgr.tool_error(self.name, self.run_id, text)
        elif self.run_type == "retriever":
            self.mgr.retriever_error(self.name, self.run_id, text)
        else:
            self.mgr.chain_error(self.name, self.run_id, text)


# ---------------------------------------------------------------------------
# the tree builder + the store
# ---------------------------------------------------------------------------


class RunSink:
    """Where finished runs go. vault_sink.VaultRunSink is the flag-gated house sink;
    anything with .save(run) qualifies."""

    def save(self, run: Run) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class InMemoryRunStore(RunSink):
    """Thread-safe capped ring, newest last. len() = runs kept."""

    def __init__(self, cap: int = DEFAULT_STORE_CAP) -> None:
        self.cap = max(1, int(cap))
        self._lock = threading.Lock()
        self._runs: dict[str, Run] = {}
        self._order: list[str] = []

    def save(self, run: Run) -> None:
        with self._lock:
            self._runs[run.id] = run
            if run.id not in self._order:
                self._order.append(run.id)
            while len(self._order) > self.cap:
                old = self._order.pop(0)
                self._runs.pop(old, None)

    def get(self, run_id: str) -> Run | None:
        with self._lock:
            return self._runs.get(run_id)

    def recent(self, limit: int = 20) -> list[Run]:
        with self._lock:
            return [self._runs[rid] for rid in self._order[-limit:] if rid in self._runs]

    def __len__(self) -> int:
        with self._lock:
            return len(self._order)

    def clear(self) -> None:
        with self._lock:
            self._runs.clear()
            self._order.clear()


class RunTreeTracer(BaseCallbackHandler):
    """The handler that builds the tree and persists FINISHED runs to the sinks.
    Parent linkage rides the manager's parent_run_id - no registry, no stack.
    The runs dict is a ring: past max_runs, finished ROOTS evict oldest-first
    (children stay readable by their own id until their turn)."""

    def __init__(self, sinks: list[RunSink] | None = None,
                 max_runs: int = 2000) -> None:
        self.sinks: list[RunSink] = list(sinks or [])
        self.max_runs = max(100, int(max_runs))
        self.runs: dict[str, Run] = {}
        self._lock = threading.Lock()

    # -- helpers
    def _make(self, name: str, run_type: str, run_id: str, parent: str | None,
              inputs: Any, tags: list[str], metadata: dict) -> None:
        with self._lock:
            if parent and parent in self.runs:
                trace_id = self.runs[parent].trace_id or parent
                self.runs[parent].child_ids.append(run_id)
            else:
                trace_id = run_id          # a root, or an orphan becomes its own root
            self.runs[run_id] = Run(id=run_id, name=name, run_type=run_type,
                                    inputs=_plain(inputs), parent_run_id=parent,
                                    trace_id=trace_id,
                                    tags=list(tags), metadata=dict(metadata))

    def _finish(self, run_id: str, outputs: Any = None, error: str | None = None) -> None:
        with self._lock:
            run = self.runs.get(run_id)
            if run is None:
                return
            run.end_time = time.time()
            if outputs is not None:
                run.outputs = _plain(outputs)
            if error is not None:
                run.error = error
            snapshot = Run(**dataclasses.asdict(run))
        self._evict()
        for sink in self.sinks:
            try:
                sink.save(snapshot)
            except Exception:  # noqa: BLE001 - persistence is best-effort
                continue

    # -- chain
    def on_chain_start(self, name, run_id, parent_run_id, inputs, tags, metadata) -> None:
        self._make(name, "chain", run_id, parent_run_id, inputs, tags, metadata)

    def on_chain_end(self, name, run_id, outputs) -> None:
        self._finish(run_id, outputs=outputs)

    def on_chain_error(self, name, run_id, error) -> None:
        self._finish(run_id, error=error)

    # -- chat model
    def on_chat_model_start(self, name, run_id, parent_run_id, messages, tags, metadata) -> None:
        self._make(name, "chat_model", run_id, parent_run_id, messages, tags, metadata)

    def on_llm_end(self, name, run_id, output) -> None:
        self._finish(run_id, outputs=output)

    def on_llm_error(self, name, run_id, error) -> None:
        self._finish(run_id, error=error)

    # -- tool
    def on_tool_start(self, name, run_id, parent_run_id, inputs, tags, metadata) -> None:
        self._make(name, "tool", run_id, parent_run_id, inputs, tags, metadata)

    def on_tool_end(self, name, run_id, output) -> None:
        self._finish(run_id, outputs=output)

    def on_tool_error(self, name, run_id, error) -> None:
        self._finish(run_id, error=error)

    # -- retriever (P6)
    def on_retriever_start(self, name, run_id, parent_run_id, query, tags, metadata) -> None:
        self._make(name, "retriever", run_id, parent_run_id, query, tags, metadata)

    def on_retriever_end(self, name, run_id, documents) -> None:
        self._finish(run_id, outputs=documents)

    def on_retriever_error(self, name, run_id, error) -> None:
        self._finish(run_id, error=error)

    # -- reads
    def _evict(self) -> None:
        """Ring eviction (called with the lock held from _finish)."""
        if len(self.runs) <= self.max_runs:
            return
        finished_roots = [r for r in self.runs.values()
                          if r.end_time is not None
                          and (not r.parent_run_id or r.parent_run_id not in self.runs)]
        if not finished_roots:
            finished_roots = [r for r in self.runs.values() if r.end_time is not None]
        if not finished_roots:
            return
        finished_roots.sort(key=lambda r: r.start_time)
        drop = max(1, int(self.max_runs * 0.1))
        for r in finished_roots[:drop]:
            self.runs.pop(r.id, None)

    def get(self, run_id: str) -> Run | None:
        with self._lock:
            return self.runs.get(run_id)

    def tree(self, run_id: str) -> dict[str, Any] | None:
        """The run nested with its children (one level of the explorer at a time)."""
        run = self.get(run_id)
        if run is None:
            return None
        node = run.to_dict()
        node["children"] = [c for c in (self.tree(cid) for cid in run.child_ids) if c]
        return node

    def roots(self, limit: int = 20) -> list[Run]:
        with self._lock:
            all_runs = list(self.runs.values())
        return [r for r in all_runs if not r.parent_run_id][-limit:]


# the process store: the explorer route reads this; lanes opt in by attaching
# global_tracer() into their config callbacks (caps are constants - a config read
# at import time would break the inertness law)
GLOBAL_STORE = InMemoryRunStore()
_TRACER: RunTreeTracer | None = None


def global_tracer() -> RunTreeTracer:
    """The process-wide tree tracer bound to GLOBAL_STORE (one per process - the
    runs the /api/aep/runs explorer sees without any wiring)."""
    global _TRACER
    if _TRACER is None:
        _TRACER = RunTreeTracer(sinks=[GLOBAL_STORE])
    return _TRACER


def reset_global() -> None:
    """Test seam: forget every global run."""
    global _TRACER
    GLOBAL_STORE.clear()
    _TRACER = None


# ---------------------------------------------------------------------------
# astream_events - the event_stream.py v2 port
# ---------------------------------------------------------------------------


class _EventStreamHandler(BaseCallbackHandler):
    """Records every event as an upstream-v2-shaped dict, in order."""

    def __init__(self, sink: Callable[[dict], None]) -> None:
        self._sink = sink
        self._parents: dict[str, str | None] = {}

    def _event(self, event: str, name: str, run_id: str, data: dict) -> None:
        parent = self._parents.get(run_id)
        chain: list[str] = []
        p = parent
        while p is not None:
            chain.append(p)
            p = self._parents.get(p)
        self._sink({"event": event, "name": name, "run_id": run_id,
                    "parent_ids": chain, "tags": [], "metadata": {}, "data": data})

    def _remember(self, run_id: str, parent_run_id: str | None) -> None:
        self._parents[run_id] = parent_run_id

    # chain
    def on_chain_start(self, name, run_id, parent_run_id, inputs, tags, metadata):
        self._remember(run_id, parent_run_id)
        self._event("on_chain_start", name, run_id, {"input": _plain(inputs)})

    def on_chain_stream(self, name, run_id, chunk):
        self._event("on_chain_stream", name, run_id, {"chunk": _plain(chunk)})

    def on_chain_end(self, name, run_id, outputs):
        self._event("on_chain_end", name, run_id, {"output": _plain(outputs)})

    def on_chain_error(self, name, run_id, error):
        self._event("on_chain_error", name, run_id, {"error": error})

    # chat model
    def on_chat_model_start(self, name, run_id, parent_run_id, messages, tags, metadata):
        self._remember(run_id, parent_run_id)
        self._event("on_chat_model_start", name, run_id, {"input": _plain(messages)})

    def on_llm_new_token(self, name, run_id, token):
        self._event("on_llm_new_token", name, run_id, {"chunk": {"text": token}})

    def on_llm_end(self, name, run_id, output):
        self._event("on_llm_end", name, run_id, {"output": _plain(output)})

    def on_llm_error(self, name, run_id, error):
        self._event("on_llm_error", name, run_id, {"error": error})

    # tool
    def on_tool_start(self, name, run_id, parent_run_id, inputs, tags, metadata):
        self._remember(run_id, parent_run_id)
        self._event("on_tool_start", name, run_id, {"input": _plain(inputs)})

    def on_tool_end(self, name, run_id, output):
        self._event("on_tool_end", name, run_id, {"output": _plain(output)})

    def on_tool_error(self, name, run_id, error):
        self._event("on_tool_error", name, run_id, {"error": error})


async def astream_events(runnable, input: Any, config: dict | None = None,  # noqa: A002,A003
                         version: str = "v2", *, include_names: list[str] | None = None):
    """The upstream event_stream v2 port: stream the runnable in a task, drain the
    events as they fire. Yields dicts: event / name / run_id / parent_ids / data.

    version is pinned "v2" (the only shape this port speaks) - anything else raises
    honestly instead of silently emitting v1."""
    if version != "v2":
        raise ValueError(f"astream_events version must be 'v2', got {version!r}")
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()
    DONE = object()

    def push(ev: dict) -> None:
        if include_names is not None and ev["name"] not in include_names:
            return
        queue.put_nowait(ev)

    handler = _EventStreamHandler(push)
    mgr = callbacks_from_config(config) or CallbackManager()
    cfg = {**(config or {}), "callbacks": CallbackManager(
        [handler, *mgr.handlers], parent_run_id=mgr.parent_run_id,
        tags=mgr.tags, metadata=mgr.metadata)}

    async def _pump() -> None:
        try:
            async for _chunk in runnable.astream(input, cfg):
                pass                       # events ride the callbacks; chunks are drained
        except Exception as e:  # noqa: BLE001 - the error already fired as an event
            push({"event": "on_chain_error", "name": runnable.get_name()
                  if hasattr(runnable, "get_name") else type(runnable).__name__,
                  "run_id": "driver", "parent_ids": [],
                  "tags": [], "metadata": {}, "data": {"error": str(e)}})
        finally:
            queue.put_nowait(DONE)

    task = loop.create_task(_pump())
    try:
        while True:
            item = await queue.get()
            if item is DONE:
                break
            yield item
        await task
    finally:
        if not task.done():
            task.cancel()


# ---------------------------------------------------------------------------
# convenience: run traced, sync
# ---------------------------------------------------------------------------


def traced_invoke(runnable, input: Any, config: dict | None = None,  # noqa: A002,A003
                  tracer: RunTreeTracer | None = None) -> Any:
    """invoke() with the tree tracer attached - the one-liner lanes will use."""
    t = tracer or global_tracer()
    cfg = {**(config or {})}
    mgr = callbacks_from_config(cfg)
    if mgr is None:
        cfg["callbacks"] = CallbackManager([t])
    else:
        cfg["callbacks"] = CallbackManager([t, *mgr.handlers], parent_run_id=mgr.parent_run_id,
                                           tags=mgr.tags, metadata=mgr.metadata)
    return runnable.invoke(input, cfg)
