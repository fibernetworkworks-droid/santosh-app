"""v0.967 HOOLA PIPELINE P3 - several parts in one message: the plan (code + the LOW planner, checked), parts side by
side, a part waiting for another's result, her tap pausing only its branch, restart, the time limit, the writer and
the final check over every part. Fake models only - no network."""
from __future__ import annotations

import asyncio
import copy
import importlib.util
import json
import pathlib
import time
import types

import pytest

_spec = importlib.util.spec_from_file_location(
    "_p1", pathlib.Path(__file__).with_name("test_v0961_pipeline_choose.py"))
_p1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_p1)

EV = "Research the top 5 EV makers in India, compare prices in a table, and make a Hindi PDF report."
PLAN5 = {"parts": [{"ask": f"Research {c} EV prices in India", "after": []}
                   for c in ("Tata", "Mahindra", "MG", "BYD", "Hyundai")]
         + [{"ask": "Make a price comparison table of the five EV makers", "after": [1, 2, 3, 4, 5]},
            {"ask": "Write a Hindi PDF report on the five EV makers with the table", "after": [6]}]}
PRICE = {"Tata": 1499000, "Mahindra": 1890000, "MG": 1398000, "BYD": 2499000, "Hyundai": 2399000}


def _doc():
    d = _p1.doc()
    d["tables"]["plan"] = {"same_as": "reason"}
    d["tables"]["write"] = copy.deepcopy(d["tables"]["chat"])
    d["tables"]["extract"] = copy.deepcopy(d["tables"]["chat"])
    return d


