"""G6 of docs/LANGGRAPH_TURN_PLAN.md: voice is a CHANNEL of the same turn graph (`chat_graph` on).

A call's brain ask (voice.Call._delegate -> turn_inbox.run_owned -> santosh.run_turn) runs through the SAME graph as a
chat turn - nodes, G1 ledger, G2 ticket + Stop, G3 facts, G4 job thread, G5 delivery record - and the call is only its
channel: the deliver node fills the call's ticket, the call tells the result from that record ONCE (the tool answer or
Call._late_result), the phone gets no push for what she heard on the call, and a call that has ended leaves the result
to the chat (its row + push) without the next call telling it again.

No real Gemini: the Call is built without __init__ (no websocket, no live session) and its speech is the list its
push_news / _orphan_note append to. The brain is scripted, the tools are fake (kaam_plan is the real tool), push is
counted at the FCM pool (test_g5's fixture), a restart is simulated as in test_g1."""
import asyncio
import json
import time
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from tests.test_bazar import bz  # noqa: F401  (fixture)
from tests.test_g0_turngraph import _new_conv, _rows, tu, txt
from tests.test_g2_turngraph import HALT, MIDWAY
from tests.test_g4_turngraph import FINAL, SEG1, _age_goal, _goal, _job_next, _quiet, gz  # noqa: F401  (fixture)
from tests.test_g5_turngraph import g5  # noqa: F401  (fixture)

CRASH = "CRASH"
SENT_REPLY = "Ravi ko mail bhej diya - subject 'Kal ki meeting'."
DRAFT_REPLY = "Ravi ke liye mail ka draft taiyaar hai - bhejne ke liye aapki haan chahiye."


class Brain:
    """Scripted brain (sequential); CRASH raises CancelledError (the process dies during that model call)."""

    def __init__(self, script):
        self.script = list(script)
        self.sent: list[str] = []
        self.models: list[str] = []
        self.messages = SimpleNamespace(create=self._create)

    @property
    def calls(self):
        return len(self.sent)

    async def _create(self, **kw):
        self.sent.append(json.dumps(kw.get("messages"), ensure_ascii=False, default=str))
        self.models.append(str(kw.get("model") or ""))
        step = self.script.pop(0) if self.script else txt("(script ended)")
        if step == CRASH:
            raise asyncio.CancelledError()
        stop = "tool_use" if any(b["type"] == "tool_use" for b in step) else "end_turn"
        return SimpleNamespace(content=json.loads(json.dumps(step)), stop_reason=stop)


class Tools:
    """kaam_plan is the REAL tool; the rest are fake. `slow` = seconds per call, email_draft answers as a draft card."""

    def __init__(self, real, slow=None):
        self.real = real
        self.slow = dict(slow or {})
        self.count: dict[str, int] = {}
        self.cancelled: list[str] = []

    async def dispatch(self, name, args, ctx):
        self.count[name] = self.count.get(name, 0) + 1
        if name == "kaam_plan":
            return await self.real(name, args, ctx)
        try:
            if self.slow.get(name):
                await asyncio.sleep(self.slow[name])
        except asyncio.CancelledError:
            self.cancelled.append(name)
            raise
        if name == "email_draft":
            return {"ok": True, "status": "draft_ready", "draft_id": "d1", "to": args.get("to")}
        return {"ok": True, "tool": name, "rows": [1, 2, 3]}


def _setup(monkeypatch, graph, script, extra=None, slow=None):
    from tests.test_g0_turngraph import _settings
    _settings(monkeypatch, graph, {"VOICE_BRAIN": "true", "VOICE_BRAIN_WAIT_S": "20", "VOICE_CHECKIN_MAX": "0",
                                   "AGENT_STEER": "false", "QUICK_LANE": "false", "VOICE_RING_QUIET": "0-0",
                                   "PUSH_QUIET": "0-0", **(extra or {})})
    from app.agent import santosh, set_client
    tools = Tools(santosh.dispatch, slow=slow)
    monkeypatch.setattr(santosh, "dispatch", tools.dispatch)
    brain = Brain(script)
    set_client(brain)
    return brain, tools


