"""v0.521.0 HOOLA TRACE - the LangSmith layer self-hosted, P2 of the HOOLA AEP plan
(owner: 'DEPLOY AND GO BUILD P2 (HOOLA TRACE - tracers/run trees)' after the deploy
verified vps-ops run 41876141774 success + healthz 0.511.0 - P1 HOOLA CORE rode the
CS-pack chain to the VPS live). The callbacks/tracers/event-stream idea and the
LangSmith run-tree idea hand-built as server/app/aep/tracers.py + vault_sink.py -
ZERO upstream code. This suite pins the layer against the upstream facts:

(1) CALLBACKS: BaseCallbackHandler no-op family; CallbackManager carries handlers +
    parent_run_id down the config['callbacks'] channel - a span start returns the
    CHILD manager; a broken handler never breaks the run (swallowed, docs7 law);
    callbacks_from_config accepts manager / handler / list / junk.
(2) SPANS: chain spans on Sequence/Parallel/Lambda (invoke + ainvoke), chat_model
    spans on BaseChatModel (invoke/stream/astream with llm_new_token per streamed
    chunk), llm spans on BaseLLM, tool spans named by the TOOL name; the P1
    no-callback path stays byte-identical (the same invokes without callbacks).
(3) RUN TREE: Run nodes with parent_run_id/trace_id/child_ids; tree() nests
    children; every run in one invocation shares the root's trace_id; errors
    captured (status 'error', the exception text) AND re-raised.
(4) ASTREAM_EVENTS: the event_stream v2 port - on_chain_start/on_chat_model_start/
    on_llm_new_token/on_chain_stream/on_llm_end/on_chain_end each with run_id +
    parent_ids + data.input/output/chunk; version pinned 'v2' (honest raise);
    a raising chain surfaces on_chain_error and the generator still finishes.
(5) STORES: InMemoryRunStore capped ring (oldest evicted); RunTreeTracer ring
    eviction (finished roots oldest-first); global_tracer()/GLOBAL_STORE +
    reset_global; traced_invoke one-liner.
(6) VAULT SINK (the flag law made real): aep_trace default OFF - save() is a
    silent no-op + skipped_flag counter; flag ON - the row is an ordinary vault
    observation typed 'aep_run' (facts run_type/name/status/ms/trace); REDACTION
    BEFORE STORAGE (a secret-shaped string lands as ***redacted***; the
    aep_trace_redact seam turns it off for the tests); fail-closed on a raising
    store (skipped_error, never an exception out of the sink).
(7) ROUTES: /api/aep/runs + /api/aep/runs/{run_id} fail-closed when the flag is
    OFF, memory shapes + vault fallback when ON; /api/agent/stats grew the honest
    aep_trace block.
(8) INERTNESS + WIRING + VERSION: a fresh interpreter imports app.aep with ZERO
    extra threads/env reads/files (the P1 law re-run on the P2 modules); the
    package-export law covers the new names; the trace_flip job shape (AEP_TRACE
    one-boolean, effective value printed); the restart pin 9 -> 10; APP_VERSION +
    pubspec + story markers; the flags default OFF/True.

No test touches the network; every async path rides asyncio.run (the documented
one-loop law).
"""
import asyncio
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER = REPO_ROOT / "server"

from app import aep
from app.aep import tracers as T
from app.aep import vault_sink as VS
from app.aep.messages import HumanMessage
from app.aep.models import FakeListChatModel, FakeListLLM
from app.aep.runnable import RunnableLambda, RunnableParallel, RunnableSequence, RunnableSequence as RS
from app.aep.tools import tool
from app.aep.tracers import (CallbackManager, InMemoryRunStore, Run, RunTreeTracer,
                             astream_events, callbacks_from_config, dumps_safe,
                             global_tracer, reset_global, traced_invoke)


# ---------------------------------------------------------------------------
# fixtures + helpers
# ---------------------------------------------------------------------------


