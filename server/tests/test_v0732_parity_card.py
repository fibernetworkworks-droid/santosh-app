"""v0.732 CLAUDE PARITY Phase 0 (docs/CLAUDE_PARITY_PLAN.md Part 3): the Claude Parity Card (60 multi-turn
conversations as data, a scorer in code calibrated on planted transcripts, a live runner that records the brain of
every step) + the request dump (exactly what the model received, per turn, masked, capped, tenant-fenced)."""
import asyncio

import pytest
from fastapi.testclient import TestClient

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import FakeBrain, _set_brain, gz, tu, txt  # noqa: F401


@pytest.fixture(autouse=True)
def _no_plan_gate(monkeypatch):
    from app.agent import research_plan

    async def _off(*a, **k):
        return None
    monkeypatch.setattr(research_plan, "gate", _off)


# ---------------------------------------------------------------- the set

def test_sixty_conversations_in_the_plan_categories():
    from app.quality import paritycard as PC
    from app.quality.parity_convs import CATEGORIES, CONVS
    assert len(CONVS) == 60
    assert CATEGORIES == {"followup": 15, "one_tool": 10, "long": 10, "make": 10, "memory": 5, "trap": 5, "lang": 5}
    for cat, n in CATEGORIES.items():
        assert sum(1 for c in CONVS if c["cat"] == cat) == n
    assert PC.check_set() == []
    assert len({c["id"] for c in CONVS}) == 60
    # the make set is "make + two edits"; follow-ups really follow
    assert all(len(c["turns"]) == 3 for c in CONVS if c["cat"] == "make")
    assert all(len(c["turns"]) >= 2 for c in CONVS if c["cat"] == "followup")
    assert all(c.get("setup") for c in CONVS if c["cat"] == "memory")
    # English user text except the Hinglish / Marathi set
    import re
    for c in CONVS:
        if c["cat"] != "lang":
            assert not any(re.search(r"[ऀ-ॿ]", t["text"]) for t in c["turns"]), c["id"]


def test_check_set_catches_bad_data():
    from app.quality import paritycard as PC
    bad = [{"id": "x", "cat": "followup", "turns": [{"text": "hi", "tool": "nope", "refers_prev": True, "zzz": 1}]},
           {"id": "x", "cat": "memory", "turns": [{"text": "q"}]}]
    lines = "\n".join(PC.check_set(bad))
    for want in ("unknown tool family nope", "unknown expectation", "needs a follow-up turn", "follow-up check on the first",
                 "duplicate id", "needs an earlier chat"):
        assert want in lines, want


# ---------------------------------------------------------------- the scorer

def test_scorer_is_calibrated_on_planted_transcripts():
    from app.quality import paritycard as PC
    cal = PC.calibration()
    misses = [(c["case"], c["failed"], c["must_fail"]) for c in cal if not c["ok"]]
    assert not misses, misses
    honest = [c for c in cal if not c["must_fail"]]
    planted = [c for c in cal if c["must_fail"]]
    assert len(honest) >= 6 and len(planted) >= 10
    # every scored dimension has at least one planted fault that it catches
    caught = {d for c in planted for d in c["must_fail"].split("+")}
    assert caught >= set(PC.DIMS)


def test_conversation_score_and_card_summary():
    from app.quality import paritycard as PC
    conv = next(c for c in PC.CONVS if c["id"] == "fu_second_name")
    good = PC._tr({"reply": "1. Crumb & Co\n2. Golden Oven\n3. Pune Bake House"},
                  {"reply": "Golden Oven - warm from our oven to you."})
    bad = PC._tr({"reply": "1. Crumb & Co\n2. Golden Oven\n3. Pune Bake House"},
                 {"reply": "Crumb & Co - every crumb counts.", "brains": ["glm:x", "claude-haiku-5-5"]})
    g, b = PC.score_conv(conv, good), PC.score_conv(conv, bad)
    assert g["pass"] and g["points"] == 1.0 and g["brains"] == ["glm:z-ai/glm-5.3-flash"]
    assert not b["pass"] and b["dims"]["followed"] is False and b["dims"]["one_brain"] is False
    card = PC.summarize([g, b])
    assert card["passed"] == 1 and card["mixed_brain_convs"] == 1 and card["dims"]["followed"] == {"pass": 1, "of": 2}
    assert "SCORE" in PC.lines(card)[0]


def test_free_check_mode_cli(env, capsys):
    from app.quality import __main__ as Q
    assert Q.main(["parity", "--check"]) == 0
    out = capsys.readouterr().out
    assert "60 conversations" in out and "calibrated 20/20" in out and "set OK" in out
    from app.quality import paritycard as PC
    saved = PC.saved()
    assert saved and saved[0]["kind"] == "check"
    assert Q.main(["parity", "--check", "--only", "nope"]) == 2


# ---------------------------------------------------------------- the live runner (scripted brain)

def test_live_runner_records_tools_and_the_brain_of_every_step(gz, monkeypatch):  # noqa: F811
    from app.quality import paritycard as PC
    conv = {"id": "t_rem", "cat": "one_tool", "turns": [{"text": "Remind me in 30 minutes to call the CA.",
                                                         "tool": "reminder", "must": [["ca", "call"]]}]}
    _set_brain(monkeypatch, FakeBrain([
        ([tu(1, "create_reminder", text="call the CA", in_minutes=30)], "tool_use"),
        ([txt("The reminder to call the CA rings in 30 minutes.")], "end_turn"),
    ]))
    row = asyncio.run(PC.run_conv(conv, tenant="default"))
    t = row["transcript"][0]
    assert [c["tool"] for c in t["tools"]][0] == "create_reminder"
    assert len(t["steps"]) == 2 and all(s["ok"] for s in t["steps"])
    assert all(s["answered"] for s in t["steps"]) and row["brains"]
    assert row["dims"]["right_tool"] is True and row["dims"]["answered"] is True
    assert row["dims"]["one_brain"] is True
    # the funnel is restored after the card
    from app.agent import santosh
    assert santosh._call_brain.__name__ == "_call_brain" and santosh._run_tool.__name__ == "_run_tool"