def _chat_and_record(call_id="call-g6"):
    from app import callconv
    chat = _new_conv()
    return chat, callconv.open_for("default", chat, call_id)


def _call(conv, call_id="call-g6"):
    """A Call without Gemini: what it would SAY lands in .said, what it saves for the next call in .orphans."""
    from app import voice
    from app.agent.tools import Ctx
    c = voice.Call.__new__(voice.Call)
    c.conv, c.tenant, c.call_id = conv, "default", call_id
    c.ctx = Ctx("default", conv)
    c.stats, c.closed, c.ws = {}, asyncio.Event(), object()
    c.user_buf, c._typed, c.recent, c._tools, c._mcp_route = "", None, [], set(), {}
    c.did, c._did_n = [], 0
    c.said, c.orphans = [], []
    c.push_news = c.said.append
    c._orphan_note = c.orphans.append
    c._tone_tag = lambda: ""
    c._place = lambda request="": ""
    return c


def _live(c):
    """Register the call as live on its record (what Call.run does): push.on_event then holds its replies."""
    from app import voice
    voice.ACTIVE.setdefault(c.conv, []).append((asyncio.get_running_loop(), c))


def _hang_up(c):
    from app import voice
    c.closed.set()
    for k in list(voice.ACTIVE):
        voice.ACTIVE[k] = [x for x in voice.ACTIVE[k] if x[1] is not c]
        if not voice.ACTIVE[k]:
            voice.ACTIVE.pop(k, None)


async def _settle(job, limit=60.0):
    """The job's task is over and its done callbacks ran."""
    await asyncio.wait_for(asyncio.shield(job), limit) if not job.done() else None
    for _ in range(5):
        await asyncio.sleep(0.05)


def _did(c, job, ok=True):
    """What Call.run_tool records for the santosh_kaam call that started `job` (the did entry + its run)."""
    c._did_n += 1
    c.did.append({"tool": "santosh_kaam", "label": "kaam", "ok": ok, "n": c._did_n})
    run = getattr(job, "_hoola_run", None)
    if run is not None:
        runs = getattr(c, "_did_runs", None)
        if runs is None:
            runs = c._did_runs = {}
        runs[c._did_n] = run


def _deliveries(conv):
    from app.agent import turndeliver as D
    return [r for r in D.rows(conv) if r["kind"] != "job"]


def _shown(conv):
    return [d for r, d in _rows(conv) if r == "assistant" and d and not d.startswith("(Kaam:")]


class Jobs(set):
    """Stands in for voice._JOBS: remembers every job a call started (a finished one leaves the real set at once)."""

    def __init__(self):
        super().__init__()
        self.seen: list = []

    def add(self, j):
        self.seen.append(j)
        super().add(j)


def _jobs(monkeypatch):
    from app import voice
    js = Jobs()
    monkeypatch.setattr(voice, "_JOBS", js)
    voice.ACTIVE.clear()
    return js


def _job_of(words):
    from app import voice
    return next((j for j in reversed(voice._JOBS.seen) if getattr(j, "_hoola_run", {}).get("request") == words),
                voice._JOBS.seen[-1] if voice._JOBS.seen else None)


async def _ask(c, words, wait_job=True):
    """Her words on the call -> santosh_kaam -> Call._delegate (the real one). Returns (tool answer, job)."""
    from app import voice
    out = await voice.Call._delegate(c, words)
    job = _job_of(words)
    if wait_job and job is not None:
        await _settle(job)
    return out, job


@pytest.fixture
def g6(g5, monkeypatch):  # noqa: F811
    from app import voice
    _jobs(monkeypatch)
    yield g5
    voice.ACTIVE.clear()