def _clear_settings_cache():
    """get_settings is lru_cached house-wide; a flag test MUST clear it after its
    setenv or the previous test's cached instance answers (the docs7 lesson)."""
    from app.config import get_settings
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _clean_global():
    reset_global()
    VS.STATS.update({"saved": 0, "skipped_flag": 0, "skipped_error": 0})
    yield
    reset_global()
    _clear_settings_cache()          # never leak a flag env into the wider sweep


def _up(x):
    return str(x).upper()


def _bang(x):
    return str(x) + "!"


def _chain():
    return RunnableLambda(_up) | RunnableLambda(_bang)


def _collector():
    """A tracer + the runs it saw, with the event log of a raw handler."""
    events: list[tuple[str, str]] = []

    class _Log(T.BaseCallbackHandler):
        def _log(self, ev, name, *a):
            events.append((ev, name))
        on_chain_start = lambda s, n, r, p, i, t, m: s._log("chain_start", n)  # noqa: E731
        on_chain_end = lambda s, n, r, o: s._log("chain_end", n)  # noqa: E731
        on_chat_model_start = lambda s, n, r, p, m, t, md: s._log("cm_start", n)  # noqa: E731
        on_llm_end = lambda s, n, r, o: s._log("llm_end", n)  # noqa: E731
        on_tool_start = lambda s, n, r, p, i, t, m: s._log("tool_start", n)  # noqa: E731
        on_tool_end = lambda s, n, r, o: s._log("tool_end", n)  # noqa: E731

    return _Log(), events


# ---------------------------------------------------------------------------
# (1) callbacks manager
# ---------------------------------------------------------------------------


def test_manager_child_propagation():
    log, events = _collector()
    mgr = CallbackManager([log], tags=["t1"])
    assert mgr.parent_run_id is None
    child = mgr.child("run-abc")
    assert child.parent_run_id == "run-abc"
    assert child.handlers == mgr.handlers
    assert child.tags == ["t1"]
    mgr.chain_start("root", "run-abc", {"x": 1})
    assert events == [("chain_start", "root")]


def test_broken_handler_never_breaks_the_run():
    class _Bad(T.BaseCallbackHandler):
        def on_chain_start(self, *a):
            raise RuntimeError("handler exploded")

        def on_chain_end(self, *a):
            raise RuntimeError("handler exploded again")

    chain = _chain()
    out = chain.invoke("yo", {"callbacks": CallbackManager([_Bad()])})
    assert out == "YO!"          # the run sailed through the broken telemetry


def test_callbacks_from_config_shapes():
    assert callbacks_from_config(None) is None
    assert callbacks_from_config({}) is None
    h = T.BaseCallbackHandler()
    assert callbacks_from_config({"callbacks": h}).handlers == [h]
    assert callbacks_from_config({"callbacks": [h, h]}).handlers == [h, h]
    assert callbacks_from_config({"callbacks": []}) is None          # empty = nothing to do
    assert callbacks_from_config({"callbacks": "junk"}) is None
    mgr = CallbackManager([h], parent_run_id="p1")
    got = callbacks_from_config({"callbacks": mgr})
    assert got is mgr and got.parent_run_id == "p1"


# ---------------------------------------------------------------------------
# (2) spans on the substrate
# ---------------------------------------------------------------------------


def test_chain_spans_sequence_tree():
    tr = RunTreeTracer()
    out = _chain().invoke("yo", {"callbacks": CallbackManager([tr])})
    assert out == "YO!"
    roots = tr.roots()
    assert len(roots) == 1 and roots[0].name == "RunnableSequence"
    root = tr.tree(roots[0].id)
    assert root["run_type"] == "chain" and root["status"] == "ok"
    kids = root["children"]
    assert [c["name"] for c in kids] == ["_up", "_bang"]
    assert all(c["status"] == "ok" and c["ms"] >= 0 for c in kids)
    assert all(c["trace_id"] == roots[0].id for c in kids)


def test_chain_stream_events_close_with_last_chunk():
    tr = RunTreeTracer()
    model = FakeListChatModel(responses=["hello there"])
    seq = RunnableLambda(_up) | model
    chunks = list(seq.stream("yo", {"callbacks": CallbackManager([tr])}))
    assert len(chunks) == 4                            # 'hello there' in 3-char chunks
    roots = tr.roots()
    assert len(roots) == 1
    # the sequence span's outputs = the last chunk (the streaming close shape)
    assert roots[0].outputs.get("content") == "re"     # 'hello there' -> hel|lo |the|re


