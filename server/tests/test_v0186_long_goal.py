"""v0.186 Lamba kaam pakka: goals finish end to end, in chat and in calls.

Covers the owner's brief: the turn does NOT stop on text while a kaam_plan goal has open steps; a failed path gets
the "ek doosra tareeka try karta hoon" ladder (web fix -> doc read -> another tool) and one breaker rescue; a goal
that runs out of room ends honestly and carries on in ONE background continuation; max_tokens cuts continue; short
tasks keep today's numbers; and the voice call tells the truth ("abhi chal raha hai" / "atka hai", never a fake
"ho gaya"). Every gate (cards, approvals) stays exactly where it was.
"""
import asyncio
import types

import pytest

from tests.test_bazar import _events, bz  # noqa: F401


@pytest.fixture
def gz(bz, monkeypatch):  # noqa: F811
    """bz + no background chat titling (it would borrow the scripted brain for its own call)."""
    from app import chats
    monkeypatch.setattr(chats, "enabled", lambda: False)
    return bz


def tu(i, tool, **inp):
    return {"type": "tool_use", "id": f"t{i}", "name": tool, "input": inp}


def txt(t):
    return {"type": "text", "text": t}


class FakeBrain:
    """Scripted Claude: each create() pops the next response; stop_reason rides with it."""

    def __init__(self, script):
        self.script = list(script)
        self.seen = []
        self.messages = self

    async def create(self, **kw):
        self.seen.append(kw)
        blocks, stop = self.script.pop(0)
        return types.SimpleNamespace(content=blocks, stop_reason=stop)


def _set_brain(monkeypatch, brain):
    import app.agent.santosh as s
    monkeypatch.setattr(s, "get_client", lambda: brain)
    return brain


def _goal_id(conv):
    from app.agent import goal
    v = goal.active_for(conv)
    return v["id"] if v else None


def test_goal_plan_keeps_the_turn_going_until_every_step_is_done(gz, monkeypatch):  # noqa: F811
    """A 3-step plan; after step 1 the model tries to end with a text line. The goal nudge sends it back and all
    steps finish; the outcome is done, not talk."""
    conv = gz["conv"]
    brain = _set_brain(monkeypatch, FakeBrain([
        ([txt("Plan banata hoon"), tu(1, "kaam_plan", action="set", goal="Report banao",
                                      steps=["data jama karo", "draft likho", "check karke bhejo"])], "tool_use"),
        ([tu(2, "kaam_plan", action="step", n=1, state="current"),
          tu(3, "kaam_plan", action="step", n=1, state="done", reason="data mil gaya")], "tool_use"),
        ([txt("Pehle data, phir draft.")], "end_turn"),                    # tries to stop: steps are open
        ([tu(4, "kaam_plan", action="step", n=2, state="current"),
          tu(5, "kaam_plan", action="step", n=2, state="done")], "tool_use"),
        ([tu(6, "kaam_plan", action="step", n=3, state="done")], "tool_use"),
        ([txt("Report taiyaar hai, bhej diya."), tu(7, "kaam_plan", action="finish", outcome="done",
                                                    reason="report bhej diya gaya")], "tool_use"),
        ([txt("Report taiyaar hai, bhej diya.")], "end_turn"),
    ]))
    from app.agent.santosh import LAST_OUTCOME, run_turn
    out = asyncio.run(run_turn(conv, "Report banao end to end", tenant_id="default"))
    assert "Report taiyaar" in out
    # the goal nudge really went back to the brain: it saw the baaki-steps message
    assert any("baaki hain" in (b.get("text") or "") for m in brain.seen for msg in m["messages"]
               for b in (msg["content"] if isinstance(msg["content"], list) else []) if isinstance(b, dict))
    assert len(brain.seen) == 7                       # the text stop did NOT end the turn
    from app.db import Event, session
    from sqlalchemy import select
    with session() as s:
        evs = s.scalars(select(Event).where(Event.conversation_id == conv, Event.kind == "goal")
                        .order_by(Event.id)).all()
    assert len(evs) >= 5                              # set + step ticks + finish, one card per goal id
    last = evs[-1].payload
    assert last["status"] == "done" and last["total"] == 3 and last["done"] == 3
    assert LAST_OUTCOME[conv]["outcome"] == "done" and "Report" in LAST_OUTCOME[conv]["goal"]  # the goal line rides for the call
    # the goal card rides in the timeline (not LOCAL), so the phone can render it
    with session() as s:
        kinds = [e.kind for e in s.scalars(select(Event).where(Event.conversation_id == conv)).all()]
    assert "goal" in kinds


