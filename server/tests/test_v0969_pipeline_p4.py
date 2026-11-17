"""v0.968 HOOLA PIPELINE P4 - the hand-over rules carried out on real calls (fake models only, no network): error /
refusal / empty -> backup at the same level, late first word -> backup (chat) or a head-start race (call), the window
outgrown -> a bigger window, at most two changes, a failed check -> one level up once, she asks for better -> one level
up, calls at once per user and per company, and the chat turn's model call wired through it."""
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
    from app.pipeline import store, turnbox as T, box as B, handover as H
    store.root().mkdir(parents=True, exist_ok=True)
    (store.root() / "current.json").write_text(json.dumps(_doc()))
    T._TABLES.update({"mtime": None, "doc": None})
    T._OUT.clear()
    T._DEAD.clear()
    B._STICKY.clear()
    monkeypatch.setitem(H.FIRST_WORD_S, "chat", 0.2)
    monkeypatch.setitem(H.FIRST_WORD_S, "call", 0.2)
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


def M(mid):
    return {"id": mid, "route": "openrouter", "status": "ready"}


def _hand(surface="chat", model="a/mid1", backups=("b/mid2", "c/mid3"), doc=None, sheet=None, n=0):
    from app.pipeline import runner as R
    return R.new_hand(kind="chat", level="MID", surface=surface, model=M(model), backups=[M(b) for b in backups],
                      tenant="t1", doc=doc or _doc(), sheet=sheet, n=n)


def _maker(script, log):
    """A fake model: `script[model] = callable(first) -> awaitable` or an exception / answer."""
    from app.agent import llm

    def make(first):
        mid = llm.MODEL_NOW.get().split(":", 1)[1]
        log.append(mid)
        return script[mid](first)
    return make


def ok(text="Namaste", delay=0.0, stream=False):
    async def run(first):
        if delay:
            await asyncio.sleep(delay)
        if stream:
            first()
        return [{"type": "text", "text": text}], "end_turn", {}
    return lambda first: run(first)


def boom(msg="503 upstream error"):
    async def run(first):
        raise RuntimeError(msg)
    return lambda first: run(first)


# ------------------------------------------------------------------ 5.2: each failure case
@pytest.mark.parametrize("bad,event", [(boom(), "error"), (boom("400 content_filter: refused"), "refusal"),
                                       (ok(text="   "), "empty")])
def test_error_refusal_empty_go_to_the_backup_at_the_same_level(box, bad, event):
    from app.pipeline import runner as R, sheet as S
    sh = S.new("c1", "t1", "x", [{"kind": "chat"}])
    hand = _hand(sheet=sh, n=1)
    log: list = []
    out = asyncio.run(R.call(hand, _maker({"a/mid1": bad, "b/mid2": ok("Backup answer")}, log)))
    assert out[0][0]["text"] == "Backup answer" and log == ["a/mid1", "b/mid2"]
    assert hand["current"]["id"] == "b/mid2" and hand["part"]["level"] == "MID"
    rec = S.get(sh["id"])["parts"][0]
    assert rec["handover"][0]["event"] == event and rec["handover"][0]["to"] == "b/mid2" and rec["ran_on"] == "b/mid2"
    assert box.health().get("a/mid1") is not None            # the failure is in the Box's outage record


def test_a_late_first_word_on_chat_stops_the_call_and_the_backup_starts(box):
    from app.pipeline import runner as R
    log: list = []
    hand = _hand()
    t0 = time.time()
    out = asyncio.run(R.call(hand, _maker({"a/mid1": ok("slow", delay=5, stream=True),
                                          "b/mid2": ok("fast", stream=True)}, log), streaming=True))
    assert out[0][0]["text"] == "fast" and time.time() - t0 < 2
    assert hand["part"]["log"][0]["event"] == "late"