# ---------------------------------------------------------------- the request dump

def _run(conv, text, script, monkeypatch):
    _set_brain(monkeypatch, FakeBrain(script))
    from app import reqdump
    from app.agent.santosh import run_turn

    async def go():
        out = await run_turn(conv, text, tenant_id="default")
        await reqdump.drain()
        return out
    return asyncio.run(go())


def test_request_dump_records_and_serves_a_turn(gz, monkeypatch):  # noqa: F811
    from app import reqdump
    conv = gz["conv"]
    _run(conv, "my card is 4111 1111 1111 1111 and api_key=sk-ant-abcdefghijklmnopqrstuvwxyz0123",
         [([tu(1, "kaam_status", q="x")], "tool_use"), ([txt("Here is your status.")], "end_turn")], monkeypatch)
    turns = reqdump.turns(conv, "default")
    assert len(turns) == 1 and turns[0]["steps"] == 2 and turns[0]["brains"]
    got = reqdump.turn(conv, "default", "1")
    assert got and [s["step"] for s in got["steps"]] == [1, 2]
    s1, s2 = got["steps"]
    assert s1["system"] and s1["tools"] and s1["max_tokens"] > 0 and s1["brain"] and s1["model"]
    assert s1["ok"] is True and s1["sizes"]["system_chars"] > 0
    import json
    body = json.dumps(s1["messages"])
    assert "4111 1111 1111 1111" not in body and "sk-ant-abcdefghijklmnopqrstuvwxyz0123" not in body
    assert "kaam_status" in json.dumps(s2["messages"])      # the second step saw the tool call + its result
    assert reqdump.turn(conv, "default", "-1")["turn"] == 1
    assert reqdump.turn(conv, "default", got["turn_id"])["turn"] == 1 if got["turn_id"] else True
    assert reqdump.turn(conv, "other", "1") is None             # another tenant never reads it


def test_request_dump_cap_switch_and_fail_open(gz, monkeypatch):  # noqa: F811
    from app import reqdump
    from app.config import get_settings
    conv = gz["conv"]
    monkeypatch.setenv("REQUEST_DUMP_TURNS", "2")
    get_settings.cache_clear()
    for i in range(3):
        _run(conv, f"question {i}", [([txt(f"answer {i}")], "end_turn")], monkeypatch)
    nums = [t["turn"] for t in reqdump.turns(conv, "default")]
    assert nums == [2, 3]
    # switch off: nothing new written
    monkeypatch.setenv("REQUEST_DUMP", "false")
    get_settings.cache_clear()
    _run(conv, "question 4", [([txt("answer 4")], "end_turn")], monkeypatch)
    assert [t["turn"] for t in reqdump.turns(conv, "default")] == [2, 3]
    # a broken dump never breaks the turn
    monkeypatch.setenv("REQUEST_DUMP", "true")
    get_settings.cache_clear()

    def boom(*a, **k):
        raise RuntimeError("disk full")
    monkeypatch.setattr(reqdump, "shape", boom)
    out = _run(conv, "question 5", [([txt("answer 5")], "end_turn")], monkeypatch)
    assert "answer 5" in out


def test_request_endpoints_need_the_key_and_the_tenant(gz, monkeypatch):  # noqa: F811
    conv = gz["conv"]
    _run(conv, "hello", [([txt("hi there")], "end_turn")], monkeypatch)
    monkeypatch.setenv("API_KEY", "k-test-123")
    from app.config import get_settings
    get_settings.cache_clear()
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    assert c.get(f"/api/conversations/{conv}/request").status_code == 401
    assert c.get(f"/api/conversations/{conv}/request/1").status_code == 401
    h = {"Authorization": "Bearer k-test-123"}
    r = c.get(f"/api/conversations/{conv}/request", headers=h)
    assert r.status_code == 200 and r.json()["turns"][0]["turn"] == 1
    r = c.get(f"/api/conversations/{conv}/request/1", headers=h)
    assert r.status_code == 200 and r.json()["steps"][0]["system"]
    assert c.get(f"/api/conversations/{conv}/request/9", headers=h).status_code == 404
    from app.db import Conversation, session
    with session() as s:
        o = Conversation(tenant_id="someone_else")
        s.add(o)
        s.flush()
        other = o.id
    assert c.get(f"/api/conversations/{other}/request/1", headers=h).status_code == 404
    assert c.get("/api/quality/parity").status_code == 401
    q = c.get("/api/quality/parity", headers=h)
    assert q.status_code == 200 and q.json()["check"]["convs"] == 60 and q.json()["check"]["ok"] is True


def test_request_dump_sweep_runs_with_an_older_row_loaded(gz, monkeypatch):  # noqa: F811
    """v0.734: on her server EVERY dump failed with "can't compare offset-naive and offset-aware datetimes" - the
    sweep (first write after a restart) ran with an older row loaded from the DB in the same session."""
    from app import reqdump
    conv = gz["conv"]
    _run(conv, "first", [([txt("one")], "end_turn")], monkeypatch)
    monkeypatch.setitem(reqdump.STATS, "written", 0)          # a restart: the next write runs the sweep
    before = reqdump.STATS["failed"]
    _run(conv, "second", [([txt("two")], "end_turn")], monkeypatch)
    assert reqdump.STATS["failed"] == before
    assert len(reqdump.turns(conv, "default")) == 2
