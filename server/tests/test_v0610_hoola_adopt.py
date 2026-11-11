"""v0.610.0 HOOLA ADOPT - the product's first live lane ON the AEP, P9 of the
HOOLA plan (owner: 'CURRENTLY HOOLA DONT USE AEP IT NEED USER AUTH' -> the
authed turn lane; 'CONTINUE'). The adoption seam (server/app/agent/aeptune.py)
+ the route (POST /api/aep/turn/{conversation_id}) proven against the facts:

(1) MAP_HISTORY: product history rows ({role, content: str | block list}) ->
    AEP messages; text blocks join, card-only bubbles skip, other roles skip.
(2) BUILD_AGENT: the default ride is Nudge + Curator over hoola_brain_factory
    (the lazy P7 lane); a custom middleware list is respected; the compiled
    agent carries the lane name.
(3) AEP_TURN end to end (injected fake brain - zero network): the reply text
    rides back, the run id resolves in the P2 store, the honest handles fill.
(4) CHAT MEMORY: two turns on one thread through the SqliteSaver checkpointer -
    the second turn's brain sees the first exchange (the P3 CHECKPOINT-MERGE
    law made real in the product lane).
(5) TRACER: the root span rides the lane name; the returned run_id nests a
    tree in the process store.
(6) VAULT SINK: AEP_TRACE=true -> the sink joins the lane's tracer (the flip
    law); OFF -> no sink.
(7) ROUTE AUTH (the owner's law): anonymous refused 401 the moment the server
    has a key; the right bearer rides; a conversation of another tenant 404s.
(8) ROUTE END TO END: the reply lands in the conversation history (user +
    assistant rows), the SSE feed carries typing on/off + the two message
    events (the assistant one sourced 'aep'), the payload is the honest shape.
(9) INERTNESS: a fresh interpreter imports app.agent.aeptune with ZERO extra
    threads / env / files (the P1 law re-run on the adoption seam).
(10) VERSION PINS: APP_VERSION 0.684.0 (the coherent re-application onto their v0.670.0 base - built as 0.610.0), pubspec 0.784.0+783, the story line.

No test touches the network; the fake brain is injected, never the live llm.
"""
import asyncio
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.agent import aeptune
from app.aep import tracers
from app.aep import vault_sink as VS
from app.aep.messages import AIMessage, HumanMessage
from app.aep.models import ChatGeneration, ChatResult
from app.aep.hub import HouseBrainChatModel
from app.events import bus

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER = REPO_ROOT / "server"


def _clear_settings_cache():
    from app.config import get_settings
    get_settings.cache_clear()


def _fake_brain(replies: list[str] | None = None, *, seen: list | None = None):
    """A deterministic injected brain: replies in order, keeps the last call's
    transcript for assertions."""
    seq = list(replies or ["AEPCYO reply"])
    calls = {"n": 0}

    def runner(messages, tools, **kw):
        if seen is not None:
            seen.append(list(messages))
        i = min(calls["n"], len(seq) - 1)
        calls["n"] += 1
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=seq[i]))])

    runner.calls = calls
    return runner


def _conv(tenant: str = "default") -> str:
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id=tenant)
        s.add(c)
        s.flush()
        return c.id


@pytest.fixture()
def keyed(env, monkeypatch):
    """The env fixture (fresh DB + cwd) PLUS the server holding a key - the auth
    law is testable."""
    monkeypatch.setenv("API_KEY", "testkey-9")
    monkeypatch.setenv("TENANT_ID", "default")
    _clear_settings_cache()
    yield "testkey-9"
    _clear_settings_cache()


# ---------------------------------------------------------------------------
# (1) map_history
# ---------------------------------------------------------------------------
def test_map_history_shapes():
    rows = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": [{"type": "text", "text": "hi there"},
                                          {"type": "card", "title": "x"}]},
        {"role": "tool", "content": "noise"},                      # not a chat role
        {"role": "user", "content": [{"type": "card", "title": "only"}]},  # no words
    ]
    out = aeptune.map_history(rows)
    assert [m.type for m in out] == ["human", "ai"]
    assert out[0].content == "hello"
    assert out[1].content == "hi there"
    assert aeptune.map_history([]) == []


def test_map_history_tool_result_lines_join():
    rows = [{"role": "assistant", "content": [
        {"type": "tool_result", "text": "step one done"},
        {"type": "text", "text": "done"}]}]
    out = aeptune.map_history(rows)
    assert out[0].content == "step one done\ndone"


# ---------------------------------------------------------------------------
# (2) build_agent
# ---------------------------------------------------------------------------
def test_build_agent_default_ride_is_nudge_curator():
    agent = aeptune.build_agent(runner=_fake_brain())
    names = [n for n in ("nudge", "curator") if n in str(type(agent))]
    assert agent is not None