def test_a_first_word_in_time_is_never_cut(box):
    from app.pipeline import runner as R

    async def slow_after_first(first):
        first()
        await asyncio.sleep(0.5)          # longer than the limit, but the first word came at once
        return [{"type": "text", "text": "long answer"}], "end_turn", {}
    log: list = []
    out = asyncio.run(R.call(_hand(), _maker({"a/mid1": slow_after_first}, log), streaming=True))
    assert out[0][0]["text"] == "long answer" and log == ["a/mid1"]


def test_a_call_starts_the_backup_at_the_same_time_and_the_first_answer_wins(box):
    from app.pipeline import runner as R
    log: list = []
    hand = _hand(surface="call")
    t0 = time.time()
    out = asyncio.run(R.call(hand, _maker({"a/mid1": ok("slow", delay=3), "b/mid2": ok("backup first")}, log)))
    assert out[0][0]["text"] == "backup first" and time.time() - t0 < 1.5
    assert set(log) == {"a/mid1", "b/mid2"} and hand["current"]["id"] == "b/mid2"
    assert R.STATS["race_backup_won"] >= 1


def test_on_a_call_the_first_model_still_wins_when_it_answers_first(box):
    from app.pipeline import runner as R
    log: list = []
    hand = _hand(surface="call")
    out = asyncio.run(R.call(hand, _maker({"a/mid1": ok("first done", delay=0.3), "b/mid2": ok("late", delay=2)},
                                         log)))
    assert out[0][0]["text"] == "first done" and hand["current"]["id"] == "a/mid1"


def test_a_part_that_outgrew_the_window_moves_to_a_bigger_window(box):
    from app.pipeline import runner as R
    d = _doc()
    d["models"]["c/mid3"]["ctx"] = 1_000_000
    log: list = []
    hand = _hand(doc=d)
    out = asyncio.run(R.call(hand, _maker({"a/mid1": boom("400 maximum context length is 200000 tokens"),
                                          "c/mid3": ok("big window")}, log)))
    assert out[0][0]["text"] == "big window" and log == ["a/mid1", "c/mid3"]
    assert hand["part"]["log"][0]["action"] == "bigger"


def test_at_most_two_changes_then_it_stops(box):
    from app.pipeline import runner as R
    log: list = []
    hand = _hand(backups=("b/mid2", "c/mid3", "d/mid4"))
    with pytest.raises(RuntimeError):
        asyncio.run(R.call(hand, _maker({m: boom() for m in ("a/mid1", "b/mid2", "c/mid3", "d/mid4")}, log)))
    assert log == ["a/mid1", "b/mid2", "c/mid3"]          # two changes, never a loop


def test_no_backup_left_gives_the_error_back(box):
    from app.pipeline import runner as R
    with pytest.raises(RuntimeError):
        asyncio.run(R.call(_hand(backups=()), _maker({"a/mid1": boom()}, [])))


# ------------------------------------------------------------------ 5.3: a failed check -> one level up, once
def test_a_worker_whose_figures_fail_the_check_runs_once_more_one_level_up(box, monkeypatch):
    from app.agent import llm, team
    from app.pipeline import parts as P, sheet as S, turnbox as T
    runs = []

    async def fake(spec, team_id, mission, fams, tenant, conv, turn_id, settings, shared=None):
        runs.append((llm.MODEL_NOW.get(), spec["task"]))
        T.saw("google_search", {"price": 1499000})
        txt = "Tata Nexon EV: Rs 1499000" if len(runs) > 1 else "Tata Nexon EV: Rs 1777777"
        return {"name": spec["name"], "ok": True, "deliverable": txt}

    monkeypatch.setattr(team, "_run_agent", fake)
    part = {"ask": "Research Tata EV prices", "after": [], "role": "worker", "kind": "research", "language": "en",
            "level": "MID", "model": M("a/mid1"), "backups": [M("b/mid2")], "label": "Research"}
    sh = S.new("c9", "t1", "x", [part, {"ask": "write", "after": [1], "role": "writer", "kind": "chat"}])
    info = {"settings": __import__("app.config").config.get_settings(), "team_id": "box_x", "mission": "",
            "families": set(), "tenant": "t1", "conv": "c9", "turn_id": "", "place": None, "limit_s": 30,
            "doc": _doc()}
    asyncio.run(P._run_worker(sh, sh["parts"][0], [], info, []))
    p = S.get(sh["id"])["parts"][0]
    assert len(runs) == 2 and runs[1][0] == "openrouter:a/high1" and "1777777" in runs[1][1]
    assert p["handover"][0]["event"] == "failed_check" and p["level_used"] == "HIGH" and p["check"]["ok"]
    assert p["state"] == "done" and not p["out"]["not_done"]


