"""G7 of docs/LANGGRAPH_TURN_PLAN.md: the turn graph is the DEFAULT chat turn engine.

(1) chat_graph is on by default and a plain turn runs on the graph without anyone setting CHAT_GRAPH.
(2) CHAT_GRAPH=false is the emergency rollback: the old while-loop answers, the graph never runs.
(3) A box without langgraph keeps answering: the switch is forced off with ONE loud warning, the old loop answers,
    and the same holds when turngraph itself cannot import langgraph (the second belt in run_steps).
(4) The retired POST /api/aep/turn lane is gone; what app/aep still serves (the run explorer, leads/scale.py) stays."""
import asyncio
import importlib.util
import logging

import pytest
from fastapi.testclient import TestClient

from tests.test_bazar import bz  # noqa: F401  (fixture)
from tests.test_g0_turngraph import Scripted, _fake_dispatch, _new_conv, _rows, tu, txt


def _turn(script, ask="namaste"):
    from app.agent import run_turn, santosh, set_client
    client = Scripted(list(script))
    set_client(client)
    conv = _new_conv()
    out = asyncio.run(asyncio.wait_for(run_turn(conv, ask, tenant_id="default"), 120))
    return out, conv, client


def _fresh_settings(monkeypatch, extra=None):
    monkeypatch.setenv("CONSOLE_V2", "false")
    monkeypatch.setenv("CONSOLE_STREAM", "false")
    monkeypatch.setenv("DRAFT_CHECK_AI", "false")
    for k, v in (extra or {}).items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    return get_settings()


def test_graph_is_the_default_engine(bz, monkeypatch):  # noqa: F811
    monkeypatch.delenv("CHAT_GRAPH", raising=False)
    st = _fresh_settings(monkeypatch)
    assert st.chat_graph is True
    from app import main
    assert main.turn_engine() == "graph"
    _fake_dispatch(monkeypatch)
    from app.agent import turngraph
    n0 = turngraph.STATS["turns"]
    out, conv, client = _turn([[tu(1, "list_reminders")], txt("Aapke 3 reminders hain.")], "mere reminders batao")
    assert out == "Aapke 3 reminders hain."
    assert turngraph.STATS["turns"] == n0 + 1           # the graph answered
    assert client.calls == 2
    assert ("assistant", "Aapke 3 reminders hain.") in _rows(conv)


def test_chat_graph_false_is_the_old_loop(bz, monkeypatch):  # noqa: F811
    _fresh_settings(monkeypatch, {"CHAT_GRAPH": "false"})
    from app import main
    assert main.turn_engine() == "old-loop"
    _fake_dispatch(monkeypatch)
    from app.agent import turngraph

    async def boom(*a, **k):
        raise AssertionError("the graph ran with CHAT_GRAPH=false")

    monkeypatch.setattr(turngraph, "run_steps", boom)
    out, conv, client = _turn([[tu(1, "list_reminders")], txt("Aapke 3 reminders hain.")], "mere reminders batao")
    assert out == "Aapke 3 reminders hain."
    assert client.calls == 2


def test_missing_langgraph_forces_the_old_loop_with_one_warning(bz, monkeypatch, caplog):  # noqa: F811
    from app import config
    real = importlib.util.find_spec

    def no_langgraph(name, *a, **k):
        if name.startswith("langgraph"):
            return None
        return real(name, *a, **k)

    monkeypatch.setattr(config.importlib.util, "find_spec", no_langgraph)
    monkeypatch.setattr(config, "_GRAPH_OK", [])
    monkeypatch.setattr(config, "_GRAPH_WARNED", [])
    monkeypatch.delenv("CHAT_GRAPH", raising=False)
    with caplog.at_level(logging.ERROR, logger="santosh.config"):
        st = _fresh_settings(monkeypatch)
        assert st.chat_graph is False                    # forced off: every reader takes the old loop
        config.get_settings.cache_clear()
        assert config.get_settings().chat_graph is False
    said = [r for r in caplog.records if r.name == "santosh.config" and "not installed" in r.getMessage()]
    assert len(said) == 1                                # one loud warning, not one per settings read
    assert said[0].levelno >= logging.ERROR
    _fake_dispatch(monkeypatch)
    from app.agent import turngraph

    async def boom(*a, **k):
        raise AssertionError("the graph ran without langgraph")

    monkeypatch.setattr(turngraph, "run_steps", boom)
    out, conv, client = _turn([[tu(1, "list_reminders")], txt("Aapke 3 reminders hain.")], "mere reminders batao")
    assert out == "Aapke 3 reminders hain."              # chat still answers
    out2, _c, _cl = _turn([txt("Namaste ji.")], "namaste")
    assert out2 == "Namaste ji."                         # and keeps answering (no lock / ticket left behind)


def test_turngraph_without_langgraph_falls_back_once(bz, monkeypatch, caplog):  # noqa: F811
    """The second belt: chat_graph on, but turngraph's own import of langgraph failed -> the old loop, said once."""
    _fresh_settings(monkeypatch)
    _fake_dispatch(monkeypatch)
    from app.agent import turngraph
    monkeypatch.setattr(turngraph, "AVAILABLE", False)
    monkeypatch.setattr(turngraph, "_WARNED_MISSING", [])
    n0, f0 = turngraph.STATS["turns"], turngraph.STATS["fallback"]
    with caplog.at_level(logging.WARNING, logger="santosh.turngraph"):
        out, _c, _cl = _turn([[tu(1, "list_reminders")], txt("Aapke 3 reminders hain.")], "mere reminders batao")
        out2, _c2, _cl2 = _turn([txt("Namaste ji.")], "namaste")
    assert (out, out2) == ("Aapke 3 reminders hain.", "Namaste ji.")
    assert turngraph.STATS["turns"] == n0                # the graph never ran
    assert turngraph.STATS["fallback"] == f0 + 2
    said = [r for r in caplog.records if r.name == "santosh.turngraph" and "cannot be imported" in r.getMessage()]
    assert len(said) == 1


def test_startup_names_the_turn_engine(env, monkeypatch, caplog):  # noqa: F811
    from app import main
    with caplog.at_level(logging.INFO, logger="santosh.api"):
        main._say_turn_engine()
    assert any("turn graph" in r.getMessage() for r in caplog.records)
    caplog.clear()
    monkeypatch.setenv("CHAT_GRAPH", "false")
    main.get_settings.cache_clear()
    with caplog.at_level(logging.INFO, logger="santosh.api"):
        main._say_turn_engine()
    warn = [r for r in caplog.records if "OLD loop" in r.getMessage()]
    assert warn and warn[0].levelno == logging.WARNING


def test_aep_turn_lane_is_retired_and_the_kept_parts_stay(env):  # noqa: F811
    from app import main
    paths = {getattr(r, "path", "") for r in main.app.routes}
    assert "/api/aep/turn/{conversation_id}" not in paths
    assert "/api/aep/runs" in paths and "/api/aep/runs/{run_id}" in paths
    assert importlib.util.find_spec("app.agent.aeptune") is None
    from app.aep import graph, tracers, vault_sink   # noqa: F401 - still used by leads/scale.py + the run explorer
    from app.leads import scale   # noqa: F401
    c = TestClient(main.app)
    r = c.post("/api/aep/turn/x", json={"text": "hi"})
    assert r.status_code in (404, 405)


@pytest.mark.parametrize("name", ["_steps_inner"])
def test_old_loop_is_marked_as_the_rollback(name):
    from app.agent import santosh
    doc = getattr(santosh, name).__doc__ or ""
    assert "ROLLBACK" in doc and "CHAT_GRAPH=false" in doc
