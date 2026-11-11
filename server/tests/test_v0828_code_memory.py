"""HOOLA CODE MEMORY (owner: "https://github.com/thedotmack/claude-mem.git --- check this repo and devlope same for hoola
code"). claude-mem's design for Hoola Code, per repo: an observer at the end of every round (one cheap call) writes typed
observations + a round summary; a new session on the repo starts with a budget-fitted INDEX of them; the coder reads
more through claude-mem's three steps (search -> timeline -> get) and can save a note on purpose; her <private> text
and anything key-like are never kept; her page shows, deletes and forgets them."""
from __future__ import annotations

import json

import pytest

from tests.test_tech_devsahayak import REPO, dev  # noqa: F401
from tests.test_v0787_hoola_code_engine import on, tu  # noqa: F401
from tests.test_v0812_ecc_agents import _round

KEY = "sk-ant-api03-" + "abcdefghijklmnopqrstuvwxyz0123"


@pytest.fixture
def mem(tmp_path, monkeypatch):
    from app.config import get_settings
    from app.devsahayak import memory as M
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(get_settings(), "dev_memory", True, raising=False)
    M._READY.clear()
    return M


def _o(title, typ="bugfix", **k):
    return {"type": typ, "title": title, "subtitle": k.get("sub", ""), "narrative": k.get("nar", "because"),
            "facts": k.get("facts", []), "concepts": k.get("concepts", ["gotcha"]), "files_modified": k.get("files", [])}


# ---------------------------------------------------------------- the store and the three steps
def test_store_search_timeline_get_and_forget(mem):
    M = mem
    a = M.store("t1", "me/shop", "dt_1", _o("Cart total divided by item count - empty carts crashed", files=["app/calc.py"]))
    b = M.store("t1", "me/shop", "dt_1", _o("Tests run with python3 -m pytest -q", "discovery", concepts=["how-it-works", "nonsense"]))
    assert a and b and a != b
    again = M.store("t1", "me/shop", "dt_2", _o("Cart total divided by item count - empty carts crashed!", nar="newer words"))
    assert again == a and M.get("t1", "me/shop", [a])[0]["narrative"] == "newer words"      # same memory, re-confirmed
    assert M.search("t1", "me/shop")[0]["hits"] in (1, 2) and {r["id"] for r in M.search("t1", "me/shop")} == {a, b}
    assert [r["id"] for r in M.search("t1", "me/shop", "empty cart")] == [a]
    assert [r["id"] for r in M.search("t1", "me/shop", "", "discovery")] == [b]
    assert M.get("t1", "me/shop", [b])[0]["concepts"] == ["how-it-works"]                    # only known concepts
    assert any(r.get("anchor") for r in M.timeline("t1", "me/shop", b))
    # walls: another repo, another tenant see nothing
    assert M.search("t1", "me/other") == [] and M.search("t2", "me/shop") == [] and M.get("t2", "me/shop", [a]) == []
    assert M.store("t1", "me/shop", "x", _o("x", "sensitive")) is None                         # never stored
    assert M.store("t1", "me/shop", "x", _o("x", "made_up_type")) is None and M.store("t1", "me/shop", "x", _o("")) is None
    assert M.forget("t2", a) is False and M.forget("t1", a) is True and M.counts("t1", "me/shop")["observations"] == 1
    M.store_summary("t1", "me/shop", "dt_1", {"request": "fix the cart", "completed": "fixed"}, ["app/calc.py"])
    assert M.forget_repo("t1", "me/shop") == {"observations": 1, "summaries": 1}


def test_private_text_and_keys_never_kept(mem):
    M = mem
    oid = M.store("t1", "me/shop", "x", _o("Payment webhook key lives in settings", nar=f"the key is {KEY} <private>my home address</private>"))
    full = M.get("t1", "me/shop", [oid])[0]
    assert KEY not in json.dumps(full) and "home address" not in json.dumps(full)


def test_the_primer_is_an_index_fitted_to_its_budget(mem):
    M = mem
    assert M.primer("t1", "me/shop") == ""                                                  # nothing yet: nothing added
    for i in range(60):
        M.store("t1", "me/shop", "dt", _o(f"Finding number {i} about the checkout flow and its retries", "decision" if i % 5 == 0 else "discovery",
                                          nar="x" * 400, files=[f"app/mod{i}.py"]))
    for i in range(6):
        M.store_summary("t1", "me/shop", "dt", {"request": f"ask {i}", "completed": "done " * 40, "learned": "y" * 300}, [])
    big = M.primer("t1", "me/shop", budget=100000)
    assert "<repo_memory" in big and "Last session" in big and "Worth knowing in full" in big
    small = M.primer("t1", "me/shop", budget=2500)
    assert len(small) <= 2500 and small.startswith("<repo_memory") and small.rstrip().endswith("</repo_memory>")
    assert "Worth knowing in full" not in small and "#" in small                          # narratives go first, the index stays
    assert M.primer("t1", "me/other") == ""


def test_the_tool_three_steps_and_save(mem):
    M = mem
    oid = M.store("t1", "me/shop", "dt", _o("Orders API returns 409 on a repeated idempotency key", "discovery"))
    out, ev = M.tool("t1", "me/shop", "dt", {"action": "search", "query": "idempotency"})
    assert f"#{oid}" in out and ev == {"k": "memory", "action": "search", "q": "idempotency", "n": 1}
    out, _ = M.tool("t1", "me/shop", "dt", {"action": "get", "ids": [oid]})
    assert "409" in out and "because" in out
    out, ev = M.tool("t1", "me/shop", "dt", {"action": "save", "title": "Use the sandbox gateway in tests", "text": "never live", "type": "decision"})
    assert out.startswith("Saved as #") and ev["n"] == 1
    assert M.tool("t1", "me/shop", "dt", {"action": "save", "title": "", "text": "x"})[0].startswith("Not saved")
    assert "Nothing" in M.tool("t1", "me/shop", "dt", {"action": "search", "query": "zebra"})[0]