# (1) a call ask runs as a graph run: the same nodes, the ledger, the facts, the call channel + profile in state; the
# answer is the tool answer (told once on the call) and the phone gets no push for it
def test_a_call_ask_is_a_graph_run_told_once_on_the_call(g6, monkeypatch):
    from app.agent import toolledger as L
    from app.agent import turndeliver as D
    from app.agent import turngraph
    from app.config import get_settings
    brain, tools = _setup(monkeypatch, True, [[tu(1, "email_send", to="ravi@x.in", subject="Kal ki meeting")],
                                              txt(SENT_REPLY)], extra={"CHAT_GRAPH_KEEP_FINISHED": "true"})
    chat, rec = _chat_and_record()
    s0 = dict(turngraph.STATS)
    intents = []
    real_intent = L.intent
    monkeypatch.setattr(L, "intent", lambda *a: (intents.append(a[2]), real_intent(*a))[1])

    async def go():
        c = _call(rec)
        _live(c)
        out, job = await _ask(c, "Ravi ko mail bhejo kal ki meeting ke baare mein")
        cps = await turngraph.checkpoints(get_settings(), rec)
        return c, out, job, cps
    c, out, job, cps = asyncio.run(asyncio.wait_for(go(), 120))
    assert out == {"result": SENT_REPLY}
    assert turngraph.STATS["turns"] == s0["turns"] + 1 and turngraph.STATS["call_runs"] == s0["call_runs"] + 1
    assert intents == ["email_send"]                                    # the G1 ledger wrapped the tool
    assert tools.count == {"email_send": 1}
    assert brain.models and all(m == get_settings().voice_brain_model for m in brain.models)   # the call profile: Haiku
    vals = max(cps, key=lambda r: r["step"] or 0)["values"]
    assert vals["channel"] == "call" and vals["profile"]["brain"] is True
    assert vals["profile"]["model"] == get_settings().voice_brain_model and vals["profile"]["thinking"] is False
    assert [f["effect"] for f in vals["facts"]] == ["did"] and vals["facts"][0]["ledger"] == "done"   # G3 facts
    run = job._hoola_run
    assert run["result"] == "done" and run["did"] == 1 and run["key"].startswith("turn:")
    rec_d = D.get(run["key"])
    assert rec_d["channels"]["call"]["state"] == D.SENT and rec_d["channels"]["call"]["via"] == "the tool answer"
    assert rec_d["channels"]["push"]["state"] == D.HELD                 # she heard it: no phone notification
    assert not g6["pool"].replies(SENT_REPLY)
    assert _shown(rec) == [SENT_REPLY] and _shown(chat) == []          # the call record, never the chat (callconv)
    assert c.said == [] and c.orphans == []                             # told once: the tool answer, no late news
    # a second done callback (a re-attached callback, a late duplicate) tells nothing again
    from app import voice
    voice.Call._late_result(c, job, "Ravi ko mail bhejo", time.time() - 60)
    assert c.said == [] and c.stats.get("call_told_once") == 1


# (2) a late result: told on the live call ONCE from the record (not a stale outcome), never pushed to the phone
def test_a_late_result_is_told_on_the_call_once_from_the_record(g6, monkeypatch):
    from app import voice
    from app.agent import santosh
    from app.agent import turndeliver as D
    _setup(monkeypatch, True, [[tu(1, "email_send", to="ravi@x.in")], txt(SENT_REPLY)],
           extra={"VOICE_BRAIN_WAIT_S": "1"}, slow={"email_send": 2.0})
    chat, rec = _chat_and_record()
    santosh.LAST_OUTCOME[rec] = {"outcome": "stuck", "left": "an EARLIER ask got stuck", "goal": "", "at": time.time()}

    async def go():
        c = _call(rec)
        _live(c)
        out, job = await _ask(c, "Ravi ko mail bhejo")
        voice.Call._late_result(c, job, "Ravi ko mail bhejo", time.time() - 60)   # a second callback: nothing more
        return c, out, job
    c, out, job = asyncio.run(asyncio.wait_for(go(), 120))
    assert out["status"] == "working"
    assert len(c.said) == 1 and "is done:" in c.said[0] and SENT_REPLY in c.said[0]
    assert "EARLIER" not in c.said[0]                                    # the record of THIS run, not a stale outcome
    run = job._hoola_run
    ch = D.get(run["key"])["channels"]
    assert ch["call"]["state"] == D.SENT and ch["call"]["via"] == "news at a pause"
    assert ch["push"]["state"] == D.HELD and not g6["pool"].replies(SENT_REPLY)
    assert c.orphans == [] and c.stats.get("call_told_once") == 1