def test_failed_path_reads_docs_and_says_doosra_tareeka_breaker_rescues_once(gz, monkeypatch):  # noqa: F811
    """In goal mode a failing tool gets the ladder: the web fix arrives, the doc is READ, and after enough fails in
    a row the breaker spends ONE replan rescue instead of stopping. She sees 'doosra tareeka' once (throttled)."""
    conv = gz["conv"]
    brain = _set_brain(monkeypatch, FakeBrain([
        ([tu(1, "kaam_plan", action="set", goal="Tally se report nikalo",
             steps=["report nikalo", "verify karo", "file bhejo"])], "tool_use"),
        ([tu(2, "tally_report", report="P&L")], "tool_use"),           # fails
        ([tu(3, "tally_report", report="P&L")], "tool_use"),           # fails again
        ([tu(4, "tally_report", report="P&L")], "tool_use"),           # 3rd: tool gets constrained
        ([tu(5, "tally_report", report="P&L")], "tool_use"),           # refused, still counts in a row
        ([tu(6, "tally_report", report="P&L")], "tool_use"),
        ([tu(7, "tally_report", report="P&L")], "tool_use"),
        ([tu(8, "tally_report", report="P&L")], "tool_use"),           # 7 in a row: rescue (not stop)
        ([tu(9, "kaam_status")], "tool_use"),                                    # the other route works
        ([tu(10, "kaam_plan", action="step", n=1, state="done", reason="report nikal gaya"),
          tu(11, "kaam_plan", action="step", n=2, state="done"),
          tu(12, "kaam_plan", action="step", n=3, state="done")], "tool_use"),
        ([txt("Ho gaya, report nikal gayi."), tu(13, "kaam_plan", action="finish", outcome="done")], "tool_use"),
        ([txt("Ho gaya, report nikal gayi.")], "end_turn"),
    ]))
    from app.agent import pakka
    from app.agent.breaker import Breaker

    async def fake_fix(tool, error, request):
        return "Tally XML export use karo: admin panel -> export."

    async def fake_search(q):
        return {"sources": [{"url": "https://docs.tally.example.in/export"}], "answer": "export XML"}

    async def fake_page(url):
        return {"text": "x" * 400}

    from app import web
    monkeypatch.setattr(pakka, "internet_fix", fake_fix)
    monkeypatch.setattr(web, "search_any", fake_search)
    monkeypatch.setattr(web, "open_website", fake_page)
    from app.agent.santosh import run_turn
    out = asyncio.run(run_turn(conv, "Tally se report nikalo", tenant_id="default"))
    assert "Ho gaya" in out
    # the rescue note reached the brain, and only once
    final_msgs = brain.seen[-1]["messages"]
    notes = [b for msg in final_msgs for b in (msg["content"] if isinstance(msg["content"], list) else [])
             if isinstance(b, dict) and b.get("type") == "text" and "replan" in (b.get("text") or "")]
    assert len(notes) == 1                            # appended once to the history (snapshots repeat it)
    # she saw the doosra-tareeka line exactly once (45 s throttle in one turn)
    progress = [e for e in _events(conv, "message") if "doosra tareeka" in (e.get("text") or "")]
    assert len(progress) == 1
    # the doc text was handed to the brain (marked as data, not instructions) — inside the failing tool's result
    assert any("Docs padh liye" in str(b) for m in brain.seen for msg in m["messages"]
               for b in (msg["content"] if isinstance(msg["content"], list) else []))
    # breaker accounting: one rescue, no hard stop
    from app.agent.breaker import STATS
    assert STATS["rescue"] >= 1
    # short-task defaults untouched: a fresh Breaker still stops at 4 in a row
    b = Breaker()
    assert b.fails_in_row == 4 and b.rescue is False


