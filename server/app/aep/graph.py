"""HOOLA AEP graph - the state-graph engine (v0.530.0 HOOLA GRAPH, P3 of the AEP
plan). The langgraph idea hand-built after the end-to-end read of
github.com/langchain-ai/langchain @ aa2528fb (agents are LangGraph graphs;
StateGraph / channels / checkpoint / interrupts). ZERO upstream code or imports
(the port law that built P1 + P2).

What lives here:

- START / END    : the graph sentinels (edges from START are entries, edges to
                   END terminate the walk).
- add_messages   : the messages channel reducer - append, replace-by-id,
                   RemoveMessage drops one id, RemoveMessage(REMOVE_ALL_MESSAGES)
                   clears, dicts coerce back into messages, plain strings become
                   HumanMessages (the upstream semantics).
- AgentState     : the canonical agent state - {"messages": Annotated[list,
                   add_messages]} - the schema P4's create_agent compiles on.
- StateGraph     : the builder - add_node / add_edge / add_conditional_edges /
                   set_entry_point / compile. Plain state channels are
                   last-value-wins; a channel annotated Annotated[T, reducer]
                   merges node updates through the reducer (operator.add works).
                   Several static edges from one node fan out into the same
                   super-step; a node with several inbound edges joins only when
                   ALL its parents have run (the barrier). Every node in a
                   super-step sees the SAME pre-step state. Routers are sync.
- CompiledStateGraph : a Runnable (it composes with `|` and rides the P2 tracer
                   seam - every node execution is a chain span named by the NODE
                   when callbacks ride the config; an interrupted node's span
                   stays open, the walk parked, honestly). invoke/ainvoke/stream/
                   astream, stream_mode "updates" | "values", recursion_limit
                   (default 25) with an honest GraphRecursionError, get_state /
                   update_state, and the interrupt machine below.
- interrupt / Command : interrupt(value) inside a node PARKS the graph - the
                   state is checkpointed, invoke returns the state carrying
                   "__interrupt__" and nothing after the interrupt runs.
                   Command(resume=value) re-enters at the parked node; the node
                   re-runs FROM ITS TOP and the interrupt() call now RETURNS the
                   resume value (a second interrupt() in the same node raises a
                   new park with the earlier answers preserved). Interrupts
                   without a checkpointer are an honest refusal.
                   Command(update=..., goto=...) reshapes the stored walk:
                   update applies through the reducers, goto picks the next
                   nodes. invoke(None) with a checkpointer + a stored walk
                   resumes it (the crash path - the dhara checkpoint lesson).
- BaseCheckpointSaver / MemorySaver / SqliteSaver : the state machine's memory.
                   A checkpoint lands after EVERY super-step. MemorySaver is a
                   thread-safe capped ring; SqliteSaver is stdlib sqlite3 (WAL)
                   and also accepts an sqlalchemy Engine (the vault's engine
                   shape, used lazily via raw_connection). Resume values and
                   state crossing SqliteSaver are JSON-ified honestly.
- store          : compile(store=...) rides config["store"] into every node -
                   the P1 stores are the cross-thread memory.

Out of scope, honestly: the Send API (dynamic map-reduce fan-out - the static
multi-edge fan-out covers the map case), subgraph composition (a compiled graph
is a Runnable, so it already nests through nodes), async routers.

INERTNESS LAW (the P1 law, re-proven by the suite): a fresh interpreter imports
app.aep.graph with zero threads, zero env reads, zero files - the module is a
library; checkpointers write only when a compiled graph with one actually runs,
so no kill switch is needed (the flag law applies to surfaces that run on their
own - routes, jobs - and P3 adds none).
"""
from __future__ import annotations

import asyncio
import inspect
import json
import operator  # noqa: F401 - re-exported for Annotated[list, operator.add] schemas
import sqlite3
import threading
import time
import uuid
from abc import ABC, abstractmethod
from typing import Annotated, Any, Callable, Iterator, TypedDict, get_args, get_origin, get_type_hints

from .messages import (
    REMOVE_ALL_MESSAGES,
    AIMessage,
    BaseMessage,
    ChatMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    ToolMessage,
    message_to_dict,
    messages_from_dict,
)
from .runnable import Runnable, RunnableConfig, ensure_config
from .runnable import _span_start

__all__ = [
    "START", "END", "INTERRUPT_KEY", "AgentState", "add_messages",
    "BaseCheckpointSaver", "MemorySaver", "SqliteSaver",
    "Command", "CompiledStateGraph", "GraphInterrupt", "GraphRecursionError",
    "StateGraph", "interrupt",
]

START = "__start__"
END = "__end__"

DEFAULT_RECURSION_LIMIT = 25
INTERRUPT_KEY = "__interrupt__"
RESUME_MISSING = object()   # a resume slot that exists but has not been answered


class GraphRecursionError(Exception):
    """The walk crossed recursion_limit super-steps (the honest stop)."""


class GraphInterrupt(Exception):
    """Raised internally when a node calls interrupt(); the runner converts it
    into a parked state. Never let it escape invoke()/ainvoke()."""

    def __init__(self, node: str, idx: int, value: Any) -> None:
        super().__init__(f"interrupt at node {node}[{idx}]")
        self.node = node
        self.idx = idx
        self.value = value