# (3) the call ended before the result: the chat row + its push tell her, and the next call does not tell it again
def test_after_hang_up_the_chat_tells_it_and_the_next_call_does_not(g6, monkeypatch):
    from app.agent import turndeliver as D
    _setup(monkeypatch, True, [[tu(1, "email_send", to="ravi@x.in")], txt(SENT_REPLY)],
           extra={"VOICE_BRAIN_WAIT_S": "1"}, slow={"email_send": 2.0})
    chat, rec = _chat_and_record()

    async def go():
        c = _call(rec)
        _live(c)
        out = await __import__("app.voice", fromlist=["Call"]).Call._delegate(c, "Ravi ko mail bhejo")
        _hang_up(c)                                                      # she hangs up while the mail is going
        job = _job_of("Ravi ko mail bhejo")
        await _settle(job)
        return c, out, job
    c, out, job = asyncio.run(asyncio.wait_for(go(), 120))
    assert out["status"] == "working"
    assert len(g6["pool"].replies(SENT_REPLY)) == 1                    # the chat (its push) told her, once
    assert c.orphans == [] and c.said == []                             # ... so the next call does not tell it again
    ch = D.get(job._hoola_run["key"])["channels"]
    assert ch["push"]["state"] == D.SENT and ch["call"]["state"] == D.SKIPPED
    assert c.stats.get("late_told_in_chat") == 1


# (3b) hung up AFTER the reply was held for the live call: she was not told yet -> the next call tells it (once)
def test_held_for_the_call_then_hung_up_goes_to_the_next_call(g6, monkeypatch):
    from app.agent import turndeliver as D
    _setup(monkeypatch, True, [[tu(1, "email_send", to="ravi@x.in")], txt(SENT_REPLY)],
           extra={"VOICE_BRAIN_WAIT_S": "1"}, slow={"email_send": 1.5})
    chat, rec = _chat_and_record()

    async def go():
        from app import voice
        c = _call(rec)
        _live(c)
        real = voice.Call._late_result

        def late(self, job, request="", since=0.0):   # the hang-up lands between the deliver node and the callback
            _hang_up(self)
            return real(self, job, request, since)
        monkeypatch.setattr(voice.Call, "_late_result", late)
        out, job = await _ask(c, "Ravi ko mail bhejo")
        return c, out, job
    c, out, job = asyncio.run(asyncio.wait_for(go(), 120))
    assert not g6["pool"].replies(SENT_REPLY)                           # held: the call was live at delivery
    assert len(c.orphans) == 1 and SENT_REPLY in c.orphans[0] and c.said == []
    assert D.get(job._hoola_run["key"])["channels"]["call"]["via"] == "a note for the next call"


