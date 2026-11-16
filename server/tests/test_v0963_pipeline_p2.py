"""v0.963 HOOLA PIPELINE P2 - a one-part chat message through the Box: the job sheet, the hand-off package, the final
check, the outage record and the 30-minute same model; off = today's turn exactly. No model call, no network."""
from __future__ import annotations

import asyncio
import importlib.util
import json
import pathlib
import time

import pytest

_spec = importlib.util.spec_from_file_location(
    "_p1", pathlib.Path(__file__).with_name("test_v0961_pipeline_choose.py"))
_p1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_p1)


@pytest.fixture
def box(env, tmp_path, monkeypatch):
    monkeypatch.setenv("PIPELINE_DIR", str(tmp_path / "pl"))
    monkeypatch.setenv("PIPELINE_ON", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.pipeline import store, turnbox as T, box as B
    store.root().mkdir(parents=True, exist_ok=True)
    (store.root() / "current.json").write_text(json.dumps(_p1.doc()))
    T._TABLES.update({"mtime": None, "doc": None})
    T._OUT.clear()
    B._STICKY.clear()
    from app.agent import llm, providers
    monkeypatch.setattr(llm, "cheap_brain", lambda: "glm")
    monkeypatch.setattr(providers, "ready", lambda m: True)
    tok = llm.MODEL_NOW.set("")
    yield T
    llm.MODEL_NOW.reset(tok)
    get_settings.cache_clear()


def test_off_is_todays_turn(env, tmp_path, monkeypatch):
    monkeypatch.setenv("PIPELINE_DIR", str(tmp_path / "pl"))
    from app.config import get_settings
    get_settings.cache_clear()
    assert get_settings().pipeline_on is False
    from app.pipeline import turnbox as T
    assert T.begin("c1", "t", "hi") is None
    assert T.end(None, "x") is None


def test_one_part_runs_on_the_chosen_model_and_the_sheet_closes(box):
    from app.agent import llm
    from app.pipeline import sheet as S, box as B
    box.end(box.begin("c0", "t1", "warm"), "ok")   # the first call of a process loads its modules (once)
    B._STICKY.clear()
    b = box.begin("c1", "t1", "Agar 3 machine 5 din mein 120 piece banati hain to 7 machine 9 din mein kitne?")
    assert llm.MODEL_NOW.get() == "openrouter:a/high1" and box.APPLIED.get() is True
    sh = S.get(b["sheet"]["id"])
    p = sh["parts"][0]
    assert sh["status"] == "running" and p["state"] == "running" and p["kind"] == "reason" and p["level"] == "HIGH"
    assert p["applied"] and p["model"]["id"] == "a/high1" and len(p["backups"]) == 2
    assert sh["box_ms"] < 30                       # no added delay: code only, the tables copy kept in memory
    chk = box.end(b, "Jawab 168 piece.")
    assert chk["ok"] and chk["checked"] == []      # no tool ran: no facts list to hold a figure to
    assert llm.MODEL_NOW.get() == "" and box.APPLIED.get() is False
    sh = S.get(b["sheet"]["id"])
    assert sh["status"] == "done" and sh["parts"][0]["state"] == "done"
    assert sh["parts"][0]["out"]["result"] == "Jawab 168 piece."
    assert B.recall("c1", "reason", "HIGH")["id"] == "a/high1"


@pytest.mark.parametrize("kw,why", [
    ({"voice": True}, "live call"),
    ({"actor": "routine"}, "routine turn"),
])
def test_not_through_the_box_for_calls_and_background(box, kw, why):
    from app.agent import llm
    b = box.begin("c2", "t", "hi", **kw)
    p = b["sheet"]["parts"][0]
    assert not p["applied"] and why in p["not_applied"] and llm.MODEL_NOW.get() == ""
    box.end(b, "ok")


def test_several_parts_and_media_wait_for_later_phases(box):
    from app.agent import llm
    b = box.begin("c3", "t", "Find prices, and then make a table; then a PDF")
    assert "P3" in b["sheet"]["parts"][0]["not_applied"] and llm.MODEL_NOW.get() == ""
    box.end(b, "x")
    b = box.begin("c3", "t", "Ek Diwali sale ka poster banao")
    assert "image.make" in b["sheet"]["parts"][0]["not_applied"] and llm.MODEL_NOW.get() == ""
    box.end(b, "x")


def test_not_applied_when_chat_is_not_on_the_openrouter_brain(box, monkeypatch):
    from app.agent import llm
    monkeypatch.setattr(llm, "cheap_brain", lambda: None)
    b = box.begin("c4", "t", "hi")
    assert "OpenRouter brain" in b["sheet"]["parts"][0]["not_applied"] and llm.MODEL_NOW.get() == ""
    box.end(b, "x")


def test_final_check_holds_figures_to_the_facts(box):
    b = box.begin("c5", "t", "What is the price of the blue shirt?")
    box.saw("shop_search", {"items": [{"name": "blue shirt", "price": 1499}]})
    assert box.end(b, "The blue shirt costs Rs 1,499.")["ok"]
    b = box.begin("c5", "t", "What is the price of the blue shirt?")
    box.saw("shop_search", {"items": [{"name": "blue shirt", "price": 1499}]})
    chk = box.end(b, "The blue shirt costs Rs 2,350.")
    assert not chk["ok"] and "2350" in chk["problems"][0]
    from app.pipeline import sheet as S
    sh = S.get(b["sheet"]["id"])
    assert sh["check"]["ok"] is False and sh["parts"][0]["out"]["facts"]


def test_check_files_and_not_done():
    from app.pipeline import check as K
    assert "does not exist" in K.final_check("done", files=["/nope/x.pdf"])["problems"][0]
    r = K.final_check("Here is the report.", not_done=["the GST portal refused the login"])
    assert not r["ok"] and r["problems"][0].startswith("not said")
    assert K.final_check("The GST portal refused the login.", not_done=["the GST portal refused the login"])["ok"]


def test_two_failures_pause_the_model_and_the_backup_takes_over(box):
    from app.agent import llm
    for _ in range(2):
        b = box.begin("c6", "t", "hi")
        assert llm.MODEL_NOW.get() == "openrouter:a/mid1"
        box.end(b, "", failed=True)
    assert box.health()["a/mid1"]["paused"] is True
    b = box.begin("c6", "t", "hi")
    assert llm.MODEL_NOW.get() == "openrouter:b/mid2"
    box.end(b, "Namaste!")


def test_her_model_pick_is_a_pin(box, monkeypatch):
    from app import modelchoice
    from app.agent import llm
    monkeypatch.setattr(modelchoice, "chosen", lambda t: "openrouter:c/mid3")
    b = box.begin("c7", "t", "hi")
    assert llm.MODEL_NOW.get() == "openrouter:c/mid3" and "her own pick" in b["sheet"]["parts"][0]["why"]
    box.end(b, "ok")


def test_sheet_states_restart_and_sweep(box):
    from app.pipeline import sheet as S
    sh = S.new("c8", "t", "x", [{"kind": "chat"}])
    with pytest.raises(ValueError):
        S.set_state(sh, 1, "lost")
    assert S.unfinished("c8")["id"] == sh["id"]
    S.set_state(sh, 1, "done")
    S.finish(sh, {"ok": True})
    assert S.unfinished("c8") is None
    old = S.new("c9", "t", "x", [{"kind": "chat"}], now=time.time() - 40 * 86400)
    assert S.sweep() >= 1 and S.get(old["id"]) is None
    pk = S.package("r", [{"text": "a", "value": 1, "source": "s"}], ["f"], ["n"], ["x"])
    assert set(pk) == {"result", "facts", "files", "notes", "not_done"}


def test_run_turn_runs_on_the_box_model(box, monkeypatch):
    from app.agent import llm, santosh
    from app.pipeline import sheet as S
    seen = {}

    async def fake(conv, text, *a, **k):
        seen["model"] = llm.MODEL_NOW.get()
        return "Namaste!"

    monkeypatch.setattr(santosh, "_run_turn", fake)
    monkeypatch.setenv("CHAT_GRAPH", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    out = asyncio.run(santosh.run_turn("c10", "hi", "t"))
    assert out == "Namaste!" and seen["model"] == "openrouter:a/mid1"
    sh = S.recent(conv="c10")[0]
    assert sh["status"] == "done" and sh["parts"][0]["applied"]


def test_run_turn_gives_the_box_her_words_and_her_account(box, monkeypatch):
    """v0.965: the live chat turn passed her words as the account and the account as her words - every live sheet
    read 'chat' with the account id as the ask. A real reasoning ask through run_turn must land as itself."""
    from app.agent import llm, santosh
    from app.pipeline import sheet as S
    seen = {}

    async def fake(conv, text, *a, **k):
        seen["model"] = llm.MODEL_NOW.get()
        return "Jawab 168 piece."

    monkeypatch.setattr(santosh, "_run_turn", fake)
    monkeypatch.setenv("CHAT_GRAPH", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    ask = "Agar 3 machine 5 din mein 120 piece banati hain to 7 machine 9 din mein kitne?"
    asyncio.run(santosh.run_turn("c12", ask, "tenant_meghana"))
    sh = S.recent(conv="c12")[0]
    assert sh["tenant"] == "tenant_meghana" and sh["ask"].startswith("Agar 3 machine")
    assert sh["parts"][0]["kind"] == "reason" and sh["parts"][0]["level"] == "HIGH"
    assert seen["model"] == "openrouter:a/high1"


def test_no_tables_is_said_once(box, caplog):
    from app.pipeline import store
    (store.root() / "current.json").unlink()
    box._TABLES.update({"mtime": None, "doc": None})
    box.STATS.pop("no_tables_said", None)
    with caplog.at_level("WARNING", logger="santosh.pipeline"):
        assert box.begin("c13", "t", "hi") is None
        assert box.begin("c13", "t", "hi") is None
    assert sum("no tables at" in r.getMessage() for r in caplog.records) == 1


def test_sheets_route(box):
    from fastapi.testclient import TestClient
    from app.main import app
    b = box.begin("c11", "t", "hi")
    box.end(b, "ok")
    j = TestClient(app).get("/api/pipeline/sheets", params={"conv": "c11"}).json()
    assert j["on"] is True and j["sheets"][0]["parts"][0]["kind"] == "chat" and "turns" in j["stats"]


def test_the_box_choice_is_not_switched_to_claude_for_hard_asks():
    src = (pathlib.Path(__file__).parents[1] / "app/agent/santosh.py").read_text()
    assert "_boxed = bool(_tbx.APPLIED.get())" in src
    assert 'state.get("hard") and brain != "claude" and not _boxed' in src
    assert '_long_now and brain != "claude" and not _boxed' in src
