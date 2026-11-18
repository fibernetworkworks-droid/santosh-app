"""v0.859 D0 THE PC CARD: the 40-task set, the code checker, the test-PC guard and a whole run against a fake
operator (no network, no real PC)."""
from __future__ import annotations

import asyncio
import json
import re
from types import SimpleNamespace

import pytest

from app.quality import pccard as PC
from app.quality.pccard_tasks import GROUPS, TASKS


# ---------------------------------------------------------------- the task set

def test_task_set_is_valid():
    assert len(TASKS) == 40
    ids = [t["id"] for t in TASKS]
    assert len(set(ids)) == 40
    for t in TASKS:
        assert t["ask"].strip(), t["id"]
        assert t["group"] in GROUPS, t["id"]
        assert PC.check_known(t["check"]), t["id"]
        assert 1 <= t["max_minutes"] <= 15
    assert {t["group"] for t in TASKS} == set(GROUPS)


def test_shopping_tasks_stop_at_approval():
    shop = [t for t in TASKS if t["group"] == "shopping_to_approval"]
    assert len(shop) >= 4
    for t in shop:
        flat = json.dumps(t["check"])
        assert "needs_confirm" in flat or "asked" in flat, t["id"]
        assert not re.search(r"\bpay kar|place the order|order kar do\b", t["ask"], re.I)


# ---------------------------------------------------------------- the checker

STATE = {"title": "Untitled - Notepad", "windows": ["Calculator", "Downloads - File Explorer"],
         "page": "Akola - Wikipedia\nhttps://en.wikipedia.org/wiki/Akola\nAkola is a city", "answer": "Result is 500",
         "status": "done", "errors": {}}


@pytest.mark.parametrize("chk,ok", [
    ({"kind": "title", "re": "notepad"}, True),
    ({"kind": "title", "re": "excel"}, False),
    ({"kind": "windows", "re": "calculator"}, True),
    ({"kind": "windows", "re": "downloads"}, True),
    ({"kind": "page", "re": "akola"}, True),
    ({"kind": "page", "re": "taj mahal"}, False),
    ({"kind": "answer", "re": r"\b500\b"}, True),
    ({"kind": "status", "in": ["done"]}, True),
    ({"kind": "status", "in": ["needs_confirm"]}, False),
    ({"all": [{"kind": "title", "re": "notepad"}, {"kind": "answer", "re": "500"}]}, True),
    ({"all": [{"kind": "title", "re": "notepad"}, {"kind": "answer", "re": "600"}]}, False),
    ({"any": [{"kind": "status", "in": ["needs_confirm"]}, {"kind": "answer", "re": "500"}]}, True),
])
def test_checker(chk, ok):
    assert PC.check(chk, STATE)[0] is ok


def test_failed_read_fails_the_check():
    st = {**STATE, "errors": {"page": "PC offline"}}
    ok, why = PC.check({"kind": "page", "re": "akola"}, st)
    assert not ok and "PC offline" in why
    assert PC.needs({"all": [{"kind": "title", "re": "x"}, {"kind": "page", "re": "y"}]}) == {"screen", "page"}


# ---------------------------------------------------------------- the guard

def _dev(name):
    return lambda tenant, pc: {"device_id": "dev1", "name": name, "kind": ""}


def test_guard(monkeypatch):
    with pytest.raises(ValueError, match="TEST PC"):
        PC.guard("t", "")
    monkeypatch.setattr(PC, "_resolve", lambda t, p: None)
    with pytest.raises(ValueError, match="No online PC"):
        PC.guard("t", "office")
    monkeypatch.setattr(PC, "_resolve", _dev("Office PC"))
    with pytest.raises(ValueError, match="test"):
        PC.guard("t", "office")
    assert PC.guard("t", "office", confirm_not_her_pc=True)["device_id"] == "dev1"
    monkeypatch.setattr(PC, "_resolve", _dev("Hoola Test PC 1"))
    assert PC.guard("t", "test")["name"] == "Hoola Test PC 1"