def test_a_worker_that_fails_the_check_twice_is_delivered_with_the_problem_said(box, monkeypatch):
    from app.agent import team
    from app.pipeline import parts as P, sheet as S, turnbox as T

    async def fake(spec, *a, **k):
        T.saw("google_search", {"price": 1499000})
        return {"name": spec["name"], "ok": True, "deliverable": "Tata Rs 1888888"}

    monkeypatch.setattr(team, "_run_agent", fake)
    part = {"ask": "Research Tata EV prices", "after": [], "role": "worker", "kind": "research", "language": "en",
            "level": "MID", "model": M("a/mid1"), "backups": [], "label": "Research"}
    sh = S.new("c10", "t1", "x", [part, {"ask": "w", "after": [1], "role": "writer", "kind": "chat"}])
    info = {"settings": __import__("app.config").config.get_settings(), "team_id": "b", "mission": "",
            "families": set(), "tenant": "t1", "conv": "c10", "turn_id": "", "place": None, "limit_s": 30,
            "doc": _doc()}
    asyncio.run(P._run_worker(sh, sh["parts"][0], [], info, []))
    p = S.get(sh["id"])["parts"][0]
    assert any("not confirmed" in x for x in p["out"]["not_done"])


def test_the_reply_fix_round_posts_a_correction_or_nothing_on_a_false_alarm(box, monkeypatch):
    from app.agent import llm, santosh
    from app.events import bus
    from app.pipeline import sheet as S
    posted, saved = [], []
    monkeypatch.setattr(bus, "publish", lambda conv, kind, p: posted.append((kind, p)))
    monkeypatch.setattr(santosh, "_save", lambda *a, **k: saved.append(a))
    answers = {"v": "OK"}
    seen = {}

    async def fake(brain, system, tools, msgs, cap):
        seen["model"] = llm.MODEL_NOW.get()
        return [{"type": "text", "text": answers["v"]}], "end_turn", {}

    monkeypatch.setattr(llm, "_openai_create", fake)
    b = box.begin("c11", "t1", "Blue shirt ka daam batao")
    box.saw("shop_search", {"items": [{"price": 1499}]})
    chk = box.end(b, "The blue shirt costs Rs 2,350.")
    assert not chk["ok"]
    assert asyncio.run(box.fix_round(b, "The blue shirt costs Rs 2,350.", chk)) == ""
    assert not posted and seen["model"].startswith("openrouter:a/high")      # one level up from MID
    answers["v"] = "Sudhaar: blue shirt ka daam Rs 1,499 hai."
    out = asyncio.run(box.fix_round(b, "The blue shirt costs Rs 2,350.", chk))
    assert "1,499" in out and posted[-1][1]["source"] == "box_fix" and saved
    assert S.get(b["sheet"]["id"])["check"]["fix"] == "correction posted"


def test_she_asked_for_better_moves_one_level_up(box):
    b = box.begin("c12", "t1", "Blue shirt ka daam batao")
    base = b["sheet"]["parts"][0]["level"]
    box.end(b, "ok")
    b = box.begin("c12", "t1", "better answer please")
    p = b["sheet"]["parts"][0]
    box.end(b, "ok")
    from app.pipeline.levels import up_one
    assert base == "MID" and p["kind"] == "chat" and p["level"] == up_one(base)
    assert any("last message again" in w for w in p["level_why"])