def test_steps_running_out_ends_honestly_and_one_continuation_finishes(gz, monkeypatch):  # noqa: F811
    """The goal cap runs out: the reply says what is done and that it continues in the background; the outcome is
    partial; exactly ONE continuation turn runs and finishes the goal."""
    conv = gz["conv"]
    from app.config import get_settings
    st = get_settings()
    monkeypatch.setattr(st, "agent_goal_max_steps", 4)
    brain = _set_brain(monkeypatch, FakeBrain([
        ([tu(1, "kaam_plan", action="set", goal="Bahut lamba kaam",
             steps=["ek", "do", "teen", "char", "paanch", "chhah"])], "tool_use"),
        ([tu(2, "kaam_plan", action="step", n=1, state="done")], "tool_use"),
        ([tu(3, "kaam_plan", action="step", n=2, state="done")], "tool_use"),
        ([tu(4, "kaam_plan", action="step", n=3, state="current")], "tool_use"),
    ]))
    import app.agent.goal as goal_mod
    conts = []

    async def fake_cont(c, tenant, ask, gid):
        conts.append((c, ask, gid))
        goal_mod.finish("default", gid, "done", "continuation ne poora kiya")

    monkeypatch.setattr(goal_mod, "_continuation", fake_cont)
    from app.agent.santosh import LAST_OUTCOME, run_turn

    async def go():
        out = await run_turn(conv, "Bahut lamba kaam shuru karo", tenant_id="default")
        for _ in range(100):
            if conts:
                break
            await asyncio.sleep(0.02)
        return out

    out = asyncio.run(go())
    assert "steps ho gaye" in out and "background" in out          # honest, not the stale mid-task text
    # _steps records partial (TaskRun); once the continuation is scheduled the call hears 'continuing'
    assert LAST_OUTCOME[conv]["outcome"] in ("partial", "continuing")
    assert conts and "baaki steps" in conts[0][1]
    from sqlalchemy import select
    from app.db import Event, session
    with session() as s:
        evs = s.scalars(select(Event).where(Event.conversation_id == conv, Event.kind == "goal")
                        .order_by(Event.id)).all()
    v = goal_mod.show("default", evs[-1].payload["id"])
    assert v["status"] == "done" and v["reason"] == "continuation ne poora kiya"


def test_no_continuation_when_blocked_on_her_after_rokiye_or_past_rounds(gz, monkeypatch):  # noqa: F811
    from app.config import get_settings
    from app.agent import goal as goal_mod
    from app.events import bus
    conv = gz["conv"]

    # 1) a waiting approval card: the goal must not continue behind her back
    goal_mod.set_goal("default", conv, "Kaam jo uske tap chahiye", ["paise bhejo", "receipt do"])
    bus.publish(conv, "bazar_approval", {"id": "bz1", "status": "pending", "title": "Bhej doon?",
                                         "amount": "₹500", "amount_paise": 50000})
    assert goal_mod.maybe_continue(conv, "default", "owner") is False

    # 2) Rokiye: the goal is stopped, continuations refuse this chat
    from app.agent.santosh import stop
    stop(conv)
    assert goal_mod.active_for(conv) is None
    assert goal_mod.maybe_continue(conv, "default", "owner") is False

    # 3) rounds cap: a goal past AGENT_GOAL_ROUNDS closes as failed instead of continuing
    #    (a fresh chat: part 1's approval card would rightly block the check)
    from app.db import Conversation
    with goal_mod.session() as s:
        c = Conversation(tenant_id="default")
        s.add(c)
        s.flush()
        conv2 = c.id
    goal_mod._STOPPED.discard(conv2)
    v = goal_mod.set_goal("default", conv2, "Aur kaam", ["step ek"])
    with goal_mod.session() as s:
        r = s.get(goal_mod.GoalRun, v["id"])
        r.rounds = get_settings().agent_goal_rounds
    assert goal_mod.maybe_continue(conv2, "default", "owner") is False
    v2 = goal_mod.show("default", v["id"])
    assert v2["status"] == "failed" and "rounds" in v2["reason"]


def test_max_tokens_cut_continues_exactly_where_it_stopped(gz, monkeypatch):  # noqa: F811
    conv = gz["conv"]
    brain = _set_brain(monkeypatch, FakeBrain([
        ([txt("Shuru kar raha hoon, pehle data —")], "max_tokens"),
        ([txt("Shuru kar raha hoon, pehle data — phir draft, phir check.")], "end_turn"),
    ]))
    from app.agent.santosh import run_turn
    out = asyncio.run(run_turn(conv, "kaam shuru karo", tenant_id="default"))
    assert "phir check" in out
    nudge_seen = any("cut gaya" in (b.get("text") or "") for m in brain.seen
                     for msg in m["messages"] for b in (msg["content"] if isinstance(msg["content"], list) else [])
                     if isinstance(b, dict))
    assert nudge_seen


def test_short_tasks_unchanged_no_goal_block_no_goal_events(gz, monkeypatch):  # noqa: F811
    conv = gz["conv"]
    brain = _set_brain(monkeypatch, FakeBrain([([txt("Namaste! Kaise madad karoon?")], "end_turn")]))
    from app.config import get_settings
    from app.agent.santosh import run_turn
    st = get_settings()
    out = asyncio.run(run_turn(conv, "namaste", tenant_id="default"))
    assert "Namaste" in out
    assert len(brain.seen) == 1 and len(_events(conv, "goal")) == 0
    assert st.agent_max_steps == 24 and st.agent_turn_timeout_s == 900   # today's numbers stay
    # the short-task turn never got the GOAL JAARI block
    msgs = brain.seen[0]["messages"]
    assert not any("GOAL JAARI" in str(b) for m in msgs for b in (m["content"] if isinstance(m["content"], list) else []))


