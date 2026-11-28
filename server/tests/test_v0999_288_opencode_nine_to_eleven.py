"""v0.999 NINE TO ELEVEN FROM OPENCODE (owner: 'GO 9 TO 11'):
(9) reads start while the model is still writing its reply (each tool_use block the moment it is whole in Claude's stream;
    only the leading run of safe reads, never one after an edit);
(10) a few words tuned to the model family in the prompt (only what Hoola Code's own workarounds show a family getting
    wrong);
(11) a step is written down before anything runs, each call marked as it starts, so after a restart the model is told
    what never ran, what was a read and what MAY have run - and Hoola never runs it again by itself."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def ses(tmp_path, monkeypatch):
    from app.devsahayak import engine as EN
    monkeypatch.setattr(EN, "root", lambda: tmp_path / "ws")
    EN.PERMIT.clear()
    s = EN.Session("t1")
    s.repo.mkdir(parents=True)
    (s.repo / "a.py").write_text("x = 1\n")
    EN._git(s.repo, "init", "-q")
    s.meta.update({"repo": "o/r", "base": EN._commit(s.repo, "base"), "hidden": []})
    s.save_meta()
    tl = EN.Tools(s, False)
    tl.conf = {}
    yield SimpleNamespace(EN=EN, s=s, tools=tl)


# ---------------------------------------------------------------- 9. reads start while the model writes
def test_only_the_leading_safe_reads_start_early(ses, monkeypatch):
    EN, tl = ses.EN, ses.tools
    ran = []
    monkeypatch.setattr(EN.Tools, "run", lambda self, name, inp: ran.append(name) or f"{name} ok")
    er = EN.EarlyReads(tl)
    for b in ({"id": "1", "name": "read", "input": {"path": "a.py"}}, {"id": "2", "name": "grep", "input": {"pattern": "x"}},
              {"id": "3", "name": "edit", "input": {"path": "a.py"}}, {"id": "4", "name": "read", "input": {"path": "a.py"}}):
        er(b)
    got = er.results([{"id": i} for i in "1234"])
    assert got == {"1": "read ok", "2": "grep ok"} and sorted(ran) == ["grep", "read"]   # nothing after the edit
    tl.conf = {"permissions": {"ask": ["Read"]}, "allow": [], "ask": ["Read"], "deny": [], "hooks": {}}
    er2 = EN.EarlyReads(tl)
    er2({"id": "9", "name": "read", "input": {"path": "a.py"}})
    assert er2.futs == {}                                                          # her rule asks first: not early


def test_the_stream_hands_over_each_tool_call_the_moment_it_is_whole(monkeypatch):
    from app.devsahayak import brain as B
    started = threading.Event()
    order = []

    class Stream:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def __iter__(self):
            yield SimpleNamespace(type="text", text="Looking. ")
            cb = SimpleNamespace(type="tool_use", id="tu1", name="read", input={"path": "a.py"})
            yield SimpleNamespace(type="content_block_stop", content_block=cb)
            started.wait(2)                                # the model is still 'writing' - the read already started
            order.append("stream went on" if started.is_set() else "stream went on without it")
            yield SimpleNamespace(type="text", text="done")

        def get_final_message(self):
            return "final"
    client = SimpleNamespace(messages=SimpleNamespace(stream=lambda **kw: Stream()))
    texts = []

    def tool_sink(b):
        order.append("read started " + b["name"] + " " + b["input"]["path"])
        started.set()
    B.TOOL_SINK.fn = tool_sink
    try:
        assert B._claude_stream(client, {}, texts.append) == "final"
    finally:
        B.TOOL_SINK.fn = None
    assert order == ["read started read a.py", "stream went on"] and texts[-1] == "Looking. done"


def test_the_round_uses_the_early_result_and_never_runs_it_twice(ses, monkeypatch):
    EN = ses.EN
    from app.devsahayak import brain as B
    ran = []
    real = EN.Tools.run
    monkeypatch.setattr(EN.Tools, "run", lambda self, name, inp: (ran.append(name), real(self, name, inp))[1])
    monkeypatch.setattr(EN.Session, "ensure", lambda self, repo, sha, token: {"reused": True})
    calls = []

    def call(system, msgs, tools, **k):
        calls.append(json.dumps(msgs[-1]["content"]))
        if len(calls) == 1:
            blk = {"type": "tool_use", "id": "r1", "name": "read", "input": {"path": "a.py"}}
            if B.TOOL_SINK.fn:
                B.TOOL_SINK.fn(blk)                         # what the stream does mid-reply
            return [blk], "tool_use"
        return [{"type": "tool_use", "id": "d", "name": "done", "input": {"explain": "ok"}}], "tool_use"
    monkeypatch.setattr(B, "call", call)
    t = SimpleNamespace(id="t1", repo="o/r", kind="fix", text="x", base="main", mode="", tenant_id="", conv="")
    try:
        EN._round(None, t, "tok", "", False, "", lambda e: None, None, None, "", None, "sha", "", "", ses.s)
    except Exception:  # noqa: BLE001
        pass
    assert ran.count("read") == 1 and "x = 1" in calls[1]
    assert not (ses.s.dir / EN.INFLIGHT).exists()                               # a step that ended leaves no record
    assert ses.s.messages()[-1]["role"] == "user"


# ---------------------------------------------------------------- 10. per model family
def test_notes_per_model_family():
    from app.devsahayak import brain as B
    assert "never as a string that contains JSON" in B.model_notes("qwen/qwen3.8-27b")
    assert "write a short first version" in B.model_notes("qwen/qwen3.8-27b")
    assert B.model_notes("claude-sonnet-5-5").startswith("Keep code comments")
    assert "Finish with the done tool" in B.model_notes("openai/gpt-6") and "Finish with" in B.model_notes("deepseek/v4")
    src = (ROOT / "server/app/devsahayak/engine.py").read_text()
    assert "notes = B.model_notes()" in src and "B.model_notes(own" in (ROOT / "server/app/devsahayak/subagent.py").read_text()


# ---------------------------------------------------------------- 11. a restart never repeats a step
def test_a_cut_step_is_told_what_ran_and_nothing_runs_again(ses):
    EN, s = ses.EN, ses.s
    uses = [{"type": "tool_use", "id": "a", "name": "read", "input": {"path": "a.py"}},
            {"type": "tool_use", "id": "b", "name": "bash", "input": {"command": "npm publish"}},
            {"type": "tool_use", "id": "c", "name": "mcp__slack__send", "input": {"text": "hi"}},
            {"type": "tool_use", "id": "d", "name": "edit", "input": {"path": "a.py"}}]
    msgs = [{"role": "user", "content": "release it"}, {"role": "assistant", "content": uses}]
    EN.begin_step(s, msgs, uses)
    assert json.loads((s.dir / EN.INFLIGHT).read_text())["ids"] == ["a", "b", "c", "d"]
    assert s.messages()[-1]["role"] == "assistant"                              # written before anything ran
    for i in ("a", "b", "c"):
        EN.mark_started(s, i)
    saved = s.messages()
    said = EN.heal_cut_step(s, saved)
    res = {r["tool_use_id"]: r["content"] for r in saved[-1]["content"]}
    assert res["a"].startswith("Did not finish") and "only reads" in res["a"]
    assert "MAY OR MAY NOT" in res["b"] and "do NOT simply run it again" in res["b"] and "MAY OR MAY NOT" in res["c"]
    assert res["d"].startswith("Did not run")
    assert "bash, mcp__slack__send may have run" in said
    assert not (s.dir / EN.INFLIGHT).exists() and s.messages()[-1]["role"] == "user"
    assert EN.heal_cut_step(s, s.messages()) == ""                              # healed once


def test_a_resumed_round_starts_from_the_answers_not_a_rerun(ses, monkeypatch):
    EN, s = ses.EN, ses.s
    from app.devsahayak import brain as B
    uses = [{"type": "tool_use", "id": "b", "name": "bash", "input": {"command": "git push"}}]
    msgs = [{"role": "user", "content": "push it"}, {"role": "assistant", "content": uses}]
    EN.begin_step(s, msgs, uses)
    EN.mark_started(s, "b")
    monkeypatch.setattr(EN.Session, "ensure", lambda self, repo, sha, token: {"reused": True})
    ran, first = [], []
    monkeypatch.setattr(EN.Tools, "run", lambda self, name, inp: ran.append(name) or "ok")
    monkeypatch.setattr(B, "call", lambda system, m, tools, **k: (first.append(json.loads(json.dumps(m))) if not first else None,
                        ([{"type": "tool_use", "id": "d", "name": "done", "input": {"explain": "checked"}}], "tool_use"))[1])
    t = SimpleNamespace(id="t1", repo="o/r", kind="fix", text="push it", base="main", mode="", tenant_id="", conv="")
    try:
        EN._round(None, t, "tok", "", False, "", lambda e: None, None, None, "", None, "sha", "", "", s, resume=True)
    except Exception:  # noqa: BLE001
        pass
    sent = first[0]
    assert sent[-1]["role"] == "user" and "MAY OR MAY NOT" in json.dumps(sent[-1]["content"])
    assert "server restarted" in json.dumps(sent[-1]["content"]) and "bash" not in ran      # Hoola never re-ran the push
