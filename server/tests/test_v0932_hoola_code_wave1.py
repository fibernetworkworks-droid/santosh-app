"""v0.932 HOOLA CODE WAVE 1 (owner: "NOW GO DEEP CHECK THE HOOLA CODE BACKEND" -> the deep check -> "GO WAVE 1"):
(1) cards published inside an open save are no longer lost to "database is locked", (2) the box can never plant git
settings the server's git would run, (3) a reply in words is the answer (never "time limit reached"), (4) one odd
tool call never ends her session, (5) her note at the finish line is read, never dropped."""
import time
from pathlib import Path

import pytest

from tests.test_tech_devsahayak import REPO, T, _join, dev  # noqa: F401
from tests.test_v0787_hoola_code_engine import FakeClient, _wait, on, tu  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------- (1) the lost cards
def test_a_card_sent_inside_an_open_save_goes_out_after_it_commits(env):
    from sqlalchemy import select

    from app.db import session
    from app.devsahayak import service as S
    from app.devsahayak.models import DevTask
    from app.events import Event
    with session() as s:
        s.add(DevTask(tenant_id=T, repo=REPO, text="x", status="new", kind="fix"))
    t0 = time.time()
    with session() as s:
        row = s.scalars(select(DevTask)).first()
        row.status = "plan_wait"
        s.flush()                                             # this thread now holds the write lock
        S._publish(T, "devsahayak_plan", {"say": "waiting for your yes"})
        with session() as s2:                                 # nothing sent yet: it waits for the save
            assert not s2.scalars(select(Event).where(Event.kind == "devsahayak_plan")).all()
    assert time.time() - t0 < 3                               # no 5 s lock wait
    with session() as s:
        evs = s.scalars(select(Event).where(Event.kind == "devsahayak_plan")).all()
        assert [e.kind for e in evs] == ["devsahayak_plan"]


def test_a_card_with_no_open_save_goes_out_at_once(env):
    from sqlalchemy import select

    from app.db import session
    from app.devsahayak import service as S
    from app.events import Event
    S._publish(T, "devsahayak_task", {"say": "hi"})
    with session() as s:
        assert s.scalars(select(Event).where(Event.kind == "devsahayak_task")).first() is not None


def test_a_rolled_back_save_sends_no_card(env):
    from sqlalchemy import select

    from app.db import session
    from app.devsahayak import service as S
    from app.devsahayak.models import DevTask
    from app.events import Event
    with pytest.raises(RuntimeError):
        with session() as s:
            s.add(DevTask(tenant_id=T, repo=REPO, text="y", status="new", kind="fix"))
            s.flush()
            S._publish(T, "devsahayak_review", {"say": "never"})
            raise RuntimeError("boom")
    with session() as s:
        assert s.scalars(select(Event).where(Event.kind == "devsahayak_review")).first() is None


# ---------------------------------------------------------------- (2) the git safety wall
def test_git_in_the_box_is_read_only_and_server_git_has_no_secrets(monkeypatch, tmp_path):
    from app.devlab import box
    from app.devsahayak import engine as EN
    seen = {}

    def fake_run(args, timeout):
        seen["args"] = args
        return 0, "ok", 0.1
    monkeypatch.setattr(box, "_run", fake_run)
    monkeypatch.setattr(box, "docker", lambda: "docker")
    (tmp_path / ".git").mkdir()
    box.run_in("img", str(tmp_path), "echo hi")
    a = " ".join(seen.get("args") or [])
    assert f"{tmp_path}/.git:/work/.git:ro" in a and f"{tmp_path}:/work:rw" in a
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret")
    env = EN._git_env()
    assert "ANTHROPIC_API_KEY" not in env and env["GIT_CONFIG_NOSYSTEM"] == "1"
    assert "core.fsmonitor=false" in EN.GIT_SAFE and "core.hooksPath=/dev/null" in EN.GIT_SAFE
    src = (ROOT / "server/app/devsahayak/engine.py").read_text()
    assert "*GIT_SAFE, *args]" in src and "never commit, stash or reset in bash" in src