class Command(dict):
    """The resume/update/goto envelope a caller may pass to invoke/ainvoke.

    - resume : the answer handed to the parked interrupt() call
    - update : a state update applied through the reducers before continuing
    - goto   : node name(s) to run next (replaces the edge-chosen next)

    Command(resume=...) or Command(resume=None) counts as a resume attempt;
    Command(update=...) / Command(goto=...) without resume reshapes the walk.
    """

    def __init__(self, resume: Any = None, update: dict[str, Any] | None = None,
                 goto: str | list[str] | None = None) -> None:
        super().__init__(resume=resume, update=update, goto=goto)
        self.resume = resume
        self.update = update
        self.goto = goto
        self.is_resume = True   # a Command is a resume attempt unless built otherwise

    @classmethod
    def update_only(cls, update: dict[str, Any]) -> "Command":
        c = cls(update=update)
        c.is_resume = False
        return c

    @classmethod
    def goto_nodes(cls, goto: str | list[str], update: dict[str, Any] | None = None) -> "Command":
        c = cls(update=update, goto=goto)
        c.is_resume = False
        return c


def _is_command(x: Any) -> bool:
    return isinstance(x, Command)


# ---------------------------------------------------------------------------
# channels: reducers over state annotations
# ---------------------------------------------------------------------------


def _coerce_message(m: Any) -> Any:
    if isinstance(m, BaseMessage):
        return m
    if isinstance(m, dict):
        if "type" not in m and "data" not in m and "role" in m:
            # the role shape ({"role", "content", ...}) - the upstream
            # convert_to_messages table, shared with the model input lane
            role = m.get("role", "human")
            cls = {"human": HumanMessage, "user": HumanMessage,
                   "ai": AIMessage, "assistant": AIMessage,
                   "system": SystemMessage, "tool": ToolMessage}.get(role)
            if cls is None:
                return ChatMessage(role=role, content=m.get("content", ""))
            kwargs: dict[str, Any] = {"content": m.get("content", "")}
            if m.get("id"):
                kwargs["id"] = m["id"]
            return cls(**kwargs)
        out = messages_from_dict([m])
        return out[0] if out else m
    if isinstance(m, str):
        return HumanMessage(content=m)
    return m


def add_messages(left: list[Any], right: list[Any]) -> list[Any]:
    """The messages-channel reducer (the upstream add_messages semantics):
    append; replace-by-id; RemoveMessage drops that id; RemoveMessage with the
    REMOVE_ALL_MESSAGES id clears the lane; dicts and strings coerce - BOTH
    sides (upstream coerces the whole lane, not just the writes)."""
    out = [_coerce_message(m) for m in (left or []) if not isinstance(m, RemoveMessage)]
    for m in (right or []):
        m = _coerce_message(m)
        if isinstance(m, RemoveMessage):
            if m.id == REMOVE_ALL_MESSAGES:
                out = []
            else:
                out = [x for x in out if getattr(x, "id", None) != m.id]
            continue
        mid = getattr(m, "id", None)
        if mid is not None:
            hit = False
            for i, x in enumerate(out):
                if getattr(x, "id", None) == mid:
                    out[i] = m
                    hit = True
                    break
            if not hit:
                out.append(m)
        else:
            out.append(m)
    return out


def _channels(schema: Any) -> dict[str, Callable | None]:
    """state field -> reducer (None = last-value-wins). Annotated metadata is
    read with include_extras so Annotated[T, reducer] survives get_type_hints."""
    try:
        hints = get_type_hints(schema, include_extras=True)
    except Exception:  # noqa: BLE001 - local schemas fall back to raw annotations
        hints = dict(getattr(schema, "__annotations__", {}) or {})
    out: dict[str, Callable | None] = {}
    for name, ann in hints.items():
        red: Callable | None = None
        if get_origin(ann) is Annotated:
            for meta in get_args(ann)[1:]:
                if callable(meta) and not isinstance(meta, type):
                    red = meta
                    break
        out[name] = red
    return out


class AgentState(TypedDict, total=False):
    """The canonical agent state - what P4's create_agent compiles on."""
    messages: Annotated[list[Any], add_messages]


# ---------------------------------------------------------------------------
# checkpointers
# ---------------------------------------------------------------------------