def test_goal_block_rides_above_every_new_turn(gz, monkeypatch):  # noqa: F811
    conv = gz["conv"]
    from app.agent import goal as goal_mod
    goal_mod.set_goal("default", conv, "Website ka content likhna hai", ["research", "draft", "final"])
    brain = _set_brain(monkeypatch, FakeBrain([
        ([txt("Theek hai, aage badhta hoon."), tu(1, "kaam_plan", action="finish", outcome="stopped",
                                                  reason="test ne band kiya")], "tool_use"),
        ([txt("Theek hai.")], "end_turn")]))
    from app.agent.santosh import run_turn
    asyncio.run(run_turn(conv, "haan aage badho", tenant_id="default"))
    flat = str(brain.seen[0]["messages"])
    assert "GOAL JAARI HAI" in flat and "research" in flat
    from sqlalchemy import select
    from app.db import Event, session
    with session() as s:
        evs = s.scalars(select(Event).where(Event.conversation_id == conv, Event.kind == "goal")
                        .order_by(Event.id)).all()
    assert evs[-1].payload["status"] == "stopped" and evs[-1].payload["id"]


# ---------------------------------------------------------------- voice truth
def _bare_call(conv):
    from app import voice
    c = object.__new__(voice.Call)
    c.closed = asyncio.Event()
    c.conv = conv
    got = []
    c.push = lambda kind, data, force=False: got.append((kind, data))
    return c, got


def _done_job(result="report taiyaar"):
    """A COMPLETED task (loop closed, task object still readable: .exception()/.result()/.cancelled())."""
    async def _ret(r):
        return r

    async def _go():
        t = asyncio.ensure_future(_ret(result))
        await t
        return t

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_go())
    finally:
        loop.close()


def _failed_job(exc: RuntimeError):
    async def _boom():
        raise exc

    async def _go():
        t = asyncio.ensure_future(_boom())
        await asyncio.gather(t, return_exceptions=True)
        return t

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_go())
    finally:
        loop.close()


def test_late_result_tells_the_truth_never_a_fake_done(gz, monkeypatch):  # noqa: F811
    conv = gz["conv"]
    from app.agent import santosh
    c, got = _bare_call(conv)

    santosh.LAST_OUTCOME[conv] = {"outcome": "partial", "left": "2/5 steps ho gaye", "goal": "Report banao"}
    c._late_result(_done_job("2/5 ho gaya"), "report banao")
    note = got[-1][1]
    assert "abhi kaam chal raha hai" in note and "khatam hote hi bataunga" in note

    santosh.LAST_OUTCOME[conv] = {"outcome": "stuck", "left": "OTP nahi mila", "goal": "Report banao"}
    c._late_result(_done_job("atka"), "report banao")
    note = got[-1][1]
    assert "atka hai" in note and "'Ho gaya' bilkul mat kehna" in note

    santosh.LAST_OUTCOME[conv] = {"outcome": "done", "left": "", "goal": "Report banao"}
    c._late_result(_done_job("poora ho gaya"), "report banao")
    note = got[-1][1]
    assert "ho gaya" in note

    # the exception branch is kept
    c._late_result(_failed_job(RuntimeError("x")), "report banao")
    assert "poora nahi ho paya" in got[-1][1]


def test_goal_events_reach_the_call_via_kaamwatch(gz, monkeypatch):  # noqa: F811
    conv = gz["conv"]
    monkeypatch.setenv("KAAM_WATCH", "true")
    from app import kaamwatch, voice
    got = []
    monkeypatch.setattr(voice, "inject", lambda c, note: got.append((c, note)) or 1)
    kaamwatch.observe(conv, "goal", {"id": "gr9", "title": "Report banao", "status": "working",
                                    "pct": 33, "stage": "draft likho"})
    assert got and "Lamba kaam" in got[-1][1] and "Report banao" in got[-1][1]
    # progress ticks are quiet (told only on real change), a blocked goal is loud
    kaamwatch.observe(conv, "goal", {"id": "gr9", "title": "Report banao", "status": "blocked",
                                    "reason": "uska jawab chahiye"})
    assert got and len(got) >= 2


def test_kaam_plan_never_declared_to_gemini_and_schema_clean(gz):  # noqa: F811
    from app import voice
    from app.agent.tools import TOOLS
    assert voice.via_kaam("kaam_plan") is True
    specs = [t["name"] for t in voice._tool_specs()]
    assert "kaam_plan" not in specs and "santosh_kaam" in specs
    d = next(t for t in TOOLS if t["name"] == "kaam_plan")
    assert voice.schema_problems(voice.fix_schema(d)) == []