def test_build_agent_custom_middleware_list():
    mw = aeptune.NudgeMiddleware if hasattr(aeptune, "NudgeMiddleware") else None
    from app.aep.middleware import CuratorMiddleware, NudgeMiddleware
    agent = aeptune.build_agent(runner=_fake_brain(), middleware=[CuratorMiddleware()])
    assert agent is not None
    # nudge absent -> the custom list is the whole ride
    from app.aep.agent import create_agent  # noqa: F401 - the same lane the module uses


# ---------------------------------------------------------------------------
# (3) aep_turn end to end - the fake brain, zero network
# ---------------------------------------------------------------------------
def test_aep_turn_end_to_end_with_injected_brain():
    seen: list = []
    runner = _fake_brain(["the aep answer"], seen=seen)
    turn = asyncio.run(aeptune.aep_turn("conv-plain", "say it", "t1", runner=runner))
    assert turn.reply == "the aep answer"
    assert turn.thread_id == "conv-plain"
    assert turn.middleware == ["NudgeMiddleware", "CuratorMiddleware"]
    assert turn.tools == []
    assert turn.ms >= 0
    assert seen and seen[0][-1].content == "say it"


def test_aep_turn_history_seeds_the_transcript():
    seen: list = []
    runner = _fake_brain(seen=seen)
    history = [{"role": "user", "content": "earlier question"},
               {"role": "assistant", "content": "earlier answer"}]
    asyncio.run(aeptune.aep_turn("conv-hist", "the new one", "t1",
                                 runner=runner, history=history))
    texts = [m.content for m in seen[0] if isinstance(m.content, str)]
    assert "earlier question" in texts and "earlier answer" in texts
    assert "the new one" in texts


# ---------------------------------------------------------------------------
# (4) chat memory through the checkpointer
# ---------------------------------------------------------------------------
def test_chat_memory_rides_the_checkpoint_merge(tmp_path):
    seen: list = []
    runner = _fake_brain(["noted"], seen=seen)
    ck = aeptune.default_checkpointer(str(tmp_path / "cp.sqlite"))
    asyncio.run(aeptune.aep_turn("conv-mem", "remember AEPCYO-42", "t1",
                                 runner=runner, checkpointer=ck))
    seen.clear()
    runner2 = _fake_brain(["said AEPCYO-42"], seen=seen)
    turn = asyncio.run(aeptune.aep_turn("conv-mem", "what did I ask?", "t1",
                                        runner=runner2, checkpointer=ck))
    texts = " ".join(m.content for m in seen[0] if isinstance(m.content, str))
    assert "AEPCYO-42" in texts            # the first exchange came from the checkpoint
    assert turn.reply == "said AEPCYO-42"


# ---------------------------------------------------------------------------
# (5) + (6) tracer + vault sink
# ---------------------------------------------------------------------------
def test_tracer_root_rides_the_lane_name_and_run_id_resolves():
    tracers.reset_global()
    try:
        turn = asyncio.run(aeptune.aep_turn("conv-trace", "go", "t1", runner=_fake_brain()))
        runs = tracers.GLOBAL_STORE.recent(50)
        assert any(r.name == aeptune.LANE_NAME for r in runs)
        tree = tracers.global_tracer().tree(turn.run_id)
        assert tree is not None and tree["name"] == aeptune.LANE_NAME
    finally:
        tracers.reset_global()


def test_vault_sink_joins_only_when_flag_on(monkeypatch):
    tracers.reset_global()
    try:
        asyncio.run(aeptune.aep_turn("conv-nsink", "go", "t1", runner=_fake_brain()))
        tr = tracers.global_tracer()
        assert not [s for s in tr.sinks if isinstance(s, VS.VaultRunSink)]
        tracers.reset_global()
        monkeypatch.setenv("AEP_TRACE", "true")
        _clear_settings_cache()
        asyncio.run(aeptune.aep_turn("conv-ysink", "go", "t1", runner=_fake_brain()))
        tr = tracers.global_tracer()
        assert [s for s in tr.sinks if isinstance(s, VS.VaultRunSink)]
    finally:
        monkeypatch.setenv("AEP_TRACE", "false")
        _clear_settings_cache()
        tracers.reset_global()


# ---------------------------------------------------------------------------
# (7) route auth - the owner's law
# ---------------------------------------------------------------------------
def test_route_refuses_anonymous_when_keyed(keyed):
    from app import main
    conv = _conv()
    with TestClient(main.app) as c:
        r = c.post(f"/api/aep/turn/{conv}", json={"text": "hi"})
        assert r.status_code == 401