def test_run_card_refuses_her_pc(monkeypatch):
    monkeypatch.setattr(PC, "_resolve", _dev("Meghana Laptop"))
    with pytest.raises(ValueError):
        asyncio.run(PC.run_card("t", "laptop", ids=["notepad_line"], save_card=False))
    assert not PC.running()


# ---------------------------------------------------------------- a whole run on a fake operator

class FakeOp:
    def __init__(self, sid, script):
        self.id, self.conv = sid, "__pccard__"
        self.status, self.summary, self.reason = "running", "", ""
        self.step, self.brain, self.brain_model = 0, "sonnet", "claude-sonnet-5-5"
        self.window, self.windows, self.monitor = "", [], "primary"
        self.timeline, self.ask = [], None
        self.done_event = asyncio.Event()
        self.script = script


class FakeOperator:
    """start() finishes each task instantly the way its script says; _pc returns that task's screen / page."""

    def __init__(self, scripts):
        self.scripts, self.OPS, self.stopped, self.answers, self.n = scripts, {}, [], [], 0

    async def start(self, tenant, conv, ask, wait=0, kind="", pc="", replace=True, **k):
        assert pc == "dev1" and replace is False and wait == 0
        self.n += 1
        sid = f"pcop_{self.n}"
        sc = next(s for key, s in self.scripts.items() if key in ask)
        op = FakeOp(sid, sc)
        op.step = sc.get("steps", 3)
        op.timeline = [{"do": d} for d in sc.get("did", [])]
        if sc.get("ask"):
            op.ask = {"id": "q1", "question": "Kaunsa?", "options": ["a"]}
        op.status = sc["status"]
        op.summary = sc.get("summary", "")
        if sc["status"] != "needs_confirm" and not sc.get("ask"):
            op.done_event.set()
        self.OPS[sid] = op
        return {"session_id": sid, "status": op.status}

    async def _pc(self, op, action, args=None, **k):
        if action == "screen":
            return {"active_window": op.script.get("title", ""), "windows": op.script.get("windows", [])}
        if action == "page_text":
            if op.script.get("page_error"):
                raise RuntimeError("no browser")
            return {"title": "", "url": "", "text": op.script.get("page", "")}
        raise AssertionError(action)

    def stop(self, tenant, sid):
        self.stopped.append(sid)
        self.OPS[sid].status = "cancelled"
        return True

    def give_answer(self, tenant, text, conv=""):
        self.answers.append(text)
        return True


def test_run_card_end_to_end(monkeypatch, tmp_path):
    monkeypatch.setenv("QUALITY_DIR", str(tmp_path))
    fake = FakeOperator({
        "HOOLA CARD 7391": {"status": "done", "title": "Untitled - Notepad", "summary": "Typed HOOLA CARD 7391"},
        "125 + 375": {"status": "done", "windows": ["Calculator"], "summary": "Answer 400"},   # wrong = false done
        "Margherita": {"status": "needs_confirm", "summary": "", "did": ["ask_user", "page_click"], "steps": 12},
        "Taj Mahal": {"status": "partial", "page_error": True, "summary": "could not"},
    })
    monkeypatch.setattr(PC, "_op_mod", lambda: fake)
    monkeypatch.setattr(PC, "_resolve", _dev("Hoola Test PC"))
    monkeypatch.setattr(PC, "_online", lambda t, d: True)
    monkeypatch.setattr(PC, "POLL_S", 0.01)
    card = asyncio.run(PC.run_card("t", "test", ids=["notepad_line", "calc_sum", "swiggy_cart_approval",
                                                     "edge_wikipedia"]))
    rows = {r["id"]: r for r in card["rows"]}
    assert rows["notepad_line"]["ok"] and not rows["notepad_line"]["false_done"]
    assert not rows["calc_sum"]["ok"] and rows["calc_sum"]["false_done"]
    sw = rows["swiggy_cart_approval"]
    assert sw["ok"] and sw["stopped_at_approval"] and sw["status"] == "needs_confirm"
    assert sw["asks"] == 1 and sw["steps"] == 12 and sw["brain"] == "sonnet"
    assert rows["edge_wikipedia"]["ok"] is False and "no browser" in rows["edge_wikipedia"]["reason"]
    stopped_ids = {fake.OPS[s].script.get("status") for s in fake.stopped}
    assert "needs_confirm" in stopped_ids                      # the approval stop was stopped: nothing bought
    s = card["summary"]
    assert s["ran"] == 4 and s["ok"] == 2 and s["success_pct"] == 50.0 and s["false_done"] == 1
    assert s["approval_stops"] == 1 and s["groups"]["shopping_to_approval"]["ok"] == 1
    assert card["file"].startswith("pccard-") and (tmp_path / card["file"]).exists()
    assert PC.saved()[0]["summary"]["ok"] == 2 and PC.last()["file"] == card["file"]
    assert not PC.running() and PC.lines(card)[0].startswith("PC card")