# (4) "band karo" on a call stops the SAME run (G2 Stop as state), across the call record / side record
def test_band_karo_on_a_call_stops_the_running_call_ask(g6, monkeypatch):
    from app import turn_inbox as ti
    from app import voice
    from app.agent import turndeliver as D
    from app.db import session
    _setup(monkeypatch, True, [[tu(1, "email_send", to="ravi@x.in")], txt("should not run")],
           extra={"VOICE_BRAIN_WAIT_S": "1"}, slow={"email_send": 8})
    chat, rec = _chat_and_record()

    async def go():
        c = _call(rec)
        _live(c)
        out1 = await voice.Call._delegate(c, "Ravi ko 20 mail bhejo")
        job1 = _job_of("Ravi ko 20 mail bhejo")
        c.user_buf = "band karo"                                         # her live words; Gemini reads them its way
        t0 = time.monotonic()
        out2 = await voice.Call._execute(c, "santosh_kaam", {"request": "stop the mail job"})
        await _settle(job1)
        return c, out1, out2, job1, time.monotonic() - t0
    c, out1, out2, job1, took = asyncio.run(asyncio.wait_for(go(), 60))
    assert out1["status"] == "working"
    assert str(out2.get("result", "")).startswith("Okay, stopped")      # the stop ran BEFORE the lock (kaamstop)
    assert took < 5
    r1 = job1.result()
    assert r1.startswith(HALT) and MIDWAY in r1
    with session() as s:
        st = s.get(ti.TurnInbox, job1._hoola_run["inbox"]).status
    assert st == "stopped"
    assert job1._hoola_run["result"] == "stopped"
    assert D.get(job1._hoola_run["key"])["channels"]["call"]["state"] in (D.SKIPPED,)
    assert not any("is done:" in x for x in c.said)                     # never "ho gaya" for a stopped job


# (5) a false spoken "ho gaya" after santosh_kaam is corrected from the run's FACTS (only a draft card was made)
def test_a_false_spoken_claim_is_corrected_from_the_facts(g6, monkeypatch):
    from app import voice
    _setup(monkeypatch, True, [[tu(1, "email_draft", to="ravi@x.in", subject="Kal")], txt(DRAFT_REPLY)])
    chat, rec = _chat_and_record()

    async def go():
        c = _call(rec)
        _live(c)
        out, job = await _ask(c, "Ravi ko mail bhejo")
        return c, out, job
    c, out, job = asyncio.run(asyncio.wait_for(go(), 120))
    assert out == {"result": DRAFT_REPLY}
    _did(c, job)
    voice.Call._check_spoken_claim(c, "Theek hai, Ravi ko mail bhej diya.")
    assert len(c.said) == 1 and "Correction" in c.said[0] and "card" in c.said[0]
    assert c.stats["voice_claim_by_facts"] == 1
    # a TRUE claim about the same draft stands
    c.said.clear()
    _did(c, job)
    voice.Call._check_spoken_claim(c, "Draft taiyaar hai, aap haan bolein to bhej dungi.")
    assert c.said == []


def test_a_true_spoken_claim_after_a_real_send_stands(g6, monkeypatch):
    from app import voice
    _setup(monkeypatch, True, [[tu(1, "email_send", to="ravi@x.in")], txt(SENT_REPLY)])
    chat, rec = _chat_and_record()

    async def go():
        c = _call(rec)
        _live(c)
        return c, *(await _ask(c, "Ravi ko mail bhejo"))
    c, out, job = asyncio.run(asyncio.wait_for(go(), 120))
    _did(c, job)
    voice.Call._check_spoken_claim(c, "Ravi ko mail bhej diya.")
    assert c.said == [] and "voice_claim_by_facts" not in c.stats