# ---------------------------------------------------------------- capture: the observer at the end of a round
class FakeObserver:
    def __init__(self, text):
        self.text, self.calls = text, []
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        return type("R", (), {"content": [{"type": "text", "text": self.text}], "stop_reason": "end_turn",
                              "model": kw.get("model"), "usage": None})()


def test_capture_turns_a_round_into_memory(mem, monkeypatch):
    M = mem
    from app.devsahayak import brain as B
    reply = json.dumps({"observations": [_o("Empty cart crashed total() - divide by len(items) removed", files=["app/calc.py"]),
                                         _o("A secret", "sensitive")],
                        "summary": {"request": "fix the empty cart", "completed": "total() returns the sum",
                                    "next_steps": "add a test for one item"}})
    B.CLIENT = FakeObserver("Here you go:\n" + reply)
    t = type("T", (), {"tenant_id": "t1", "repo": "me/shop", "id": "dt_9", "text": f"total() crashes <private>{KEY}</private>"})()
    out = {"explain": "Fixed it.", "files": [{"path": "app/calc.py"}], "test_plan": "ran pytest"}
    got = M.capture(t, "", {"found": {"loop": {"trail": ["read app/calc.py", "edited app/calc.py"]}}}, out, [])
    assert got == {"observations": 1, "summary": True}
    kw = B.CLIENT.calls[0]
    assert kw["model"] == "claude-haiku-5-5" and "thinking" not in kw and not kw.get("tools")
    assert KEY not in json.dumps(kw["messages"]) and "edited app/calc.py" in json.dumps(kw["messages"])
    assert M.summaries("t1", "me/shop")[0]["next_steps"] == "add a test for one item"
    # all-private ask: nothing kept, no model call; a broken answer: nothing kept, no error
    B.CLIENT = FakeObserver("{}")
    t2 = type("T", (), {"tenant_id": "t1", "repo": "me/shop", "id": "dt_10", "text": "<private>all of it</private>"})()
    assert M.capture(t2, "", {}, {}, []) == {"observations": 0, "summary": False} and B.CLIENT.calls == []
    B.CLIENT = FakeObserver("not json at all")
    assert M.capture(t, "", {}, {}, []) == {"observations": 0, "summary": False}
    B.CLIENT = None


# ---------------------------------------------------------------- end to end: session 2 starts where session 1 ended
def test_the_next_session_starts_where_the_last_one_left_off(on, monkeypatch):  # noqa: F811
    from app.config import get_settings
    from app.devsahayak import memory as M
    monkeypatch.setattr(get_settings(), "dev_memory", True, raising=False)
    M._READY.clear()
    observer = json.dumps({"observations": [_o("total() divided by len(items) - an empty cart crashed", files=["app/calc.py"])],
                           "summary": {"request": "total() crashes on an empty cart", "completed": "the divide is gone",
                                       "next_steps": "round to 2 places"}})
    first = [[tu(1, "read", path="app/calc.py")],
             [tu(2, "edit", path="app/calc.py", old_string="    return s / len(items)\n", new_string="    return s\n")],
             [tu(3, "done", explain="Fixed.", pr_title="Fix total")],
             [{"type": "text", "text": observer}]]                                      # the observer's one call
    client, events, ctx, out = _round(on, monkeypatch, first, {}, "mem-s1")
    assert any(e["k"] == "memory" and e["action"] == "remembered" for e in events)
    assert client.calls[-1]["system"][0]["text"].startswith("You are the memory observer")
    seen = {}

    def look(kw):
        seen["first"] = str(kw["messages"][0]["content"])
        seen["tools"] = [x["name"] for x in kw["tools"]]
        return [tu(4, "memory", action="search", query="empty cart")]

    def answer(kw):
        seen["result"] = kw["messages"][-1]["content"][0]["content"]
        return [tu(5, "done", explain="It already returns the sum; nothing to do.")]
    client, events, ctx, out = _round(on, monkeypatch, [look, answer, [{"type": "text", "text": "{}"}]], {}, "mem-s2")
    assert "<repo_memory" in seen["first"] and "an empty cart crashed" in seen["first"] and "round to 2 places" in seen["first"]
    assert "memory" in seen["tools"] and "an empty cart crashed" in seen["result"]
    assert any(e["k"] == "memory" and e["action"] == "search" and e["n"] == 1 for e in events)
    monkeypatch.setattr(get_settings(), "dev_memory", False, raising=False)
    from app.devsahayak import engine as EN
    assert "memory" not in [x["name"] for x in EN.tools_for_round()]


def test_routes_and_page():
    from pathlib import Path
    from app.devsahayak import api
    src = Path(api.__file__).read_text()
    for r in ('@r.get("/memory")', '@r.get("/memory/{oid}")', '@r.delete("/memory/{oid}")', '@r.delete("/memory")'):
        assert r in src
    js = (Path(api.__file__).parents[1] / "static" / "console" / "code.js").read_text()
    assert "What Hoola remembers" in js and "data-memshow" in js and "case 'memory':" in js and "Forget everything" in js