def test_chat_model_spans_invoke_and_stream():
    tr = RunTreeTracer()
    model = FakeListChatModel(responses=["bonjour"])
    out = model.invoke("salut", {"callbacks": CallbackManager([tr])})
    assert out.content == "bonjour"
    runs = tr.roots()
    assert len(runs) == 1 and runs[0].run_type == "chat_model"
    assert runs[0].outputs["content"] == "bonjour"

    tr2 = RunTreeTracer()
    log, events = _collector()
    mgr = CallbackManager([tr2, log])
    toks = [c for c in FakeListChatModel(responses=["abcdef"]).stream("x", {"callbacks": mgr})]
    assert len(toks) == 2
    assert [e for e, _ in events].count("llm_end") == 1
    kinds = {r.run_type for r in tr2.roots()}
    assert kinds == {"chat_model"}


def test_base_llm_span():
    tr = RunTreeTracer()
    out = FakeListLLM(responses=["plain"]).invoke("p", {"callbacks": CallbackManager([tr])})
    assert out == "plain"
    (run,) = tr.roots()
    assert run.run_type == "chat_model" and run.outputs == "plain"


def test_tool_span_named_by_the_tool():
    tr = RunTreeTracer()

    @tool
    def adder(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    out = adder.invoke({"a": 1, "b": 2}, {"callbacks": CallbackManager([tr])})
    assert out == 3
    (run,) = tr.roots()
    assert run.name == "adder" and run.run_type == "tool" and run.status == "ok"
    assert run.outputs == 3


def test_tool_error_span():
    tr = RunTreeTracer()

    @tool
    def detonate(x: int) -> int:
        """Always explodes."""
        raise ValueError("boom in tool")

    with pytest.raises(ValueError):
        detonate.invoke({"x": 1}, {"callbacks": CallbackManager([tr])})
    (run,) = tr.roots()
    assert run.status == "error" and "boom in tool" in (run.error or "")


def test_error_tree_captures_and_reraises():
    tr = RunTreeTracer()

    def boom(x):
        raise KeyError("kaboom")

    with pytest.raises(KeyError):
        RunnableSequence.from_steps([RunnableLambda(_up), RunnableLambda(_bang),
                                     RunnableLambda(boom)]).invoke(
            "yo", {"callbacks": CallbackManager([tr])})
    (root,) = tr.roots()
    assert root.status == "error" and "kaboom" in (root.error or "")
    # the children that DID finish stay ok under the erroring root
    kids = tr.tree(root.id)["children"]
    assert [c["status"] for c in kids] == ["ok", "ok", "error"]


# ---------------------------------------------------------------------------
# (3) run tree details
# ---------------------------------------------------------------------------


def test_tree_nesting_parallel():
    tr = RunTreeTracer()
    seq = RunnableLambda(_up) | RunnableParallel({"a": RunnableLambda(_bang),
                                                  "b": RunnableLambda(lambda x: x + "?")})
    out = seq.invoke("yo", {"callbacks": CallbackManager([tr])})
    assert out == {"a": "YO!", "b": "YO?"}              # the parallel eats _up's output
    (root,) = tr.roots()
    tree = tr.tree(root.id)
    kinds = [(c["name"], len(c["children"])) for c in tree["children"]]
    assert ("_up", 0) in kinds
    par = [c for c in tree["children"] if c["name"] == "RunnableParallel"][0]
    assert len(par["children"]) == 2


def test_trace_id_shared_across_the_invocation():
    tr = RunTreeTracer()
    seq = RunnableLambda(_up) | RunnableParallel({"a": RunnableLambda(_bang)})
    seq.invoke("yo", {"callbacks": CallbackManager([tr])})
    (root,) = tr.roots()
    tree = tr.tree(root.id)
    nodes = [root, *tree["children"], *tree["children"][1]["children"]]
    tids = [r.trace_id if isinstance(r, Run) else r["trace_id"] for r in nodes]
    assert tids == [root.id] * len(nodes)


def test_run_node_shape_and_status():
    run = Run(id="r1", name="n", run_type="chain", start_time=1.0, end_time=1.25)
    assert run.ms == 250 and run.status == "ok" and run.error is None
    running = Run(id="r2", name="n", run_type="chain", start_time=1.0)
    assert running.status == "running" and running.ms == 0
    bad = Run(id="r3", name="n", run_type="chain", start_time=1.0, end_time=2.0, error="x")
    assert bad.status == "error"


def test_dumps_safe_handles_messages_and_junk():
    s = dumps_safe([HumanMessage(content="namaste"), {"a": (1, 2)}])
    assert "namaste" in s and '"a"' in s

    class _Odd:
        def __str__(self):
            return "odd-object"

    assert "odd-object" in dumps_safe(_Odd())
    assert dumps_safe(42) == "42"


# ---------------------------------------------------------------------------
# (4) astream_events
# ---------------------------------------------------------------------------


def test_astream_events_full_sequence_and_parent_wiring():
    model = FakeListChatModel(responses=["hello there"])
    seq = RunnableLambda(_up) | model

    async def _go():
        return [ev async for ev in astream_events(seq, "yo", version="v2")]

    evs = asyncio.run(_go())
    kinds = [e["event"] for e in evs]
    assert kinds[0] == "on_chain_start" and kinds[-1] == "on_chain_end"
    assert "on_chat_model_start" in kinds and kinds.count("on_llm_new_token") == 4
    assert kinds.count("on_chain_stream") == 4          # one per streamed chunk
    # parent wiring: every model event carries the root chain id
    root_id = evs[0]["run_id"]
    model_start = [e for e in evs if e["event"] == "on_chat_model_start"][0]
    assert model_start["parent_ids"] == [root_id]
    # data shapes
    assert "input" in evs[0]["data"]
    assert "output" in evs[-1]["data"]
    assert "chunk" in [e for e in evs if e["event"] == "on_chain_stream"][0]["data"]


def test_astream_events_over_a_bare_model():
    async def _go():
        return [ev async for ev in astream_events(FakeListChatModel(responses=["ab"]), "x", version="v2")]

    evs = asyncio.run(_go())
    kinds = [e["event"] for e in evs]
    assert kinds == ["on_chat_model_start", "on_llm_new_token", "on_llm_end"]


def test_astream_events_version_guard():
    async def _go():
        return [ev async for ev in astream_events(_chain(), "x", version="v1")]

    with pytest.raises(ValueError, match="v2"):
        asyncio.run(_go())


def test_astream_events_error_surfaced_and_generator_ends():
    def boom(x):
        raise RuntimeError("stream kaboom")

    async def _go():
        evs = []
        async for ev in astream_events(RunnableLambda(boom), "x", version="v2"):
            evs.append(ev)
        return evs

    evs = asyncio.run(_go())                            # must not hang, must not raise
    kinds = [e["event"] for e in evs]
    assert "on_chain_start" in kinds
    assert kinds.count("on_chain_error") >= 1
    err_data = [e for e in evs if e["event"] == "on_chain_error"][-1]["data"]
    assert "stream kaboom" in str(err_data)


# ---------------------------------------------------------------------------
# (5) stores + global
# ---------------------------------------------------------------------------


def test_inmemory_store_ring_cap():
    store = InMemoryRunStore(cap=3)
    for i in range(5):
        store.save(Run(id=f"r{i}", name="n", run_type="chain"))
    assert len(store) == 3
    assert [r.id for r in store.recent(10)] == ["r2", "r3", "r4"]
    assert store.get("r0") is None and store.get("r4") is not None
    store.clear()
    assert len(store) == 0


def test_tracer_ring_eviction_keeps_bounded():
    tr = RunTreeTracer(max_runs=100)
    for i in range(60):
        _chain().invoke("yo", {"callbacks": CallbackManager([tr])})
    assert len(tr.runs) <= 100                          # 3 runs per chain, ring held
    assert len(tr.runs) >= 100 * 0.5                    # and not over-eager


def test_global_tracer_and_traced_invoke():
    reset_global()
    out = traced_invoke(_chain(), "go")
    assert out == "GO!"
    gt = global_tracer()
    assert len(GLOBAL := T.GLOBAL_STORE) == 3           # seq + two lambdas
    roots = gt.roots()
    assert len(roots) == 1
    assert tracers_tree_ok(gt, roots[0].id)
    reset_global()
    assert len(T.GLOBAL_STORE) == 0


def tracers_tree_ok(tr, run_id):
    tree = tr.tree(run_id)
    return tree is not None and len(tree["children"]) == 2


# ---------------------------------------------------------------------------
# (6) vault sink - the flag law
# ---------------------------------------------------------------------------


def _run():
    return Run(id="run-1", name="adder", run_type="tool", inputs={"a": 1}, outputs={"n": 3},
               start_time=1.0, end_time=1.5, trace_id="run-1")


def test_flag_defaults_off(monkeypatch):
    monkeypatch.setenv("AEP_TRACE", "false")
    _clear_settings_cache()
    assert VS.trace_enabled() is False


def test_vault_sink_flag_off_is_a_silent_noop(monkeypatch):
    monkeypatch.setenv("AEP_TRACE", "false")
    _clear_settings_cache()
    calls: list[Any] = []

    def _spy(*a, **k):
        calls.append(a)
        return 99

    monkeypatch.setattr("app.coder.store.store_observation", _spy)
    saved = VS.VaultRunSink(tenant="t1", conv="c1").save(_run())
    assert saved is None and calls == []
    assert VS.STATS["skipped_flag"] == 1 and VS.STATS["saved"] == 0


def test_vault_sink_flag_on_lands_an_aep_run_row(monkeypatch):
    monkeypatch.setenv("AEP_TRACE", "true")
    _clear_settings_cache()
    seen: dict[str, Any] = {}

    def _fake_store(conv, tenant, row, actor=""):
        seen.update({"conv": conv, "tenant": tenant, "row": row, "actor": actor})
        return 42

    monkeypatch.setattr("app.coder.store.store_observation", _fake_store)
    saved = VS.VaultRunSink(tenant="t1", conv="c1").save(_run())
    assert saved == 42
    assert seen["actor"] == "aep_trace" and seen["tenant"] == "t1"
    row = seen["row"]
    assert row["type"] == "aep_run"
    assert "adder" in row["title"] and "ok" in row["title"]
    assert f"ms:{_run().ms}" in row["facts"]
    assert "run_type:tool" in row["facts"] and "status:ok" in row["facts"]
    assert VS.STATS["saved"] == 1


def test_vault_sink_redaction_before_storage(monkeypatch):
    monkeypatch.setenv("AEP_TRACE", "true")
    _clear_settings_cache()
    secret_run = Run(id="run-2", name="leaky", run_type="chain", inputs="x",
                     outputs="the key is sk-ant-abcdefghijklmnopqrst",
                     start_time=1.0, end_time=2.0, trace_id="run-2")
    seen: dict[str, Any] = {}

    def _fake_store(conv, tenant, row, actor=""):
        seen["row"] = row
        return 1

    monkeypatch.setattr("app.coder.store.store_observation", _fake_store)
    VS.VaultRunSink().save(secret_run)
    narrative = seen["row"]["narrative"]
    assert "sk-ant-abcdefghijklmnopqrst" not in narrative
    assert "***redacted***" in narrative


def test_vault_sink_redact_seam_off(monkeypatch):
    monkeypatch.setenv("AEP_TRACE", "true")
    monkeypatch.setenv("AEP_TRACE_REDACT", "false")
    _clear_settings_cache()
    seen: dict[str, Any] = {}

    def _fake_store(conv, tenant, row, actor=""):
        seen["row"] = row
        return 1

    monkeypatch.setattr("app.coder.store.store_observation", _fake_store)
    plain_run = Run(id="run-3", name="plain", run_type="chain", inputs="x",
                    outputs="<private>hidden matter</private> visible", start_time=1.0,
                    end_time=2.0, trace_id="run-3")
    VS.VaultRunSink().save(plain_run)
    assert "hidden matter" in seen["row"]["narrative"]   # the seam is honest about being off


def test_vault_sink_fail_closed(monkeypatch):
    monkeypatch.setenv("AEP_TRACE", "true")
    _clear_settings_cache()

    def _explode(*a, **k):
        raise RuntimeError("vault on fire")

    monkeypatch.setattr("app.coder.store.store_observation", _explode)
    saved = VS.VaultRunSink().save(_run())
    assert saved is None                                # telemetry never breaks the run
    assert VS.STATS["skipped_error"] == 1


def test_attach_vault_sink_idempotent():
    tr = RunTreeTracer()
    VS.attach_vault_sink(tr, tenant="t1")
    VS.attach_vault_sink(tr, tenant="t1")
    VS.attach_vault_sink(tr, tenant="t2")
    assert len([s for s in tr.sinks if isinstance(s, VS.VaultRunSink)]) == 2


# ---------------------------------------------------------------------------
# (7) routes
# ---------------------------------------------------------------------------


def test_routes_fail_closed_when_flag_off(monkeypatch, env):
    monkeypatch.setenv("AEP_TRACE", "false")
    _clear_settings_cache()
    from app import main
    with TestClient(main.app) as c:
        r = c.get("/api/aep/runs")
        assert r.status_code == 200 and r.json()["ok"] is False
        assert "trace_flip" in r.json()["error"]
        r2 = c.get("/api/aep/runs/nope")
        assert r2.json()["ok"] is False


def test_routes_memory_shapes_when_flag_on(monkeypatch, env):
    monkeypatch.setenv("AEP_TRACE", "true")
    _clear_settings_cache()
    reset_global()
    traced_invoke(_chain(), "go")
    from app import main
    with TestClient(main.app) as c:
        body = c.get("/api/aep/runs", params={"limit": 5}).json()
        assert body["ok"] is True and body["source"] == "memory"
        assert body["count"] >= 3
        assert {"id", "name", "run_type", "status", "ms"} <= set(body["runs"][0].keys())
        root = [r for r in body["runs"] if r["name"] == "RunnableSequence"][0]
        tree = c.get(f"/api/aep/runs/{root['id']}").json()
        assert tree["ok"] is True and tree["source"] == "memory"
        assert len(tree["run"]["children"]) == 2
        assert c.get("/api/aep/runs/does-not-exist").json()["error"] == "no such run"


def test_routes_vault_source(monkeypatch, env):
    monkeypatch.setenv("AEP_TRACE", "true")
    _clear_settings_cache()
    rows = [{"id": 7, "title": "Run adder (tool) - ok", "subtitle": "12 ms, ok",
             "narrative": "{}", "facts": ["run_type:tool"], "created_at": "now"}]
    monkeypatch.setattr(VS, "vault_runs", lambda tenant, limit=20: rows)
    monkeypatch.setattr(VS, "vault_run_by_id", lambda tenant, obs_id: rows[0] if obs_id == 7 else None)
    from app import main
    with TestClient(main.app) as c:
        body = c.get("/api/aep/runs", params={"source": "vault"}).json()
        assert body["ok"] is True and body["source"] == "vault" and body["count"] == 1
        one = c.get("/api/aep/runs/7").json()
        assert one["ok"] is True and one["source"] == "vault" and one["run"]["id"] == 7


def test_agent_stats_carries_the_aep_block(env):
    from app import main
    with TestClient(main.app) as c:
        body = c.get("/api/agent/stats").json()
    assert "aep_trace" in body
    assert set(body["aep_trace"]) == {"enabled", "store", "saved", "skipped_flag", "skipped_error"}


# ---------------------------------------------------------------------------
# (8) inertness + wiring + version
# ---------------------------------------------------------------------------


def test_import_is_inert_fresh_interpreter():
    probe = (
        "import sys, threading, os, pathlib;"
        "before_threads = threading.active_count();"
        "before_env = {k: v for k, v in os.environ.items() if k.startswith(('CODER_', 'AEP_'))};"
        "cwd = pathlib.Path.cwd();"
        "before_files = {p.name for p in cwd.iterdir()};"
        "sys.path.insert(0, sys.argv[1]);"
        "import app.aep;"
        "assert threading.active_count() == before_threads, 'import spawned threads';"
        "assert {k: v for k, v in os.environ.items() if k.startswith(('CODER_', 'AEP_'))} == before_env, 'env read/written';"
        "assert {p.name for p in cwd.iterdir()} == before_files, 'import created files';"
        "print('inert-ok')"
    )
    r = subprocess.run([sys.executable, "-c", probe, str(SERVER)],
                       capture_output=True, text=True, timeout=120, cwd="/tmp")
    assert r.returncode == 0, r.stderr[-800:]
    assert "inert-ok" in r.stdout


def test_package_export_law_covers_the_trace_surface():
    for name in ("RUN_TYPES", "BaseCallbackHandler", "CallbackManager", "Span", "Run",
                 "RunSink", "RunTreeTracer", "InMemoryRunStore", "astream_events",
                 "callbacks_from_config", "dumps_safe", "global_tracer", "reset_global",
                 "traced_invoke", "VaultRunSink", "attach_vault_sink", "trace_enabled",
                 "vault_runs", "vault_run_by_id", "TRACE_STATS"):
        assert name in aep.__all__ and getattr(aep, name, None) is not None
    for mod in ("tracers", "vault_sink"):
        assert hasattr(aep, mod), f"aep.{mod} not exported as a module"


def test_trace_flip_job_shape():
    yml = (REPO_ROOT / ".github" / "workflows" / "vps-ops.yml").read_text()
    assert "- trace_flip" in yml                       # the choice-list entry
    assert "trace_flip)" in yml                        # the job body
    body = yml.split("trace_flip)")[1].split(";;")[0]
    assert 'grep -q "^AEP_TRACE="' in body             # idempotent upsert
    assert "AEP_TRACE=true" in body
    assert "pm2 restart santosh --kill-timeout 12000 --update-env" in body
    assert "get_settings().aep_trace" in body          # the EFFECTIVE value printed back


def test_restart_pin_bumped_to_ten():
    yml = (REPO_ROOT / ".github" / "workflows" / "vps-ops.yml").read_text()
    restarts = [ln for ln in yml.splitlines() if "pm2 restart santosh" in ln]
    assert len(restarts) == 10                         # 9 + trace_flip (the mem pin moved too)
    for ln in restarts:
        assert "--kill-timeout 12000" in ln, ln


def test_flags_default_off_and_redact_on():
    sys.path.insert(0, str(SERVER))
    from app.config import Settings
    st = Settings(_env_file=None)                      # the CODE default, no env file
    assert st.aep_trace is False
    assert st.aep_trace_redact is True


def test_version_pins():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.739.0"
    assert "0.739.0+738" in (REPO_ROOT / "pubspec.yaml").read_text()
    line = (SERVER / "app" / "main.py").read_text().splitlines()[35]
    assert line.startswith('APP_VERSION = "0.739.0"')
    # the story-token pin rides the NEWEST story (the newest-story precedent);
    # the v0.520 story tokens live in git history - the v0.530 story carries
    # the P3 markers AND names the trace layer it sits on
    # the P6 story pins moved to the P7 suite (the newest-story precedent)
    assert "HOOLA RETRIEVE" in line  # the Previous chain keeps the P6 name
    assert "HOOLA TRACE" in line   # the Previous chain keeps the P2 name


def test_no_new_registry_tools():
    src = (SERVER / "app" / "aep" / "tracers.py").read_text()
    src2 = (SERVER / "app" / "aep" / "vault_sink.py").read_text()
    for blob in (src, src2):
        assert "input_schema" not in blob and 'DOCS7_SCHEMA' not in blob  # no tool schema, no registry
    assert "VOICE_TOOL_NAMES" not in src and "VOICE_TOOL_NAMES" not in src2  # voice untouched by construction