# ---------------------------------------------------------------- (3) + (4) the round itself
def test_broken_tool_json_is_kept_and_answered():
    from app.devsahayak import brain as B
    from app.devsahayak import engine as EN
    data = {"choices": [{"finish_reason": "tool_calls", "message": {"content": "", "tool_calls": [
        {"id": "c1", "type": "function", "function": {"name": "read_file", "arguments": '{"path": "a.py"}'}},
        {"id": "c2", "type": "function", "function": {"name": "write", "arguments": '{"path": "b.py", "content": "x'}}]}}]}
    from app.agent import llm
    blocks, stop = B._keep_broken(data, *llm.from_openai(data))
    assert stop == "tool_use" and [b["id"] for b in blocks if b["type"] == "tool_use"] == ["c1", "c2"]
    broken = blocks[-1]["input"]
    tools = EN.Tools.__new__(EN.Tools)
    out = EN.Tools.run(tools, "write", broken)
    assert "not valid JSON" in out and "did not run" in out


def test_one_odd_call_never_ends_the_session():
    from app.devsahayak import engine as EN

    class X(EN.Tools):
        def __init__(self):
            pass

        def t_todo_write(self, todos):
            return f"{len(todos)} todos: {todos[0]['content']}"

        def t_boom(self, n=0):
            return int("not a number")
    x = X()
    assert x.run("todo_write", {"todos": '[{"content": "read", "status": "pending"}]'}) == "1 todos: read"   # JSON text read back
    assert "could not run" in x.run("boom", {"n": 1})            # ValueError -> words for the model, not a crash


def _engine_on(on, monkeypatch):  # noqa: F811
    from app.devlab import box
    monkeypatch.setattr(box, "available", lambda: {"ok": True})
    return on


def test_an_explain_answer_in_words_is_kept(on, monkeypatch):  # noqa: F811
    S = _engine_on(on, monkeypatch)
    _join(S)
    from app.devsahayak import brain as B
    answer = "total() divides by len(items), so an empty cart divides by zero. Sum only, or return 0 when empty."
    B.CLIENT = FakeClient([[tu(1, "read", path="app/calc.py")], [{"type": "text", "text": answer}]])
    v = S.start_bg(T, "explain", "Why does total() crash?", repo=REPO)
    t = _wait(S, v["id"], lambda t: not t["running"] and t["status"] != "new", 60)
    assert t["status"] == "explained", (t["status"], t.get("error"))
    assert "divides by len(items)" in (t["explain"] or "") and "time limit" not in (t["explain"] or "")
    assert len(B.CLIENT.calls) == 2                               # no extra nudge round-trip


def test_a_fix_that_answers_in_words_keeps_its_words(on, monkeypatch):  # noqa: F811
    S = _engine_on(on, monkeypatch)
    _join(S)
    from app.devsahayak import brain as B
    B.CLIENT = FakeClient([[tu(1, "read", path="app/calc.py")],
                           [{"type": "text", "text": "Looking at it."}],
                           [{"type": "text", "text": "The bug needs a product decision: should an empty cart be 0?"}]])
    v = S.start_bg(T, "fix", "total() crashes on an empty cart", repo=REPO, mode="ask")
    t = _wait(S, v["id"], lambda t: not t["running"] and t["status"] != "new", 60)
    assert "product decision" in (t["explain"] or ""), (t["status"], t.get("explain"), t.get("error"))
    assert "time limit" not in (t["explain"] or "")


def test_her_note_at_the_finish_line_is_read(monkeypatch):
    src = (ROOT / "server/app/devsahayak/engine.py").read_text()
    assert "if inbox:                                         # v0.932 also read at done" in src
    assert "Not finished yet: she just wrote to you" in src
    svc = (ROOT / "server/app/devsahayak/service.py").read_text()
    assert "Your note came in just as Hoola finished this round" in svc


def test_version():
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.935.0"' in main
    assert "version: 0.935.0+934" in (ROOT / "pubspec.yaml").read_text()