# ------------------------------------------------------------------ 6.8: calls at once
def test_calls_wait_their_turn_per_company(box, monkeypatch):
    from app.pipeline import limits as LM
    monkeypatch.setenv("PIPELINE_COMPANY_CAP", "1")
    from app.config import get_settings
    get_settings.cache_clear()
    order = []

    async def one(i):
        async with LM.slot(f"t{i}", "a/x"):
            order.append(("in", i))
            await asyncio.sleep(0.1)
            order.append(("out", i))

    async def main():
        await asyncio.gather(one(1), one(2))
    asyncio.run(main())
    assert order == [("in", 1), ("out", 1), ("in", 2), ("out", 2)]


def test_other_companies_do_not_wait(box, monkeypatch):
    from app.pipeline import limits as LM
    monkeypatch.setenv("PIPELINE_COMPANY_CAP", "1")
    from app.config import get_settings
    get_settings.cache_clear()
    order = []

    async def one(i, model):
        async with LM.slot("t1", model):
            order.append(("in", i))
            await asyncio.sleep(0.1)
            order.append(("out", i))

    async def main():
        await asyncio.gather(one(1, "a/x"), one(2, "b/y"))
    asyncio.run(main())
    assert order[:2] == [("in", 1), ("in", 2)]


# ------------------------------------------------------------------ wiring
def test_the_box_failure_never_pauses_the_whole_openrouter_brain(box):
    from app.agent import llm
    from app.pipeline import runner as R
    before = dict(llm.BREAKERS["glm"])
    asyncio.run(R.call(_hand(), _maker({"a/mid1": boom(), "b/mid2": ok()}, [])))
    assert llm.BREAKERS["glm"]["fails"] == before["fails"] and not llm.brain_paused("glm")


def test_the_chat_turns_model_call_goes_through_the_runner(box, monkeypatch):
    from app.agent import llm, santosh
    from app.pipeline import runner as R
    calls = []

    async def fake(brain, system, tools, msgs, cap):
        m = llm.MODEL_NOW.get()
        calls.append(m)
        if m.endswith("a/mid1"):
            raise RuntimeError("502 bad gateway")
        return [{"type": "text", "text": "from the backup"}], "end_turn", {"prompt_tokens": 1, "completion_tokens": 1}

    monkeypatch.setattr(llm, "_openai_create", fake)
    hand = _hand()
    tok = R.HAND.set(hand)
    try:
        settings = __import__("app.config").config.get_settings()
        blocks, stop = asyncio.run(santosh._call_brain_once("glm", "sys", [{"role": "user", "content": "hi"}],
                                                            settings, tools=[]))
    finally:
        R.HAND.reset(tok)
    assert blocks[0]["text"] == "from the backup" and calls == ["openrouter:a/mid1", "openrouter:b/mid2"]


def test_a_one_part_turn_carries_its_hand_and_lets_go_after(box):
    from app.pipeline import runner as R
    b = box.begin("c14", "t1", "hi")
    h = R.HAND.get()
    assert h is not None and h["current"]["id"] == "a/mid1" and [x["id"] for x in h["backups"]]
    box.end(b, "ok")
    assert R.HAND.get() is None


def test_calls_stay_off_the_box_unless_switched_on(box, monkeypatch):
    b = box.begin("c15", "t1", "hi", voice=True)
    assert "live call" in b["sheet"]["parts"][0]["not_applied"]
    box.end(b, "x")
    monkeypatch.setenv("PIPELINE_CALLS", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    b = box.begin("c16", "t1", "hi", voice=True)
    assert b["sheet"]["parts"][0]["applied"] and b["sheet"]["surface"] == "call"
    from app.pipeline import runner as R
    assert R.HAND.get()["part"]["surface"] == "call"
    box.end(b, "x")