# (6) a call ask during the chat's long job reaches the JOB THREAD (G4): its next segment reads what the call did
def test_a_call_ask_reaches_the_chats_long_job_thread(gz, monkeypatch):  # noqa: F811
    from app import voice
    from app.agent import goal, turngraph
    from app.db import Message, session
    seg2 = [[tu(6, "kaam_plan", action="step", n=3, state="done"), tu(11, "kaam_plan", action="step", n=4, state="done"),
             tu(7, "kaam_plan", action="finish", outcome="done", reason="chaaron kadam")], txt(FINAL)]
    call_steps = [[tu(10, "kaam_plan", action="add", text="chaar: report PDF mein bhi")],
                  txt("Theek hai, job mein chautha kadam jod diya.")]
    brain, tools = _setup(monkeypatch, True, SEG1 + call_steps + seg2, extra={"AGENT_GOAL_MAX_STEPS": "3"})
    _jobs(monkeypatch)
    real_schedule = goal._schedule
    monkeypatch.setattr(goal, "_schedule", lambda *a, **k: True)       # the round waits: the job sits at `carry`
    chat = gz["conv"]
    from tests.test_g4_turngraph import _job_turn
    _job_turn(chat)
    assert brain.calls == 3 and _job_next(chat) == "carry"
    from app import callconv
    rec = callconv.open_for("default", chat, "call-job")
    s0 = dict(turngraph.STATS)

    async def call():
        c = _call(rec, "call-job")
        _live(c)
        return await _ask(c, "us kaam mein report PDF mein bhi daal do")
    out, job = asyncio.run(asyncio.wait_for(call(), 120))
    assert out == {"result": "Theek hai, job mein chautha kadam jod diya."}
    assert turngraph.STATS["call_job_notes"] == s0["call_job_notes"] + 1
    g = _goal(chat)
    assert len(g["steps"]) == 4                                          # kaam_plan add reached the chat's job
    with session() as s:
        notes = [m for m in s.scalars(select(Message).where(Message.conversation_id == chat)).all()
                 if m.display is None and "From her voice call" in json.dumps(m.content, ensure_ascii=False)]
    assert len(notes) == 1 and notes[0].in_history                      # history only: never shown, never pushed
    # the job continues on its own thread: the next segment reads the call's line
    monkeypatch.setattr(goal, "_schedule", real_schedule)
    from tests.test_g4_turngraph import _restart
    _restart()
    _age_goal(chat)

    async def recover():
        n = goal.recover_tick()
        await _quiet()
        return n
    assert asyncio.run(recover()) == 1
    assert turngraph.STATS["job_resumed"] == s0["job_resumed"] + 1
    seg = brain.sent[5]
    assert "From her voice call" in seg and "[Goal jaari" in seg
    assert _goal(chat)["status"] == "done"
    assert _shown(chat).count(FINAL) == 1


# (7) every chat tool is reachable on a call: declared to Gemini Live, or santosh_kaam into the graph - none unknown
def test_every_registered_tool_reaches_a_call(g6, monkeypatch):
    from app import voice
    from app.agent import tools as T
    names = {t["name"] for t in T.TOOLS} | set(getattr(T, "HANDLERS", {}).keys())
    assert len(names) > 300
    declared = {t["name"] for t in voice._tool_specs()}
    asked = []

    class Fake:
        user_buf = "yeh kaam kar do"
        _mcp_route = {}
        _typed = None
        recent = ()
        call_id = "walk"
        stats: dict = {}
        ctx = SimpleNamespace(place="")

        def _place(self, request=""):
            return ""

        async def _delegate(self, request):
            asked.append(request)
            return {"status": "working"}

    lost, unknown = [], []
    for n in sorted(names):
        route = voice.call_route(n)
        if route == "declared":
            assert n in declared, n
            continue
        if route != "kaam":
            lost.append(n)
            continue
        out = asyncio.run(voice.Call._execute(Fake(), n, {"x": 1}))
        if out != {"status": "working"}:
            unknown.append((n, out))
    assert not lost, lost
    assert not unknown, unknown[:5]
    assert len(asked) == sum(1 for n in names if voice.call_route(n) == "kaam")
    # and one of them end to end: the real _delegate -> a graph run that runs the tool the call wanted
    from app.agent import turngraph
    brain, tools = _setup(monkeypatch, True, [[tu(1, "sheet_format", spreadsheet="Sales", bold=True)],
                                              txt("Sales sheet ka header bold kar diya.")])
    chat, rec = _chat_and_record()
    s0 = turngraph.STATS["call_runs"]

    async def go():
        c = _call(rec)
        _live(c)
        c.user_buf = "Sales sheet ka header bold kar do"
        return await voice.Call._execute(c, "sheet_format", {"spreadsheet": "Sales", "format": {"bold": True}})
    out = asyncio.run(asyncio.wait_for(go(), 120))
    assert out == {"result": "Sales sheet ka header bold kar diya."}
    assert turngraph.STATS["call_runs"] == s0 + 1 and tools.count == {"sheet_format": 1}
    assert "sheet_format" in brain.sent[0]                              # the call's wish rode into the graph run