def test_run_card_answers_then_counts_asked(monkeypatch, tmp_path):
    monkeypatch.setenv("QUALITY_DIR", str(tmp_path))
    fake = FakeOperator({"biryani": {"status": "running", "ask": True},
                         "Akola weather": {"status": "running", "ask": True}})
    orig = fake.give_answer

    def answer_once(tenant, text, conv=""):       # the fake asks again after every answer
        orig(tenant, text, conv)
        return True
    fake.give_answer = answer_once
    monkeypatch.setattr(PC, "_op_mod", lambda: fake)
    monkeypatch.setattr(PC, "_resolve", _dev("test box"))
    monkeypatch.setattr(PC, "_online", lambda t, d: True)
    monkeypatch.setattr(PC, "POLL_S", 0.01)
    card = asyncio.run(PC.run_card("t", "test", ids=["chrome_google_search", "swiggy_pick_ask"],
                                     save_card=False))
    r, b = card["rows"]
    assert r["status"] == "asked" and not r["ok"] and fake.stopped   # no answer given in the task: stopped, not guessed
    assert b["status"] == "asked" and b["ok"] and b["answered"] == PC.MAX_ANSWERS   # its own answer, at most twice
    assert len(fake.answers) == PC.MAX_ANSWERS


def test_offline_stops_early_and_skip_needs(monkeypatch, tmp_path):
    monkeypatch.setenv("QUALITY_DIR", str(tmp_path))
    monkeypatch.setattr(PC, "_op_mod", lambda: FakeOperator({}))
    monkeypatch.setattr(PC, "_resolve", _dev("test box"))
    monkeypatch.setattr(PC, "_online", lambda t, d: False)
    card = asyncio.run(PC.run_card("t", "test", ids=["excel_sum", "notepad_line"], skip_needs=["office"],
                                   save_card=False))
    assert card["note"] == "the test PC went offline" and card["rows"] == []   # notepad_line first: nothing ran
    card = asyncio.run(PC.run_card("t", "test", ids=["excel_sum"], skip_needs=["office"], save_card=False))
    assert card["rows"][0]["skipped"] and card["summary"]["skipped"] == 1
    assert card["summary"]["ran"] == 0


def test_routes_mounted_and_owner_only(env, monkeypatch, tmp_path):
    from fastapi import HTTPException
    from fastapi.testclient import TestClient

    from app.main import app
    from app.quality import pccard_api
    monkeypatch.setenv("QUALITY_DIR", str(tmp_path))
    c = TestClient(app)
    h = {"X-API-Key": "test-key"}
    over = c.get("/api/quality/pccard", headers=h)
    assert over.status_code == 200 and len(over.json()["tasks"]) == 40 and over.json()["last"] is None
    assert c.post("/api/quality/pccard/run", json={"pc": ""}, headers=h).status_code == 400   # no PC named
    assert c.post("/api/quality/pccard/stop", headers=h).json() == {"stopped": False}
    with pytest.raises(HTTPException):
        pccard_api._owner("someone-else")
