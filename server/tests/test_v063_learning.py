"""v0.63 Seekhne wala Hoola: learned procedures (Hermes idea), pinned memory, circuit breaker (Munder Difflin idea)."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.agent import run_turn, set_client
from app.db import Conversation, session
from tests.test_bazar import _events


class Model:
    """Scripted stand-in for Claude that also records the system prompt of every call."""

    def __init__(self, script):
        self.script, self.systems, self.sent = list(script), [], []
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kw):
        self.systems.append(kw.get("system") or "")
        self.sent.append(json.loads(json.dumps(kw["messages"], default=str)))
        blocks = self.script.pop(0) if self.script else [{"type": "text", "text": "Ho gaya."}]
        stop = "tool_use" if any(b["type"] == "tool_use" for b in blocks) else "end_turn"
        return SimpleNamespace(content=blocks, stop_reason=stop)


def call(name, args, i):
    return [{"type": "tool_use", "id": f"tu_{name}_{i}", "name": name, "input": args}]


def say(t):
    return [{"type": "text", "text": t}]


def conv():
    with session() as s:
        c = Conversation(tenant_id="default")
        s.add(c)
        s.flush()
        return c.id


def last_results(model):
    msgs = model.sent[-1]
    return [b for b in msgs[-1]["content"] if b.get("type") == "tool_result"]


def run(c):
    return asyncio.run(c)


# ---------------------------------------------------------------- circuit breaker
def test_breaker_rules():
    from app.agent.breaker import Breaker
    b = Breaker()
    assert b.before("list_show", {"list_name": "a"}) is None
    assert b.before("list_show", {"list_name": "a"}) is None
    assert "same kaam" in b.before("list_show", {"list_name": "a"})        # 3rd identical: steered
    assert b.before("list_show", {"list_name": "b"}) is None                # different input is fine
    b.after("list_show", True)
    for i in range(3):
        b.before("email_read", {"id": i})
        b.after("email_read", False)
    b.before("list_show", {"list_name": "c"})
    b.after("list_show", True)                                             # something else worked in between
    assert "fail ho raha" in b.before("email_read", {"id": 9})            # constrained: the failing tool is taken away
    b2 = Breaker()
    for i in range(4):
        b2.before(f"t{i}", {})
        b2.after(f"t{i}", False)
    assert b2.stopped and "Ruko" in b2.before("t9", {})                     # 4 failures in a row: stop
    b3 = Breaker(max_calls=3)
    for i in range(3):
        assert b3.before("x", {"i": i}) is None
    assert b3.before("x", {"i": 99}) and b3.stopped


def test_same_call_is_not_run_a_third_time(env):
    cid = conv()
    m = Model([call("list_show", {"list_name": "kirana"}, 1), call("list_show", {"list_name": "kirana"}, 2),
               call("list_show", {"list_name": "kirana"}, 3), say("List khaali hai.")])
    set_client(m)
    out = run(run_turn(cid, "kirana list dikhao"))
    assert out == "List khaali hai."
    third = last_results(m)[0]
    assert third["is_error"] and "same kaam" in third["content"]


def test_stuck_turn_stops_and_says_so(env):
    cid = conv()
    m = Model([call("forget", {"fact_id": 900 + i}, i) for i in range(6)] + [say("never")])
    set_client(m)
    out = run(run_turn(cid, "purani yaadein mitao"))
    assert "atak gaya" in out
    assert len(m.sent) == 4                       # 4 failed calls, then stopped without asking the model again
    assert any(e.get("phase") == "stopped" for e in _events(cid, "work"))
    from app.agent.breaker import STATS
    assert STATS["stop"] >= 1


# ---------------------------------------------------------------- learned procedures
def _job(cid, words="Har mahine ka kirana list bana ke reminder lagao", n=0):
    script = [call("list_add", {"list_name": "kirana", "items": ["atta", "tel"]}, 1 + n),
              call("list_show", {"list_name": "kirana"}, 2 + n),
              call("create_reminder", {"text": "Kirana lena", "when": "2027-01-10T10:00"}, 3 + n),
              call("list_show", {"list_name": ""}, 4 + n),
              say("Kirana list ban gayi aur 10 Jan ka reminder laga diya.")]
    m = Model(script)
    set_client(m)
    out = run(run_turn(cid, words))
    return m, out


def test_learns_a_procedure_and_uses_it_next_time(env):
    from app import procedures as pr
    cid = conv()
    m, out = _job(cid)
    assert out.startswith("Kirana list")
    rows = pr.listing("default")
    assert len(rows) == 1
    p = rows[0]
    assert p["title"].startswith("Har mahine ka kirana") and [s["tool"] for s in p["steps"]] == ["list_add", "list_show", "create_reminder"]
    assert all("atta" not in json.dumps(s) for s in p["steps"])            # inputs are never stored
    assert _events(cid, "procedure")[0]["title"] == p["title"]
    # the same kind of request again: the procedure is in the prompt, and it is counted as a win
    m2, _ = _job(cid, "Har mahine ka kirana list bana ke reminder lagao, is baar dal bhi", n=10)
    assert "Seekhe hue kaam" in m2.systems[0] and p["title"] in m2.systems[0]
    rows = pr.listing("default")
    assert len(rows) == 1 and rows[0]["uses"] == 1 and rows[0]["wins"] == 1   # updated, not duplicated


def test_small_or_failed_turns_teach_nothing(env):
    from app import procedures as pr
    cid = conv()
    m = Model([call("list_show", {"list_name": "a"}, 1), say("Khaali hai.")])
    set_client(m)
    run(run_turn(cid, "list dikhao"))
    assert pr.listing("default") == []
    m = Model([call("forget", {"fact_id": 900 + i}, i) for i in range(5)])
    set_client(m)
    run(run_turn(cid, "sab bhool jao aur list banao aur reminder lagao"))
    assert pr.listing("default") == []
    # staff / customers never teach the owner's Hoola
    assert pr.after_turn("default", "x y z", [{"tool": "list_add", "ok": True}, {"tool": "list_show", "ok": True}] * 3,
                         [], True, actor="staff:tm_1") is None


def test_procedure_that_keeps_failing_switches_off(env):
    from app import procedures as pr
    calls = [{"tool": "list_add", "ok": True}, {"tool": "list_show", "ok": True},
             {"tool": "create_reminder", "ok": True}, {"tool": "list_show", "ok": True}]
    got = pr.after_turn("default", "Bijli ka bill dekh ke reminder lagao", calls, [], True)
    pid = got["learned"]
    for _ in range(3):
        pr.after_turn("default", "x", [], [pid], False)
    assert pr.listing("default")[0]["active"] is False
    assert pr.hint("default", "Bijli ka bill dekh ke reminder lagao") == ("", [])
    assert pr.update("default", pid, active=True)["active"] is True
    p = pr.update("default", pid, title="Bijli bill + yaad", steps=["Bill dekho", "Reminder lagao"])
    assert p["title"] == "Bijli bill + yaad" and [s["label"] for s in p["steps"]] == ["Bill dekho", "Reminder lagao"]
    pr.after_turn("default", "Bijli ka bill dekh ke reminder lagao", calls, [], True)
    assert [s["label"] for s in pr.listing("default")[0]["steps"]] == ["Bill dekho", "Reminder lagao"]   # her words stay
    with pytest.raises(pr.ProcedureError):
        pr.update("kunal", pid, active=False)                                 # another owner's procedure
    text, ids = pr.hint("default", "bijli ka bill dekh ke reminder lagao please")
    assert ids == [pid] and "Bill dekho -> Reminder lagao" in text


def test_procedure_tool_and_api(env):
    from app import main
    from app import procedures as pr
    from app.agent.tools import Ctx, ToolError, dispatch
    calls = [{"tool": "list_add", "ok": True}, {"tool": "list_show", "ok": True},
             {"tool": "create_reminder", "ok": True}, {"tool": "list_show", "ok": True}]
    pid = pr.after_turn("default", "Doodh wale ka hisaab likho aur yaad dilao", calls, [], True)["learned"]
    ctx = Ctx(tenant_id="default", conversation_id=conv())
    assert run(dispatch("seekhe_kaam", {"action": "list"}, ctx))["total"] == 1
    assert run(dispatch("seekhe_kaam", {"action": "off", "id": pid}, ctx))["on"] is False
    with pytest.raises(ToolError):
        run(dispatch("seekhe_kaam", {"action": "list"}, Ctx(tenant_id="default", conversation_id="", actor="staff:tm_1")))
    with TestClient(main.app) as c:
        assert c.get("/api/procedures").json()["procedures"][0]["id"] == pid
        assert c.patch(f"/api/procedures/{pid}", json={"active": True}).json()["active"]
        assert c.patch(f"/api/procedures/{pid}", json={"title": "  "}).status_code == 400
        assert c.delete(f"/api/procedures/{pid}").json()["ok"]
        assert c.delete(f"/api/procedures/{pid}").status_code == 400
        s = c.get("/api/agent/stats").json()
        assert set(s["breaker"]) == {"steer", "constrain", "stop"} and "learned" in s["procedures"]


# ---------------------------------------------------------------- pinned memory
def test_pinned_memory(env):
    from app import life, main
    from app.agent.tools import Ctx, dispatch
    ctx = Ctx(tenant_id="default", conversation_id=conv())
    r = run(dispatch("remember", {"fact": "Main shakahari hoon, non-veg kabhi suggest mat karna", "pin": True}, ctx))
    assert r["pinned"] is True
    for i in range(45):
        run(dispatch("remember", {"fact": f"Purani baat number {i}"}, ctx))
    block = life.context_block("default")
    assert "ALWAYS keep in mind" in block and "shakahari" in block
    assert "Purani baat number 44" in block and "Purani baat number 0\n" not in block + "\n"
    assert "memory_search" in block                                         # older ones are searched, not listed
    facts = life.memory_facts("default", 500)
    assert facts[0].pinned and facts[0].text.startswith("Main shakahari")
    with TestClient(main.app) as c:
        m = c.get("/api/memory").json()
        assert m["facts"][0]["pinned"] and m["pinned_max"] == 1500 and len(m["facts"]) == 46
        long_id = run(dispatch("remember", {"fact": "x" * 490}, ctx))["fact_id"]
        ids = [run(dispatch("remember", {"fact": "y" * 490}, ctx))["fact_id"] for _ in range(2)]
        assert c.patch(f"/api/memory/{long_id}", json={"pinned": True}).status_code == 200
        assert c.patch(f"/api/memory/{ids[0]}", json={"pinned": True}).status_code == 200
        assert c.patch(f"/api/memory/{ids[1]}", json={"pinned": True}).status_code == 400   # over 1,500 characters
        assert c.patch(f"/api/memory/{long_id}", json={"pinned": False}).json()["pinned_chars"] < 1500
        assert c.patch("/api/memory/999999", json={"pinned": True}).status_code == 400
        assert c.patch(f"/api/memory/{long_id}", json={"pinned": True}).status_code == 200    # ~1,030 used now
    r = run(dispatch("remember", {"fact": "z" * 480, "pin": True}, ctx))
    assert r["saved"] and r["pinned"] is False and "1500" in r["note"]      # saved, just not pinned