def _jsonify(v: Any) -> Any:
    if isinstance(v, BaseMessage):
        return message_to_dict(v)
    if isinstance(v, dict):
        return {k: _jsonify(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonify(x) for x in v]
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    return str(v)


def _thread_id(config: dict | None) -> str:
    cfg = config or {}
    return str((cfg.get("configurable") or {}).get("thread_id") or "default")


class BaseCheckpointSaver(ABC):
    """The checkpointer contract: put/get/list/delete_thread, keyed by the
    thread_id in config['configurable']. A checkpoint is a plain dict."""

    @abstractmethod
    def put(self, config: dict, checkpoint: dict) -> None: ...

    @abstractmethod
    def get(self, config: dict) -> dict | None: ...

    @abstractmethod
    def list(self, config: dict, *, limit: int | None = None) -> list[dict]: ...

    @abstractmethod
    def delete_thread(self, thread_id: str) -> None: ...


class MemorySaver(BaseCheckpointSaver):
    """Thread-safe in-memory ring, newest first on list, capped (the house
    ring law - oldest evicted past the cap)."""

    def __init__(self, cap: int = 500) -> None:
        self.cap = cap
        self._lock = threading.Lock()
        self._threads: dict[str, list[dict]] = {}

    def put(self, config: dict, checkpoint: dict) -> None:
        tid = _thread_id(config)
        with self._lock:
            rows = self._threads.setdefault(tid, [])
            rows.append(dict(checkpoint))
            if len(rows) > self.cap:
                del rows[: len(rows) - self.cap]

    def get(self, config: dict) -> dict | None:
        with self._lock:
            rows = self._threads.get(_thread_id(config))
            return dict(rows[-1]) if rows else None

    def list(self, config: dict, *, limit: int | None = None) -> list[dict]:
        with self._lock:
            rows = [dict(c) for c in reversed(self._threads.get(_thread_id(config), []))]
        return rows[:limit] if limit else rows

    def delete_thread(self, thread_id: str) -> None:
        with self._lock:
            self._threads.pop(thread_id, None)


class SqliteSaver(BaseCheckpointSaver):
    """stdlib sqlite3 (WAL) - a path OR an sqlalchemy Engine (the vault's
    engine shape; the engine is used lazily via raw_connection and never
    imported at module load). One table: aep_checkpoints(thread_id, id, step,
    ts, blob)."""

    def __init__(self, path: str | None = None, engine: Any = None) -> None:
        if (path is None) == (engine is None):
            raise ValueError("SqliteSaver needs exactly one of path= / engine=")
        self.path = path
        self.engine = engine
        self._local = threading.local()
        self._ensured = False   # per-instance: class-level leaked across databases
        if self.path:
            conn = self._conn()
            self._ensure(conn)

    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.path, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            self._local.conn = conn
        return conn

    def _ensure(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS aep_checkpoints ("
            "thread_id TEXT NOT NULL, id TEXT NOT NULL, step INTEGER NOT NULL,"
            "ts TEXT NOT NULL, blob TEXT NOT NULL,"
            "PRIMARY KEY (thread_id, id))"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_aep_cp_thread_step"
            " ON aep_checkpoints (thread_id, step)"
        )
        conn.commit()

    def _raw(self) -> tuple[Any, bool]:
        """(connection, borrowed) - an engine connection is borrowed from the
        pool and returned by close(); a path connection is thread-local. The
        engine path ensures its table on FIRST use of the instance (put, get,
        list or delete may all arrive first - a get before any put is the
        chat-memory path)."""
        if self.engine is not None:
            conn = self.engine.raw_connection()
            if not self._ensured:
                self._ensure(conn)
                self._ensured = True
            return conn, True
        return self._conn(), False

    def put(self, config: dict, checkpoint: dict) -> None:
        tid = _thread_id(config)
        blob = json.dumps(_jsonify(checkpoint), ensure_ascii=False, default=str)
        conn, borrowed = self._raw()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO aep_checkpoints"
                " (thread_id, id, step, ts, blob) VALUES (?, ?, ?, ?, ?)",
                (tid, str(checkpoint.get("id")), int(checkpoint.get("step") or 0),
                 str(checkpoint.get("ts")), blob),
            )
            conn.commit()
        finally:
            if borrowed:
                conn.close()

    def get(self, config: dict) -> dict | None:
        tid = _thread_id(config)
        conn, borrowed = self._raw()
        try:
            row = conn.execute(
                "SELECT blob FROM aep_checkpoints WHERE thread_id = ?"
                " ORDER BY step DESC, ts DESC LIMIT 1", (tid,)).fetchone()
        finally:
            if borrowed:
                conn.close()
        return json.loads(row[0]) if row else None

    def list(self, config: dict, *, limit: int | None = None) -> list[dict]:
        tid = _thread_id(config)
        conn, borrowed = self._raw()
        try:
            sql = ("SELECT blob FROM aep_checkpoints WHERE thread_id = ?"
                   " ORDER BY step DESC, ts DESC")
            if limit:
                sql += f" LIMIT {int(limit)}"
            rows = conn.execute(sql, (tid,)).fetchall()
        finally:
            if borrowed:
                conn.close()
        return [json.loads(r[0]) for r in rows]

    def delete_thread(self, thread_id: str) -> None:
        conn, borrowed = self._raw()
        try:
            conn.execute("DELETE FROM aep_checkpoints WHERE thread_id = ?", (thread_id,))
            conn.commit()
        finally:
            if borrowed:
                conn.close()


# ---------------------------------------------------------------------------
# the builder
# ---------------------------------------------------------------------------


class _NodeRef:
    """Names a node inside the tracer tree (Span.start names runs via get_name)."""

    def __init__(self, name: str) -> None:
        self.name = name

    def get_name(self, suffix: str | None = None) -> str:
        return f"{self.name}{suffix}" if suffix else self.name


class _CondEdge:
    __slots__ = ("router", "path_map")

    def __init__(self, router: Callable, path_map: Any) -> None:
        self.router = router
        self.path_map = path_map


def _run_callable(fn: Callable, *args: Any) -> Any:
    """Call fn; a coroutine function runs via asyncio.run when no loop is
    running and refuses honestly inside one (use ainvoke for async nodes)."""
    if inspect.iscoroutinefunction(fn):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(fn(*args))
        raise TypeError(
            "an async callable cannot run inside sync invoke() while a loop is "
            "running - use ainvoke()")
    return fn(*args)


def _takes_cfg(fn: Callable) -> bool:
    try:
        params = [p for p in inspect.signature(fn).parameters.values()
                  if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    except (TypeError, ValueError):
        return False
    return len(params) >= 2


def _node_config(fn: Callable) -> Callable:
    """Normalize fn(state) to the two-arg shape fn(state, config) - an async
    one-arg fn stays awaitable (a sync lambda wrapper would swallow the
    coroutine and the walk would see a coroutine object, not a dict)."""
    if _takes_cfg(fn):
        return fn
    one = fn
    if inspect.iscoroutinefunction(one):
        async def _two(state, config=None):
            return await one(state)
        return _two
    return lambda state, config=None: one(state)  # noqa: E731


class StateGraph:
    """The builder: nodes + edges + conditional edges, compiled into a
    CompiledStateGraph. All topology errors are compile-time, never mid-run."""

    def __init__(self, schema: Any) -> None:
        if not hasattr(schema, "__annotations__"):
            raise TypeError("StateGraph(schema) needs a TypedDict schema")
        self.schema = schema
        self._channels = _channels(schema)
        self._nodes: dict[str, Callable] = {}
        self._edges: list[tuple[str, str]] = []          # (from, to) static
        self._conds: dict[str, list[_CondEdge]] = {}     # source -> routers
        self._entry: list[str] = []

    # -- construction --------------------------------------------------------

    def add_node(self, name: str, fn: Any) -> "StateGraph":
        if not isinstance(name, str) or not name or name in (START, END):
            raise ValueError(f"bad node name: {name!r}")
        if name in self._nodes:
            raise ValueError(f"node {name!r} already exists")
        if isinstance(fn, Runnable):
            run = fn
            fn = lambda state, config=None, _r=run: _r.invoke(state, config)  # noqa: E731
        if not callable(fn):
            raise TypeError(f"node {name!r} needs a callable or Runnable")
        self._nodes[name] = fn
        return self

    def add_edge(self, from_key: str, to_key: str) -> "StateGraph":
        if from_key != START and from_key not in self._nodes:
            raise ValueError(f"add_edge: unknown source {from_key!r} (add the node first)")
        if to_key != END and to_key not in self._nodes:
            raise ValueError(f"add_edge: unknown target {to_key!r} (add the node first)")
        if from_key == START:
            self._entry.append(to_key)
        else:
            self._edges.append((from_key, to_key))
        return self

    def set_entry_point(self, name: str) -> "StateGraph":
        return self.add_edge(START, name)

    def add_conditional_edges(self, source: str, router: Callable,
                              path_map: Any = None) -> "StateGraph":
        if source not in self._nodes:
            raise ValueError(f"add_conditional_edges: unknown source {source!r}")
        if not callable(router):
            raise TypeError("router must be a callable")
        if isinstance(path_map, (list, tuple)):
            path_map = dict(enumerate(path_map))   # positional map
        self._conds.setdefault(source, []).append(_CondEdge(router, path_map))
        return self

    # -- validation + compile --------------------------------------------------

    def _validate(self) -> None:
        if not self._nodes:
            raise ValueError("a graph needs at least one node")
        if not self._entry:
            raise ValueError("no entry point - add_edge(START, node) or set_entry_point")
        for src, conds in self._conds.items():
            for ce in conds:
                if isinstance(ce.path_map, dict):
                    for target in ce.path_map.values():
                        if target != END and target not in self._nodes:
                            raise ValueError(
                                f"conditional edge from {src!r} targets unknown node {target!r}")

    def compile(self, checkpointer: BaseCheckpointSaver | None = None,
                store: Any = None, name: str | None = None) -> "CompiledStateGraph":
        self._validate()
        return CompiledStateGraph(self, checkpointer=checkpointer, store=store, name=name)


# ---------------------------------------------------------------------------
# the compiled walk
# ---------------------------------------------------------------------------


class CompiledStateGraph(Runnable):
    """The executable graph: a Runnable, so it composes with `|` and its node
    executions ride the P2 tracer seam (a chain span per node when callbacks
    ride the config)."""

    _tls = threading.local()   # the interrupt/resume context of the running node

    def __init__(self, builder: StateGraph, checkpointer: BaseCheckpointSaver | None = None,
                 store: Any = None, name: str | None = None) -> None:
        self.schema = builder.schema
        self.nodes = dict(builder._nodes)
        self.channels = dict(builder._channels)
        self.edges = list(builder._edges)
        self.conds = {k: list(v) for k, v in builder._conds.items()}
        self.entry = list(dict.fromkeys(builder._entry))
        self.checkpointer = checkpointer
        self.store = store
        self._name = name   # the display name (P4 create_agent names its agent)
        # fan-in barriers: node -> the parents it waits for
        self._parents: dict[str, set[str]] = {}
        self._out: dict[str, list[str]] = {}
        for src, dst in self.edges:
            if dst != END:
                self._parents.setdefault(dst, set()).add(src)
                self._out.setdefault(src, []).append(dst)

    # -- naming --------------------------------------------------------

    def get_name(self, suffix: str | None = None) -> str:
        base = self._name or "StateGraph"
        return f"{base}{suffix}" if suffix else base

    # -- state plumbing --------------------------------------------------

    def _apply_update(self, state: dict, update: dict) -> dict:
        unknown = set(update) - set(self.channels)
        if unknown:
            raise ValueError(
                f"update touches unknown state keys: {sorted(unknown)} "
                f"(schema has {sorted(self.channels)})")
        out = dict(state)
        for k, v in update.items():
            red = self.channels.get(k)
            # a reducer merges when the channel already carries a value; a
            # first-ever value seeds the channel directly (operator.add has
            # no identity for a missing left side)
            out[k] = red(out[k], v) if (red is not None and k in out) else v
        return out

    def _init_state(self, inp: Any) -> dict:
        if inp is None:
            inp = {}
        if not isinstance(inp, dict):
            raise TypeError("graph input must be a dict of state values")
        return self._apply_update({}, inp)

    def _next_from(self, ready_parents: dict[str, set[str]], sources: list[str]) -> list[str]:
        """Static-edge next: a join node becomes ready when ALL parents ran."""
        nxt: list[str] = []
        for src in sources:
            for dst in self._out.get(src, []):
                ready_parents[dst].discard(src)
                if not ready_parents[dst] and dst not in nxt:
                    nxt.append(dst)
        return nxt

    def _route(self, state: dict, src: str) -> list[str]:
        targets: list[str] = []
        for ce in self.conds.get(src, []):
            ans = _run_callable(ce.router, state)
            answers = ans if isinstance(ans, (list, tuple)) else [ans]
            for i, a in enumerate(answers):
                if isinstance(ce.path_map, dict):
                    t = ce.path_map.get(a)
                    if t is None:
                        raise ValueError(
                            f"router at {src!r} returned {a!r} - not in the path_map")
                else:
                    t = a
                if t != END and t not in self.nodes:
                    raise ValueError(f"router at {src!r} targets unknown node {t!r}")
                if t not in targets:
                    targets.append(t)
        return targets

    # -- one node execution (sync) -----------------------------------------

    def _run_node(self, name: str, state: dict, cfg: dict,
                  resumes: dict[int, Any] | None = None) -> dict:
        fn = _node_config(self.nodes[name])
        prev = getattr(self._tls, "resume", None)
        self._tls.resume = {"node": name, "resumes": resumes or {}, "calls": 0}
        span = _span_start(cfg, _NodeRef(name), "chain", state)
        try:
            # the node body runs on the span's child config, so runs fired
            # INSIDE the node (a model call, a tool call) nest under the node
            # span in the P2 run tree - the upstream shape
            out = _run_callable(fn, state, span.child_cfg if span is not None else cfg)
        except GraphInterrupt:
            raise   # the span stays open - the walk parked, honestly
        except Exception as e:  # noqa: BLE001 - the span must close before re-raise
            if span is not None:
                span.error(e)
            raise
        finally:
            self._tls.resume = prev
        if out is None:
            out = {}
        if not isinstance(out, dict):
            err = TypeError(
                f"node {name!r} returned {type(out).__name__} - nodes return a dict update")
            if span is not None:
                span.error(err)
            raise err
        if span is not None:
            span.end(out)
        return out

    async def _arun_node(self, name: str, state: dict, cfg: dict) -> dict:
        fn = _node_config(self.nodes[name])
        prev = getattr(self._tls, "resume", None)
        self._tls.resume = {"node": name, "resumes": {}, "calls": 0}
        span = _span_start(cfg, _NodeRef(name), "chain", state)
        body_cfg = span.child_cfg if span is not None else cfg
        try:
            if inspect.iscoroutinefunction(fn):
                out = await fn(state, body_cfg)
            else:
                out = await asyncio.to_thread(fn, state, body_cfg)
        except GraphInterrupt:
            raise   # the span stays open - the walk parked, honestly
        except Exception as e:  # noqa: BLE001
            if span is not None:
                span.error(e)
            raise
        finally:
            self._tls.resume = prev
        if out is None:
            out = {}
        if not isinstance(out, dict):
            err = TypeError(
                f"node {name!r} returned {type(out).__name__} - nodes return a dict update")
            if span is not None:
                span.error(err)
            raise err
        if span is not None:
            span.end(out)
        return out

    # -- checkpointing -------------------------------------------------------

    def _checkpoint(self, cfg: dict, step: int, values: dict, nxt: list[str],
                    pending: dict | None) -> dict | None:
        if self.checkpointer is None:
            return None
        cp = {
            "v": 1, "id": uuid.uuid4().hex,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "thread_id": _thread_id(cfg), "step": step,
            "channel_values": values, "next": [n for n in nxt if n != END],
            "pending": pending,
        }
        self.checkpointer.put(cfg, cp)
        return cp

    # -- interrupt shape -------------------------------------------------------

    @staticmethod
    def _interrupt_state(state: dict, node: str, idx: int, value: Any) -> dict:
        return {**state, INTERRUPT_KEY: [{
            "value": value, "resumable": True, "node": node, "idx": idx}]}

    # -- the sync walk ---------------------------------------------------------

    def _walk(self, inp: Any, cfg: dict) -> dict:
        state = self._init_state(inp)
        step = 0
        limit = self._limit(cfg)
        ready_parents = {n: set(p) for n, p in self._parents.items()}
        nxt: list[str] = list(self.entry)
        self._checkpoint(cfg, step, state, nxt, None)
        while nxt:
            if step >= limit:
                raise GraphRecursionError(
                    f"recursion_limit of {limit} super-steps crossed - the walk never reached END")
            updates: dict[str, dict] = {}
            parked: GraphInterrupt | None = None
            for name in nxt:
                try:
                    updates[name] = self._run_node(name, state, cfg)
                except GraphInterrupt as gi:
                    parked = gi
                    break   # the super-step parks; nothing after the interrupt runs
            if parked is not None:
                if self.checkpointer is None:
                    raise RuntimeError(
                        "interrupt() needs a checkpointer - compile(checkpointer=...)")
                for upd in updates.values():
                    state = self._apply_update(state, upd or {})
                step += 1
                self._checkpoint(cfg, step, state, [parked.node],
                                 {"node": parked.node, "idx": parked.idx,
                                  "value": _jsonify(parked.value), "resumes": {}})
                return self._interrupt_state(state, parked.node, parked.idx, parked.value)
            for upd in updates.values():   # sequential fold: reducers merge
                state = self._apply_update(state, upd or {})   # parallel writes
            step += 1
            sources = list(updates)
            routed: list[str] = []
            for src in sources:
                routed.extend(self._route(state, src))
            # routing is ADDITIVE (the upstream law): the routers' targets and
            # the static edges' targets both fire in the next super-step
            nxt = [n for n in dict.fromkeys(routed + self._next_from(ready_parents, sources))
                   if n != END]
            self._checkpoint(cfg, step, state, nxt, None)
        return state

    def _limit(self, cfg: dict) -> int:
        return int((cfg.get("configurable") or {}).get("recursion_limit")
                   or cfg.get("recursion_limit") or DEFAULT_RECURSION_LIMIT)

    # -- interrupt + resume -------------------------------------------------

    def _resume_walk(self, resume: Any, cfg: dict, update: dict | None,
                     goto: list[str] | None) -> dict:
        cp = self.checkpointer.get(cfg) if self.checkpointer else None
        if cp is None or not cp.get("pending"):
            raise ValueError("nothing to resume - no parked interrupt for this thread")
        pending = dict(cp["pending"])
        state = dict(cp.get("channel_values") or {})
        if update:
            state = self._apply_update(state, update)
        node = pending["node"]
        resumes = {int(k): v for k, v in (pending.get("resumes") or {}).items()}
        resumes[int(pending.get("idx") or 0)] = resume
        step = int(cp.get("step") or 0)
        limit = self._limit(cfg)
        ready_parents = {n: set(p) for n, p in self._parents.items()}

        # re-run the parked node FROM ITS TOP; answered slots replay, open slots re-park
        try:
            out = self._run_node(node, state, cfg, resumes=resumes)
        except GraphInterrupt as gi:
            if gi.node != node:
                raise
            step += 1
            self._checkpoint(cfg, step, state, [node],
                             {"node": node, "idx": gi.idx, "value": _jsonify(gi.value),
                              "resumes": {str(k): v for k, v in resumes.items()}})
            return self._interrupt_state(state, node, gi.idx, gi.value)
        state = self._apply_update(state, out)
        step += 1
        routed: list[str] = []
        for src in [node]:
            routed.extend(self._route(state, src))
        # additive here too: routers + static edges from the resumed node
        static_next = [n for n in self._next_from(ready_parents, [node]) if n != END]
        if goto:
            nxt = [n for n in dict.fromkeys(goto) if n != END]
        else:
            nxt = [n for n in dict.fromkeys(routed + static_next) if n != END]
        self._checkpoint(cfg, step, state, nxt, None)
        return self._tail(state, nxt, cfg, step, limit, ready_parents)

    def _tail(self, state: dict, nxt: list[str], cfg: dict, step: int, limit: int,
              ready_parents: dict[str, set[str]]) -> dict:
        """Continue a walk from explicit next nodes (post-resume / goto)."""
        while nxt:
            if step >= limit:
                raise GraphRecursionError(
                    f"recursion_limit of {limit} super-steps crossed - the walk never reached END")
            updates: dict[str, dict] = {}
            parked: GraphInterrupt | None = None
            for name in nxt:
                try:
                    updates[name] = self._run_node(name, state, cfg)
                except GraphInterrupt as gi:
                    parked = gi
                    break
            if parked is not None:
                if self.checkpointer is None:
                    raise RuntimeError(
                        "interrupt() needs a checkpointer - compile(checkpointer=...)")
                for upd in updates.values():
                    state = self._apply_update(state, upd or {})
                step += 1
                self._checkpoint(cfg, step, state, [parked.node],
                                 {"node": parked.node, "idx": parked.idx,
                                  "value": _jsonify(parked.value), "resumes": {}})
                return self._interrupt_state(state, parked.node, parked.idx, parked.value)
            for upd in updates.values():   # sequential fold: reducers merge
                state = self._apply_update(state, upd or {})   # parallel writes
            step += 1
            sources = list(updates)
            routed: list[str] = []
            for src in sources:
                routed.extend(self._route(state, src))
            # routing is ADDITIVE (the upstream law): the routers' targets and
            # the static edges' targets both fire in the next super-step
            nxt = [n for n in dict.fromkeys(routed + self._next_from(ready_parents, sources))
                   if n != END]
            self._checkpoint(cfg, step, state, nxt, None)
        return state

    # -- Runnable contract ---------------------------------------------------

    def invoke(self, input: Any, config: RunnableConfig | None = None) -> dict:  # noqa: A002,A003
        cfg: dict = dict(ensure_config(config))
        if self.store is not None:
            cfg.setdefault("store", self.store)
        span = _span_start(cfg, self, "chain", input)
        if span is None:
            return self._invoke_body(input, cfg)
        try:
            out = self._invoke_body(input, span.child_cfg)
        except Exception as e:  # noqa: BLE001
            span.error(e)
            raise
        span.end(out)
        return out

    def _invoke_body(self, input: Any, cfg: dict) -> dict:  # noqa: A002,A003
        if _is_command(input):
            cmd = input
            if cmd.is_resume:
                return self._resume_walk(cmd.resume, cfg, cmd.update, cmd.goto)
            return self._reshape(cmd, cfg)
        if input is None and self.checkpointer is not None:
            cp = self.checkpointer.get(cfg)
            if cp is not None:
                state = dict(cp.get("channel_values") or {})
                nxt = list(cp.get("next") or [])
                pending = cp.get("pending")
                if pending:   # a parked walk - a bare None does not answer it
                    return self._interrupt_state(state, pending["node"],
                                                 int(pending.get("idx") or 0),
                                                 pending.get("value"))
                return self._tail(state, nxt, cfg, int(cp.get("step") or 0) + 1,
                                  self._limit(cfg),
                                  {n: set(p) for n, p in self._parents.items()})
        if isinstance(input, dict) and self.checkpointer is not None:
            cp = self.checkpointer.get(cfg)
            if cp is not None:
                return self._merged_walk(input, cp, cfg)
        return self._walk(input, cfg)

    def _merged_walk(self, inp: dict, cp: dict, cfg: dict) -> dict:
        """A dict input on a checkpointed thread MERGES into the stored channel
        values (the chat-memory law, the upstream shape): the input rides the
        reducers on top of the stored state, then the walk continues - from the
        parked node when the thread is parked (no resumes: the interrupt
        re-parks honestly with the merged state), from the stored next on a
        crashed walk, or from the entry when the thread finished (a fresh turn
        on an old conversation)."""
        state = self._apply_update(dict(cp.get("channel_values") or {}), inp)
        pending = cp.get("pending")
        parents = {n: set(p) for n, p in self._parents.items()}
        if pending:
            nxt: list[str] = [pending["node"]]
            step = int(cp.get("step") or 0) + 1
        elif cp.get("next"):
            nxt = list(cp.get("next") or [])
            step = int(cp.get("step") or 0) + 1
        else:
            nxt = list(self.entry)
            step = 0   # a fresh turn - the step budget restarts
        self._checkpoint(cfg, step, state, nxt, pending)
        return self._tail(state, nxt, cfg, step, self._limit(cfg), parents)

    def _reshape(self, cmd: Command, cfg: dict) -> dict:
        """Command(update/goto): shape the stored walk, continue it."""
        if self.checkpointer is None:
            raise RuntimeError("Command(update/goto) needs a checkpointer")
        cp = self.checkpointer.get(cfg)
        if cp is None:
            raise ValueError("no checkpoint for this thread - run the graph first")
        state = self._apply_update(dict(cp.get("channel_values") or {}), cmd.update or {})
        nxt = list(dict.fromkeys(cmd.goto)) if cmd.goto else list(cp.get("next") or [])
        pending = cp.get("pending")
        self._checkpoint(cfg, int(cp.get("step") or 0) + 1, state, nxt, pending)
        if pending and not nxt:
            return self._interrupt_state(state, pending["node"],
                                         int(pending.get("idx") or 0), pending.get("value"))
        if not nxt:
            return state
        return self._tail(state, nxt, cfg, int(cp.get("step") or 0) + 1, self._limit(cfg),
                          {n: set(p) for n, p in self._parents.items()})

    async def ainvoke(self, input: Any, config: RunnableConfig | None = None) -> dict:  # noqa: A002,A003
        cfg = ensure_config(config)
        if self.store is not None:
            cfg = {**cfg, "store": cfg.get("store", self.store)}
        has_async = any(inspect.iscoroutinefunction(_node_config(f))
                        for f in self.nodes.values())
        if not has_async:
            return await asyncio.to_thread(self.invoke, input, {**cfg})
        if _is_command(input) or (input is None and self.checkpointer is not None):
            # the command/crash paths are sync walks - run them off the loop
            return await asyncio.to_thread(self.invoke, input, {**cfg})
        span = _span_start(cfg, self, "chain", input)
        if span is None:
            return await self._awalk(input, cfg)
        try:
            out = await self._awalk(input, span.child_cfg)
        except Exception as e:  # noqa: BLE001
            span.error(e)
            raise
        span.end(out)
        return out

    async def _awalk(self, inp: Any, cfg: dict) -> dict:
        state = self._init_state(inp)
        step = 0
        limit = self._limit(cfg)
        ready_parents = {n: set(p) for n, p in self._parents.items()}
        nxt: list[str] = list(self.entry)
        self._checkpoint(cfg, step, state, nxt, None)
        while nxt:
            if step >= limit:
                raise GraphRecursionError(
                    f"recursion_limit of {limit} super-steps crossed - the walk never reached END")
            updates: dict[str, dict] = {}
            parked: GraphInterrupt | None = None
            for name in nxt:
                try:
                    updates[name] = await self._arun_node(name, state, cfg)
                except GraphInterrupt as gi:
                    parked = gi
                    break
            if parked is not None:
                if self.checkpointer is None:
                    raise RuntimeError(
                        "interrupt() needs a checkpointer - compile(checkpointer=...)")
                for upd in updates.values():
                    state = self._apply_update(state, upd or {})
                step += 1
                self._checkpoint(cfg, step, state, [parked.node],
                                 {"node": parked.node, "idx": parked.idx,
                                  "value": _jsonify(parked.value), "resumes": {}})
                return self._interrupt_state(state, parked.node, parked.idx, parked.value)
            for upd in updates.values():   # sequential fold: reducers merge
                state = self._apply_update(state, upd or {})   # parallel writes
            step += 1
            sources = list(updates)
            routed: list[str] = []
            for src in sources:
                routed.extend(self._route(state, src))
            # routing is ADDITIVE (the upstream law): the routers' targets and
            # the static edges' targets both fire in the next super-step
            nxt = [n for n in dict.fromkeys(routed + self._next_from(ready_parents, sources))
                   if n != END]
            self._checkpoint(cfg, step, state, nxt, None)
        return state

    def stream(self, input: Any, config: RunnableConfig | None = None,  # noqa: A002,A003
               stream_mode: str = "updates") -> Iterator[dict]:
        if stream_mode not in ("updates", "values"):
            raise ValueError(f"stream_mode must be 'updates' or 'values', got {stream_mode!r}")
        cfg = dict(ensure_config(config))
        if self.store is not None:
            cfg.setdefault("store", self.store)
        span = _span_start(cfg, self, "chain", input)
        if span is None:
            yield from self._stream_body(input, cfg, stream_mode)
            return
        try:
            last = None
            for chunk in self._stream_body(input, span.child_cfg, stream_mode):
                last = chunk
                yield chunk
        except Exception as e:  # noqa: BLE001
            span.error(e)
            raise
        span.end(last)   # the streaming close carries the last chunk (the v2 shape)

    def _stream_body(self, input: Any, cfg: dict,  # noqa: A002,A003
                     stream_mode: str = "updates") -> Iterator[dict]:
        state = self._init_state(input)
        step = 0
        limit = self._limit(cfg)
        ready_parents = {n: set(p) for n, p in self._parents.items()}
        nxt: list[str] = list(self.entry)
        while nxt:
            if step >= limit:
                raise GraphRecursionError(
                    f"recursion_limit of {limit} super-steps crossed - the walk never reached END")
            updates: dict[str, dict] = {}
            parked: GraphInterrupt | None = None
            for name in nxt:
                try:
                    updates[name] = self._run_node(name, state, cfg)
                except GraphInterrupt as gi:
                    parked = gi
                    break
            if parked is not None:
                if self.checkpointer is None:
                    raise RuntimeError(
                        "interrupt() needs a checkpointer - compile(checkpointer=...)")
                for upd in updates.values():
                    state = self._apply_update(state, upd or {})
                step += 1
                self._checkpoint(cfg, step, state, [parked.node],
                                 {"node": parked.node, "idx": parked.idx,
                                  "value": _jsonify(parked.value), "resumes": {}})
                yield {INTERRUPT_KEY: [{
                    "value": parked.value, "resumable": True,
                    "node": parked.node, "idx": parked.idx}]}
                return
            for upd in updates.values():   # sequential fold: reducers merge
                state = self._apply_update(state, upd or {})   # parallel writes
            yield updates if stream_mode == "updates" else dict(state)
            step += 1
            sources = list(updates)
            routed: list[str] = []
            for src in sources:
                routed.extend(self._route(state, src))
            # routing is ADDITIVE (the upstream law): the routers' targets and
            # the static edges' targets both fire in the next super-step
            nxt = [n for n in dict.fromkeys(routed + self._next_from(ready_parents, sources))
                   if n != END]

    def astream(self, input: Any, config: RunnableConfig | None = None,  # noqa: A002,A003
                stream_mode: str = "updates"):
        for chunk in self.stream(input, config, stream_mode=stream_mode):
            yield chunk

    # -- state reads ----------------------------------------------------------

    def get_state(self, config: RunnableConfig | None = None) -> dict:
        cfg = ensure_config(config)
        if self.checkpointer is None:
            raise RuntimeError("get_state needs a checkpointer")
        cp = self.checkpointer.get(cfg)
        if cp is None:
            return {"values": {}, "next": [], "checkpoint_id": None}
        return {"values": cp.get("channel_values") or {}, "next": cp.get("next") or [],
                "checkpoint_id": cp.get("id"), "step": cp.get("step"),
                "pending": cp.get("pending")}

    def update_state(self, config: RunnableConfig | None, values: dict,  # noqa: A002,A003
                     as_node: str | None = None) -> dict:
        cfg = ensure_config(config)
        if self.checkpointer is None:
            raise RuntimeError("update_state needs a checkpointer")
        cp = self.checkpointer.get(cfg) or {"channel_values": {}, "step": 0}
        state = self._apply_update(dict(cp.get("channel_values") or {}), values)
        if as_node is not None:
            if as_node not in self.nodes:
                raise ValueError(f"update_state(as_node={as_node!r}): unknown node")
            nxt: list[str] = [d for d in self._out.get(as_node, []) if d != END]
        else:
            nxt = list(cp.get("next") or [])
        self._checkpoint(cfg, int(cp.get("step") or 0) + 1, state, nxt, cp.get("pending"))
        return {"values": state, "next": nxt}


# ---------------------------------------------------------------------------
# the interrupt() seam - the node-facing API
# ---------------------------------------------------------------------------


def interrupt(value: Any) -> Any:
    """Park the graph. Called INSIDE a node: the first call raises the park;
    on resume the node re-runs from its top and the n-th interrupt() call
    RETURNS the n-th resume value (or raises the park again when that slot is
    still unanswered). Outside a graph run it is an honest refusal."""
    ctx = getattr(CompiledStateGraph._tls, "resume", None)
    if not ctx or ctx.get("node") is None:
        raise RuntimeError(
            "interrupt() must be called inside a graph node execution "
            "(and the graph must be compiled with a checkpointer to park)")
    idx = int(ctx.get("calls", 0))
    ctx["calls"] = idx + 1
    resumes = ctx.get("resumes") or {}
    if idx in resumes and resumes[idx] is not RESUME_MISSING:
        return resumes[idx]
    raise GraphInterrupt(ctx["node"], idx, value)