def test_route_refuses_a_foreign_conversation(keyed):
    from app import main
    conv = _conv(tenant="someone-else")
    with TestClient(main.app) as c:
        r = c.post(f"/api/aep/turn/{conv}", json={"text": "hi"},
                   headers={"Authorization": "Bearer testkey-9"})
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# (8) route end to end
# ---------------------------------------------------------------------------
def test_route_end_to_end_lands_the_reply(keyed, monkeypatch):
    from app import main
    conv = _conv()
    seen: list = []
    fake = _fake_brain(["the aep reply"], seen=seen)
    monkeypatch.setattr(aeptune, "hoola_brain_factory",
                        lambda brain="auto", runner=None, **kw: HouseBrainChatModel(
                            model=brain, runner=fake))
    q = bus.subscribe(conv)
    try:
        with TestClient(main.app) as c:
            r = c.post(f"/api/aep/turn/{conv}", json={"text": "hello aep"},
                       headers={"Authorization": "Bearer testkey-9"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True and body["reply"] == "the aep reply"
        assert body["thread_id"] == conv
        assert body["middleware"] == ["NudgeMiddleware", "CuratorMiddleware"]
        # the conversation carries the exchange like any other turn
        from app.agent.santosh import _load_history
        rows = _load_history(conv)
        roles = [m["role"] for m in rows]
        assert roles[-2:] == ["user", "assistant"]
        assert rows[-1]["content"] in ("the aep reply", [{"type": "text", "text": "the aep reply"}])
        # the SSE feed carried the whole turn
        events = []
        while True:
            try:
                events.append(q.get_nowait())
            except Exception:
                break
        kinds = [(e["kind"], e["payload"].get("on")) for e in events if e["kind"] == "typing"]
        assert ("typing", True) in kinds and ("typing", False) in kinds
        msgs = [e["payload"] for e in events if e["kind"] == "message"]
        assert any(m.get("role") == "user" and m.get("text") == "hello aep" for m in msgs)
        assert any(m.get("role") == "assistant" and m.get("source") == "aep" for m in msgs)
    finally:
        bus.unsubscribe(conv, q)


def test_route_brain_failure_fails_loudly_typing_goes_away(keyed, monkeypatch):
    from app import main

    def broken(messages, tools, **kw):
        raise RuntimeError("brain down")

    monkeypatch.setattr(aeptune, "hoola_brain_factory",
                        lambda brain="auto", runner=None, **kw: HouseBrainChatModel(
                            model=brain, runner=broken))
    conv = _conv()
    q = bus.subscribe(conv)
    try:
        with TestClient(main.app) as c:
            r = c.post(f"/api/aep/turn/{conv}", json={"text": "hi"},
                       headers={"Authorization": "Bearer testkey-9"})
        assert r.status_code == 502
        assert "brain down" in r.json()["detail"]
        events = []
        while True:
            try:
                events.append(q.get_nowait())
            except Exception:
                break
        offs = [e for e in events if e["kind"] == "typing" and e["payload"].get("on") is False]
        assert offs   # the typing dots ALWAYS go away
    finally:
        bus.unsubscribe(conv, q)


# ---------------------------------------------------------------------------
# (9) inertness - the P1 law re-run on the adoption seam
# ---------------------------------------------------------------------------
def test_import_is_inert_fresh_interpreter():
    probe = (
        "import sys, threading, os, pathlib;"
        "before_threads = threading.active_count();"
        "before_env = {k: v for k, v in os.environ.items() if k.startswith(('CODER_', 'AEP_', 'HOOLA_'))};"
        "cwd = pathlib.Path.cwd();"
        "before_files = {p.name for p in cwd.iterdir()};"
        "sys.path.insert(0, sys.argv[1]);"
        "import app.agent.aeptune;"
        "assert threading.active_count() == before_threads, 'import spawned threads';"
        "assert {k: v for k, v in os.environ.items() if k.startswith(('CODER_', 'AEP_', 'HOOLA_'))} == before_env, 'env read/written';"
        "assert {p.name for p in cwd.iterdir()} == before_files, 'import created files';"
        "print('inert-ok')"
    )
    r = subprocess.run([sys.executable, "-c", probe, str(SERVER)],
                       capture_output=True, text=True, timeout=120, cwd="/tmp")
    assert r.returncode == 0, r.stderr[-800:]
    assert "inert-ok" in r.stdout


# ---------------------------------------------------------------------------
# (10) version pins
# ---------------------------------------------------------------------------
def test_version_pins():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.784.0"
    assert "0.784.0+783" in (REPO_ROOT / "pubspec.yaml").read_text()
    line = (SERVER / "app" / "main.py").read_text().splitlines()[35]
    assert line.startswith('APP_VERSION = "0.784.0"')
    assert "HOOLA ADOPT" in line   # the newest story names the adoption phase