@pytest.fixture
def box(env, tmp_path, monkeypatch):
    monkeypatch.setenv("PIPELINE_DIR", str(tmp_path / "pl"))
    monkeypatch.setenv("PIPELINE_ON", "true")
    monkeypatch.setenv("CHAT_GRAPH", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.pipeline import store, turnbox as T, box as B, parts as P
    store.root().mkdir(parents=True, exist_ok=True)
    (store.root() / "current.json").write_text(json.dumps(_doc()))
    T._TABLES.update({"mtime": None, "doc": None})
    T._OUT.clear()
    T._DEAD.clear()
    B._STICKY.clear()
    from app.agent import llm, providers
    monkeypatch.setattr(llm, "cheap_brain", lambda: "glm")
    monkeypatch.setattr(providers, "ready", lambda m: True)
    tok = llm.MODEL_NOW.set("")
    yield T
    llm.MODEL_NOW.reset(tok)
    from app.pipeline import runner as R
    T.APPLIED.set(False)        # a test that simulates a crash never closes its turn: nothing leaks into the next one
    T.CURRENT.set(None)
    R.HAND.set(None)
    R.TURN_SWAP.set(None)
    T._DEAD.clear()
    get_settings.cache_clear()


def _planner(monkeypatch, answer):
    from app.agent import llm
    seen = {}

    async def fake(brain, system, tools, msgs, max_tokens):
        seen["model"] = llm.MODEL_NOW.get()
        if isinstance(answer, Exception):
            raise answer
        return [{"type": "text", "text": answer if isinstance(answer, str) else json.dumps(answer)}], "end_turn", {}

    monkeypatch.setattr(llm, "_openai_create", fake)
    return seen


def _agents(monkeypatch, delay=0.2, cards=(), fail=()):
    """A fake sub-agent runner: notes its model + clock, returns a 'tool result' with a price."""
    from app.agent import llm, team
    from app.pipeline import turnbox as T
    log: list[dict] = []

    async def fake(spec, team_id, mission, fams, tenant, conv, turn_id, settings, shared=None):
        rec = {"name": spec["name"], "task": spec["task"], "model": llm.MODEL_NOW.get(), "start": time.time()}
        log.append(rec)
        await asyncio.sleep(delay)
        co = next((c for c in PRICE if c in spec["task"].split("\n")[0]), "")
        if co:
            T.saw("google_search", {"items": [{"maker": co, "price": PRICE[co]}]})
        if any(c in spec["task"].split("\n")[0] for c in cards):
            T.saw("email_draft", {"draft_id": "d_" + co, "status": "pending_approval", "subject": "Quote"})
        rec["end"] = time.time()
        if any(f in spec["task"].split("\n")[0] for f in fail):
            return {"name": spec["name"], "ok": False, "deliverable": "the site refused"}
        return {"name": spec["name"], "ok": True,
                "deliverable": f"{co or 'Table'}: Rs {PRICE.get(co, 0)}" if co else "| maker | price |"}

    monkeypatch.setattr(team, "_run_agent", fake)
    return log


def _writer(monkeypatch, answer="Report taiyaar."):
    """santosh._run_turn replaced by: the real parts hook, then the writer's answer (as the real turn would)."""
    from app.agent import llm, santosh
    from app.pipeline import parts as P
    seen = {}

    async def fake(conv, text, tenant=None, *a, **k):
        ctx = types.SimpleNamespace(admit=types.SimpleNamespace(families={"core"}), place=None)
        seen["block"] = await P.run_for_turn(conv, ctx, __import__("app.config").config.get_settings(), tenant,
                                             "turn_t")
        seen["model"] = llm.MODEL_NOW.get()
        return answer(seen) if callable(answer) else answer

    monkeypatch.setattr(santosh, "_run_turn", fake)
    return seen


# ------------------------------------------------------------------ the plan
def test_code_plan_splits_her_words_and_gathering_parts_run_side_by_side():
    from app.pipeline import parts as P
    plan = P.code_plan("Research Tata EV prices; research MG EV prices; then write a Hindi report")
    assert [p["ask"] for p in plan] == ["Research Tata EV prices", "research MG EV prices", "write a Hindi report"]
    assert plan[0]["after"] == [] and plan[1]["after"] == [] and plan[2]["after"] == [1, 2]
    assert P.code_plan("Find prices, and then make a table; then a PDF")[1] == {"ask": "make a table", "after": [1]}
    assert len(P.split("; ".join(f"research thing {i}" for i in range(10)))) == P.MAX_PARTS


def test_a_plan_code_cannot_read_is_thrown_away():
    from app.pipeline import parts as P
    ok = P.check_plan(PLAN5)
    assert ok and len(ok) == 7 and ok[-1]["after"] == [1, 2, 3, 4, 5, 6]
    assert P.check_plan({"parts": [{"ask": "a", "after": [2]}, {"ask": "b", "after": []}]}) is None   # a later part
    assert P.check_plan({"parts": [{"ask": "a", "after": [1]}, {"ask": "b"}]}) is None                # itself
    assert P.check_plan({"parts": [{"ask": "only one"}]}) is None
    assert P.check_plan({"parts": [{"ask": f"x{i}"} for i in range(9)]}) is None
    assert P.check_plan("not json") is None and P.check_plan({"parts": [{"ask": ""}, {"ask": "b"}]}) is None


def test_the_planner_runs_on_the_low_plan_model_and_falls_back_to_code(box, monkeypatch):
    from app.pipeline import parts as P
    seen = _planner(monkeypatch, "Here you go: " + json.dumps(PLAN5))
    plan, mid = asyncio.run(P.model_plan(EV, _doc()))
    assert len(plan) == 7 and mid == "a/low1" and seen["model"] == "openrouter:a/low1"
    _planner(monkeypatch, "sorry, no idea")
    assert asyncio.run(P.model_plan(EV, _doc()))[0] is None
    _planner(monkeypatch, TimeoutError("slow"))
    assert asyncio.run(P.model_plan(EV, _doc()))[0] is None


# ------------------------------------------------------------------ the worked example (plan section 11)
def test_the_ev_example_runs_end_to_end(box, monkeypatch):
    from app.agent import santosh
    from app.pipeline import sheet as S
    _planner(monkeypatch, PLAN5)
    log = _agents(monkeypatch, delay=0.3)
    seen = _writer(monkeypatch, lambda s: "Tata Rs 14,99,000 se BYD Rs 24,99,000 tak - PDF report taiyaar.")
    t0 = time.time()
    out = asyncio.run(santosh.run_turn("ev1", EV, "t1"))
    took = time.time() - t0
    assert "PDF report" in out
    sh = S.recent(conv="ev1")[0]
    assert sh["multi"] and sh["plan_by"] == "planner" and len(sh["parts"]) == 7 and sh["status"] == "done"
    assert all(p["state"] == "done" for p in sh["parts"])
    research = [r for r in log if r["name"].startswith("Research")]
    table = next(r for r in log if r["name"].startswith("Table"))
    assert len(research) == 5
    assert max(r["start"] for r in research) < min(r["end"] for r in research)       # side by side
    assert table["start"] >= max(r["end"] for r in research) - 0.01                  # waited for all five
    assert took < 0.3 * 5                                                             # not one after another
    assert "Rs 1499000" in table["task"]                                              # got the packages
    assert all(r["model"].startswith("openrouter:") for r in log)
    assert sh["parts"][5]["kind"] == "extract" and sh["parts"][6]["kind"] == "write.lang"
    assert sh["parts"][6]["language"] == "hi" and seen["model"] == "openrouter:a/wl-h"
    assert "Part 1 - Research" in seen["block"] and "Your part: Write a Hindi PDF report" in seen["block"]
    assert sh["check"]["ok"] and "figures" in sh["check"]["checked"]


def test_an_invented_figure_and_an_unsaid_failure_are_caught(box, monkeypatch):
    from app.agent import santosh
    from app.pipeline import sheet as S
    _planner(monkeypatch, PLAN5)
    _agents(monkeypatch, delay=0.01, fail=("BYD",))
    _writer(monkeypatch, "Tata Rs 14,99,000, Kia Rs 31,00,000. Report ready.")
    asyncio.run(santosh.run_turn("ev2", EV, "t1"))
    sh = S.recent(conv="ev2")[0]
    probs = " ".join(sh["check"]["problems"])
    assert sh["parts"][3]["state"] == "failed" and "3100000" in probs and "not said" in probs


# ------------------------------------------------------------------ her tap pauses only its branch (6.9)
def test_a_card_pauses_only_its_branch_and_her_yes_carries_it_on(box, monkeypatch):
    from app.agent import santosh
    from app.pipeline import parts as P, sheet as S
    plan = {"parts": [{"ask": "Research Tata EV prices and email the dealer for a quote", "after": []},
                      {"ask": "Research MG EV prices", "after": []},
                      {"ask": "Compare the Tata quote in a table", "after": [1]},
                      {"ask": "Write the reply", "after": [1, 2, 3]}]}
    _planner(monkeypatch, plan)
    log = _agents(monkeypatch, delay=0.01, cards=("Tata",))
    answer = {"v": "waiting"}
    monkeypatch.setattr(P, "card_answer", lambda c: answer["v"])
    seen = _writer(monkeypatch, "MG done; the Tata quote waits for your Send tap.")
    asyncio.run(santosh.run_turn("tap1", "x; y; z", "t1"))
    sh = S.recent(conv="tap1")[0]
    st = [p["state"] for p in sh["parts"]]
    assert st == ["waiting_tap", "done", "waiting_tap", "done"] and sh["status"] == "waiting_tap"
    assert sh["parts"][2]["blocked_by"] == 1 and "WAITING FOR HER TAP" in seen["block"]
    assert [r["name"] for r in log] == ["Research 1", "Research 2"]                   # the table did not run yet
    turns = []

    async def fake_turn(conv, text, tenant_id=None, actor="owner", context="", **k):
        turns.append((actor, text, context, P.CONTINUING.get()))
        return "ok"

    monkeypatch.setattr(santosh, "run_turn", fake_turn)
    assert asyncio.run(P.continue_sheet(S.get(sh["id"]))) == "still waiting"
    answer["v"] = "yes"
    assert asyncio.run(P.continue_sheet(S.get(sh["id"]))) == "continued"
    sh = S.get(sh["id"])
    assert [p["state"] for p in sh["parts"]] == ["done", "done", "done", "done"] and sh["status"] == "done"
    assert log[-1]["name"].startswith(sh["parts"][2]["label"]) and "Rs 1499000" in log[-1]["task"]
    assert turns and turns[0][0] == "approved:card" and turns[0][1].startswith("[Card answered by her tap]")
    assert turns[0][3] is True and "Part 3" in turns[0][2]


def test_not_now_ends_only_that_branch(box, monkeypatch):
    from app.agent import santosh
    from app.pipeline import parts as P, sheet as S
    plan = {"parts": [{"ask": "Research Tata EV prices and email the dealer", "after": []},
                      {"ask": "Table of the Tata quote", "after": [1]}, {"ask": "Write the reply", "after": [1, 2]}]}
    _planner(monkeypatch, plan)
    _agents(monkeypatch, delay=0.01, cards=("Tata",))
    monkeypatch.setattr(P, "card_answer", lambda c: "no")
    _writer(monkeypatch, "waits for your tap")
    monkeypatch.setattr(P, "card_answer", lambda c: "waiting")
    asyncio.run(santosh.run_turn("tap2", "x; y", "t1"))
    sh = S.recent(conv="tap2")[0]
    called = []

    async def fake_turn(*a, **k):
        called.append(1)

    monkeypatch.setattr(santosh, "run_turn", fake_turn)
    monkeypatch.setattr(P, "card_answer", lambda c: "no")
    assert asyncio.run(P.continue_sheet(S.get(sh["id"]))) == "answered"
    sh = S.get(sh["id"])
    assert [p["state"] for p in sh["parts"]] == ["failed", "failed", "done"] and not called
    assert "Not now" in sh["parts"][0]["out"]["not_done"][0] and sh["status"] == "failed"


def test_cards_are_read_from_the_raw_tool_results():
    from app.pipeline import parts as P
    cards = P.cards_in([("email_draft", {"draft_id": "d1", "status": "pending_approval", "subject": "Q"}),
                        ("google_search", {"items": []})])
    assert cards == [{"kind": "email", "id": "d1", "title": "Email: Q"}]


# ------------------------------------------------------------------ restart, time, stop
def test_a_restart_keeps_the_parts_already_done(box, monkeypatch):
    from app.agent import santosh
    from app.pipeline import sheet as S, turnbox as T
    _planner(monkeypatch, PLAN5)
    b = T.begin("rs1", "t1", EV)                     # the first run: planned, then the process died mid-way
    assert b["multi"]
    sh = b["sheet"]
    import app.pipeline.parts as P
    T.replan(b, P.check_plan(PLAN5))
    for n in (1, 2):
        S.set_state(sh, n, "done", out=S.package(result=f"done {n}"))
    S.set_state(sh, 3, "running")
    T.CURRENT.set(None)
    log = _agents(monkeypatch, delay=0.01)
    _writer(monkeypatch, "ok")
    asyncio.run(santosh.run_turn("rs1", EV, "t1"))
    names = [r["name"] for r in log]
    assert "Research 1" not in names and "Research 2" not in names and "Research 3" in names
    sh2 = S.get(sh["id"])
    assert sh2["status"] == "done" and P.STATS["reused"] >= 1


def test_a_part_over_the_time_limit_is_cut_and_said(box, monkeypatch):
    from app.agent import santosh
    from app.pipeline import sheet as S
    monkeypatch.setenv("PIPELINE_PARTS_S", "1")
    from app.config import get_settings
    get_settings.cache_clear()
    _planner(monkeypatch, {"parts": [{"ask": "Research Tata EV prices", "after": []},
                                     {"ask": "Write the reply", "after": [1]}]})
    _agents(monkeypatch, delay=3)
    seen = _writer(monkeypatch, "Tata ran out of time, sorry.")
    t0 = time.time()
    asyncio.run(santosh.run_turn("tm1", "x; y", "t1"))
    assert time.time() - t0 < 2.5
    sh = S.recent(conv="tm1")[0]
    assert sh["parts"][0]["state"] == "failed" and sh["parts"][0]["cut"] and "ran out of time" in seen["block"]


def test_one_part_messages_are_unchanged(box, monkeypatch):
    from app.pipeline import sheet as S
    b = box.begin("one", "t", "Agar 3 machine 5 din mein 120 piece banati hain to 7 machine 9 din mein kitne?")
    assert not b.get("multi") and len(b["sheet"]["parts"]) == 1
    box.end(b, "168")
    assert S.recent(conv="one")[0]["status"] == "done"


def test_a_call_is_not_planned(box):
    b = box.begin("call", "t", "Research Tata prices; then write a report", voice=True)
    assert not b.get("multi") and "live call" in b["sheet"]["parts"][0]["not_applied"]
    box.end(b, "x")


def test_wiring():
    root = pathlib.Path(__file__).parents[1] / "app"
    src = (root / "agent/santosh.py").read_text()
    i = src.index("_plparts.run_for_turn(conversation_id, ctx, settings, tenant_id, _turn_id)")
    assert src.rindex("_stopped.discard(conversation_id)", 0, i) > src.index("STOPPED_IN_PREP", 0, i)
    assert "pipeline_branch_jobs" in (root / "worker.py").read_text()
    from app.config import Settings
    assert Settings().pipeline_parts_s == 300 and Settings().pipeline_tap_wait_h == 24