# (8) a call ask cut by a restart resumes as a CALL ask (its profile), and the chat row + push deliver it
def test_a_call_ask_resumed_after_a_restart_keeps_its_channel(g6, monkeypatch):
    from app import turn_inbox as ti
    from app.agent import santosh, turndeliver as D, turngraph
    from tests.test_g1_turngraph import _age, _restart, _status, _sweep
    brain, tools = _setup(monkeypatch, True, [[tu(1, "list_reminders")], CRASH, txt("Aapke 3 reminder hain.")])
    chat, rec = _chat_and_record()
    rid = ti.accept("default", rec, "mere reminders batao", False, "", "c-g6r")
    s0 = dict(turngraph.STATS)

    async def first():
        tok = santosh.VOICE_BRAIN_NOW.set(True)
        ctok = D.CALL.set({"call": "call-g6", "conv": rec, "origin": rec, "inbox": rid, "request": "mere reminders batao"})
        try:
            await ti.run_owned(rid, rec, "mere reminders batao", "default", False)
        finally:
            D.CALL.reset(ctok)
            santosh.VOICE_BRAIN_NOW.reset(tok)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(first())
    _restart()
    _age(rid)
    assert asyncio.run(_sweep()) == 1
    assert turngraph.STATS["resumed"] == s0["resumed"] + 1 and turngraph.STATS["call_resumed"] == s0["call_resumed"] + 1
    assert tools.count == {"list_reminders": 1}                         # the done tool is not run again (G1)
    from app.config import get_settings
    assert brain.models[-1] == get_settings().voice_brain_model         # still the call brain's model after the restart
    assert _status(rid) == "done"
    recs = _deliveries(rec)
    assert len(recs) == 1 and recs[0]["channels"]["call"]["state"] == D.SKIPPED   # its call is gone
    assert recs[0]["channels"]["push"]["state"] == D.SENT and len(g6["pool"].replies("Aapke 3 reminder hain.")) == 1


# (9) switch off: the old call path, byte for byte - no ticket, no graph run, no delivery record, the old late line
def test_switch_off_keeps_the_old_call_path(g6, monkeypatch):
    from app import voice
    from app.agent import santosh, turngraph
    _setup(monkeypatch, False, [[tu(1, "email_draft", to="ravi@x.in")], txt(DRAFT_REPLY)])
    chat, rec = _chat_and_record()
    s0 = dict(turngraph.STATS)

    async def go():
        c = _call(rec)
        _live(c)
        return c, *(await _ask(c, "Ravi ko mail bhejo"))
    c, out, job = asyncio.run(asyncio.wait_for(go(), 120))
    assert out == {"result": DRAFT_REPLY}
    assert getattr(job, "_hoola_run", None) is None
    assert turngraph.STATS["turns"] == s0["turns"] and turngraph.STATS["call_runs"] == s0["call_runs"]
    assert _deliveries(rec) == []
    # the old path as it is: the inline tool answer ALSO comes back as late news (v0.657's hang-up callback runs
    # before _delegate resumes, so it is not yet "handed") - the graph path tells it once (test 1 asserts said == [])
    late = [x for x in c.said if "big job" in x]
    assert len(late) == 1 and DRAFT_REPLY in late[0]
    n = len(c.said)
    # the old spoken-claim check: santosh_kaam ran ok, so the claim is not challenged (what G6 changes on the graph)
    _did(c, job)
    voice.Call._check_spoken_claim(c, "Ravi ko mail bhej diya.")
    assert len(c.said) == n
    # the old late line reads LAST_OUTCOME with the 'since' guard
    santosh.LAST_OUTCOME[rec] = {"outcome": "done", "left": "", "goal": "", "at": time.time()}
    f = asyncio.new_event_loop()
    try:
        fut = f.create_future()
        fut.set_result("ho gaya")
        voice.Call._late_result(c, fut, "kaam", time.time() - 5)
    finally:
        f.close()
    assert len(c.said) == n + 1 and "is done: ho gaya" in c.said[-1]
