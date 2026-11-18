"""G8 of docs/LANGGRAPH_TURN_PLAN.md: (A) an approval card PARKS the turn graph (LangGraph interrupt) and her tap
resumes the SAME job with the real result; (B) the tools Gemini Live calls itself on a call go through santosh._run_tool
with a ledger on the call's chat and their real G3 effect.

Fake brain + fake tools in the style of test_g0 .. test_g6. A bazar confirm card is a REAL bz_approvals row (the demo
electricity bill pack - fetch, then pay = card), decided through the REAL bazar.decide (its claim-once update, its own
card event); an email card is a real email_drafts row. A tap runs the way the route runs it: bazar.decide in a worker
thread (asyncio.to_thread) while the server loop runs. A restart is simulated as in test_g1 (locks / live runs wiped,
a FRESH event loop)."""
import asyncio
import concurrent.futures
import json
from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from tests.test_bazar import bz  # noqa: F401  (fixture)
from tests.test_g0_turngraph import _new_conv, _rows, _settings, tu, txt
from tests.test_g4_turngraph import gz  # noqa: F401  (fixture)

CARD_SAID = "The bill payment card is ready - tap Approve to pay it."
PAID_SAID = "Done - the electricity bill is paid (demo), receipt is in the chat."
NOT_PAID = "Okay, I did not pay the bill."


class Brain:
    """Scripted brain. A step may be a coroutine function (awaited first: lets a test hold a model call open)."""

    def __init__(self, script):
        self.script = list(script)
        self.sent: list[str] = []
        self.live = 0
        self.max_live = 0
        self.messages = SimpleNamespace(create=self._create)

    @property
    def calls(self):
        return len(self.sent)

    async def _create(self, **kw):
        self.sent.append(json.dumps(kw.get("messages"), ensure_ascii=False, default=str))
        self.live += 1
        self.max_live = max(self.max_live, self.live)
        try:
            step = self.script.pop(0) if self.script else txt("(script ended)")
            if callable(step):
                step = await step()
            stop = "tool_use" if any(b["type"] == "tool_use" for b in step) else "end_turn"
            return SimpleNamespace(content=json.loads(json.dumps(step)), stop_reason=stop)
        finally:
            self.live -= 1


class Tools:
    """bazar_run = the REAL demo bill pack (fetch + pay -> a real confirm card); email_draft = a real draft row."""

    def __init__(self, svc):
        self.svc = svc
        self.count: dict[str, int] = {}
        self.cards: list[str] = []
        self.drafts: list[str] = []

    async def dispatch(self, name, args, ctx):
        self.count[name] = self.count.get(name, 0) + 1
        if name == "bazar_run":
            num = str(args.get("consumer") or "330012345678")

            def work():
                bill = self.svc.run(ctx.tenant_id, ctx.conversation_id, "msedcl-mahavitaran", "fetch_bill",
                                    {"consumer_number": num, "billing_unit": "4630"})
                return self.svc.run(ctx.tenant_id, ctx.conversation_id, "msedcl-mahavitaran", "pay_bill",
                                    {"bill_ref": bill["bill_ref"], "amount": 1})
            out = await asyncio.to_thread(work)
            self.cards.append(out["approval_id"])
            return out
        if name == "email_draft":
            from app.db import EmailDraft, session
            with session() as s:
                d = EmailDraft(tenant_id=ctx.tenant_id, conversation_id=ctx.conversation_id,
                               to_addr=str(args.get("to") or "ravi@example.com"), subject="Kal ki meeting", body="Hi")
                s.add(d)
                s.flush()
                did = d.id
            self.drafts.append(did)
            return {"draft_id": did, "to": "ravi@example.com", "subject": "Kal ki meeting",
                    "status": "pending_approval", "note": "The user will approve it by tapping 'Send'."}
        return {"ok": True, "tool": name, "rows": [1, 2, 3]}


@pytest.fixture
def g8(gz, monkeypatch):  # noqa: F811
    from app.agent import turnpark
    turnpark._LOOP.clear()
    turnpark._LOCKS.clear()
    yield gz
    turnpark._LOOP.clear()
    turnpark._LOCKS.clear()


def _setup(monkeypatch, svc, script, graph=True, extra=None):
    _settings(monkeypatch, graph, {"AGENT_STEER": "false", "QUICK_LANE": "false", "VOICE_RING_QUIET": "0-0",
                                   "PUSH_QUIET": "0-0", **(extra or {})})
    from app.agent import santosh, set_client
    tools = Tools(svc)
    monkeypatch.setattr(santosh, "dispatch", tools.dispatch)
    brain = Brain(script)
    set_client(brain)
    return brain, tools


async def _drain(limit: float = 60.0):
    """Wait for every resume the tap scheduled (and the turn it runs)."""
    from app.agent import turnpark
    end = asyncio.get_running_loop().time() + limit
    while asyncio.get_running_loop().time() < end:
        live = [t for t in list(turnpark._TASKS) if not t.done()]
        if not live:
            await asyncio.sleep(0.05)
            if not [t for t in list(turnpark._TASKS) if not t.done()]:
                return
            continue
        await asyncio.gather(*[asyncio.wrap_future(t) if isinstance(t, concurrent.futures.Future) else t
                               for t in live], return_exceptions=True)
    raise AssertionError("resumes never finished")


def _turn(conv, ask):
    from app.agent import run_turn
    return asyncio.run(asyncio.wait_for(run_turn(conv, ask, tenant_id="default"), 120))


def _tap(svc, approval_id, decision="approve"):
    """Her tap, as the route runs it: bazar.decide in a worker thread while the server loop runs."""
    async def go():
        from app.agent import turnpark
        turnpark.bind_loop()
        out = await asyncio.to_thread(svc.decide, "default", approval_id, decision)
        await _drain()
        return out
    return asyncio.run(asyncio.wait_for(go(), 120))


def _parks(conv):
    from app.agent import turnpark
    return turnpark.rows(conversation_id=conv)


def _checkpoints(conv):
    from app.agent import turngraph
    from app.config import get_settings
    return asyncio.run(turngraph.checkpoints(get_settings(), conv))


def _shown(conv):
    return [d for r, d in _rows(conv) if r == "assistant" and d]


def _decision(approval_id):
    from app.bazar.db import Approval
    from app.db import session
    with session() as s:
        return s.get(Approval, approval_id).decision


def _restart():
    from app.agent import santosh, turngraph, turnpark
    santosh._locks.clear()
    santosh._stopped.clear()
    turngraph._RUNS.clear()
    turnpark._LOOP.clear()
    turnpark._LOCKS.clear()


def _done_notice(conv):
    """bazar.decide's own chat line after a tap ('... is done.' / '... is cancelled.') - the pre-G8 path."""
    return [d for r, d in _rows(conv) if r == "assistant" and d and ("is cancelled" in d or "DEMO" in d)]


# (A1) park -> tap -> resume: the run stops at the park (interrupt checkpointed), the reply is told once; her Approve
# runs the action through bazar.decide exactly as before, the SAME thread resumes with the real result and the model
# continues the job from that step; the result is told once by the resumed run's own delivery record
def test_card_parks_the_run_and_her_tap_resumes_the_job(g8, monkeypatch):
    from app.agent import turndeliver as D
    from app.agent import turngraph, turnpark
    svc = g8["svc"]
    brain, tools = _setup(monkeypatch, svc, [[tu(1, "bazar_run", consumer="330012345678")], txt(CARD_SAID),
                                             txt(PAID_SAID)])
    conv = _new_conv()
    n0 = turngraph.STATS.get("parked_runs", 0)
    assert _turn(conv, "Mera bijli ka bill bhar do") == CARD_SAID
    assert brain.calls == 2 and tools.count == {"bazar_run": 1}
    assert turngraph.STATS.get("parked_runs", 0) == n0 + 1
    parks = _parks(conv)
    assert len(parks) == 1 and parks[0]["status"] == "waiting" and parks[0]["kind"] == "bazar"
    assert parks[0]["card"] == tools.cards[0] and parks[0]["tool"] == "bazar_run" and parks[0]["tool_use_id"] == "tu_1"
    cps = _checkpoints(conv)
    assert cps and parks[0]["thread"] == cps[0]["thread_id"]          # the thread is kept (not cleaned at END)
    assert cps[0]["values"].get("route") == "park" and cps[0]["values"]["park"]["cards"][0]["id"] == tools.cards[0]
    rec = [r for r in D.rows(conv) if r["kind"] == "turn"]
    assert len(rec) == 1 and rec[0]["outcome"] == "waiting"           # the record is honest: it waits for her tap
    assert _shown(conv).count(CARD_SAID) == 1
    # her tap: the action runs through the card's own code, ONCE; the job continues on the same thread
    out = _tap(svc, tools.cards[0])
    assert out["status"] == "approved" and _decision(tools.cards[0]) == "approved"
    assert brain.calls == 3 and tools.count == {"bazar_run": 1}       # the card tool is never re-run
    resumed = json.loads(brain.sent[-1])
    flat = json.dumps(resumed, ensure_ascii=False)
    assert "tu_1" in flat                                             # the parked step + its tool_result are there
    assert turnpark.LINE_PREFIX in flat and "it RAN" in flat          # ... and what her tap really did
    assert resumed[-1]["role"] == "user"                              # the request still ends on a user message
    assert _shown(conv).count(PAID_SAID) == 1 and _shown(conv).count(CARD_SAID) == 1
    assert not any(turnpark.LINE_PREFIX in (d or "") for d in _shown(conv) + [d for r, d in _rows(conv) if r == "user"])
    assert _done_notice(conv) == []                                   # no second 'done' line from the card's code
    assert _parks(conv)[0]["status"] == "resumed" and _parks(conv)[0]["answer"] == "done"
    assert _checkpoints(conv) == []                                   # the resumed run reached END: thread gone
    recs = [r for r in D.rows(conv) if r["kind"] == "turn"]
    assert len(recs) == 2 and recs[-1]["outcome"] == "done"           # told once, by the resumed run's record


# (A2) "Not now": the resume carries a declined result; the model must not retry the action - and when it tries,
# the ledger runner refuses the same tool + arguments in that thread (nothing ran, no new card)
def test_decline_resumes_with_declined_and_the_action_is_never_retried(g8, monkeypatch):
    svc = g8["svc"]
    brain, tools = _setup(monkeypatch, svc, [[tu(1, "bazar_run", consumer="330012345678")], txt(CARD_SAID),
                                             [tu(2, "bazar_run", consumer="330012345678")], txt(NOT_PAID)])
    conv = _new_conv()
    _turn(conv, "Mera bijli ka bill bhar do")
    out = _tap(svc, tools.cards[0], "reject")
    assert out["status"] == "rejected"
    assert tools.count == {"bazar_run": 1}                            # the retry never reached the tool
    assert "declined" in json.loads(brain.sent[2])[-1]["content"][0]["text"].lower() or \
        "Not now" in brain.sent[2]
    assert "Not now on this exact bazar_run" in brain.sent[3]          # the refusal the model got
    assert _shown(conv).count(NOT_PAID) == 1
    assert _done_notice(conv) == []                                   # the card's own 'cancelled' line is not doubled
    assert _parks(conv)[0]["answer"] == "declined"


# (A3) a restart while parked keeps the park (checkpoint + rows on disk); a tap after the restart resumes the thread
def test_restart_while_parked_then_tap_resumes(g8, monkeypatch):
    svc = g8["svc"]
    brain, tools = _setup(monkeypatch, svc, [[tu(1, "bazar_run")], txt(CARD_SAID), txt(PAID_SAID)])
    conv = _new_conv()
    _turn(conv, "Mera bijli ka bill bhar do")
    _restart()
    assert len(_checkpoints(conv)) >= 1 and _parks(conv)[0]["status"] == "waiting"
    _tap(svc, tools.cards[0])                                         # a fresh event loop = a new process
    assert brain.calls == 3 and _shown(conv).count(PAID_SAID) == 1 and tools.count == {"bazar_run": 1}
    assert _checkpoints(conv) == []


# (A3b) a restart AFTER her tap but before its resume ran: the worker's sweep picks the answered row up
def test_tap_whose_resume_a_restart_cut_is_resumed_by_the_sweep(g8, monkeypatch):
    from app.agent import turnpark
    from app.db import now, session
    svc = g8["svc"]
    brain, tools = _setup(monkeypatch, svc, [[tu(1, "bazar_run")], txt(CARD_SAID), txt(PAID_SAID)])
    conv = _new_conv()
    _turn(conv, "Mera bijli ka bill bhar do")
    _restart()
    svc.decide("default", tools.cards[0], "approve")                 # no loop in this thread: the resume cannot start
    assert _parks(conv)[0]["status"] == "answered" and brain.calls == 2
    with session() as s:
        s.get(turnpark.TurnCardPark, _parks(conv)[0]["id"]).answered_at = now() - timedelta(minutes=5)

    async def tick():
        n = await turnpark.sweep()
        await _drain()
        return n
    assert asyncio.run(tick()) >= 1
    assert brain.calls == 3 and _shown(conv).count(PAID_SAID) == 1
    assert _parks(conv)[0]["status"] == "resumed"


# (A4) a card never tapped: the park closes after the TTL (thread + ledger gone, the inbox row honest: waiting_tap
# while parked, done after), the card itself is untouched - a later tap behaves exactly as before G8
def test_untapped_card_ttl_closes_the_park_and_the_card_stays(g8, monkeypatch):
    from app import turn_inbox as ti
    from app.agent import toolledger as L
    from app.agent import turnpark
    from app.db import now, session
    from tests.test_g1_turngraph import _owned, _status
    svc = g8["svc"]
    brain, tools = _setup(monkeypatch, svc, [[tu(1, "bazar_run")], txt(CARD_SAID)], extra={"GRAPH_CARD_PARK_TTL_H": "1"})
    conv = _new_conv()
    ask = "Mera bijli ka bill bhar do"
    rid = ti.accept("default", conv, ask, False, "", "c-ttl")
    asyncio.run(_owned(conv, rid, ask))
    assert _status(rid) == "waiting_tap"                              # the turn row says it waits for her tap
    th = _parks(conv)[0]["thread"]
    assert th == f"{conv}:{rid}" and L.rows(th)
    with session() as s:
        s.get(turnpark.TurnCardPark, _parks(conv)[0]["id"]).created_at = now() - timedelta(hours=2)

    async def tick():
        n = await turnpark.sweep()
        await _drain()
        await asyncio.sleep(0.1)
        await _drain()
        return n
    asyncio.run(tick())
    assert _parks(conv)[0]["status"] == "closed" and _parks(conv)[0]["answer"] == "expired"
    assert _checkpoints(conv) == [] and L.rows(th) == []
    assert _status(rid) == "done"
    assert _decision(tools.cards[0]) == "pending"                     # the card is hers to tap, as before
    assert brain.calls == 2
    svc.decide("default", tools.cards[0], "approve")                  # a late tap: today's behaviour (its own line)
    assert brain.calls == 2 and _done_notice(conv)


# (A5) two cards in one run: the run parks on both; each answer resumes once, the first resume names the card still
# waiting and the run parks again on it; nothing is told twice
def test_two_cards_park_on_both_each_answer_resumes_once(g8, monkeypatch):
    from app import main
    svc = g8["svc"]
    brain, tools = _setup(monkeypatch, svc, [[tu(1, "bazar_run"), tu(2, "email_draft", to="ravi@example.com")],
                                             txt("Two cards are ready - the bill and the mail to Ravi."),
                                             txt("The bill is paid; the mail to Ravi still waits for your Send."),
                                             txt("Okay, the mail to Ravi was not sent.")])
    conv = _new_conv()
    _turn(conv, "Bill bhar do aur Ravi ko mail likho")
    parks = _parks(conv)
    assert {p["kind"] for p in parks} == {"bazar", "email"} and all(p["status"] == "waiting" for p in parks)
    _tap(svc, tools.cards[0])
    assert brain.calls == 3
    assert "Still waiting for her tap" in brain.sent[2] and "Kal ki meeting" in brain.sent[2]
    by = {p["kind"]: p for p in _parks(conv)}
    assert by["bazar"]["status"] == "resumed" and by["email"]["status"] == "waiting"
    assert _checkpoints(conv)                                          # parked again, on the mail card
    async def cancel():
        from app.agent import turnpark
        turnpark.bind_loop()
        await asyncio.to_thread(main.cancel_email_draft, tools.drafts[0], "default")
        await _drain()
    asyncio.run(asyncio.wait_for(cancel(), 120))
    assert brain.calls == 4
    by = {p["kind"]: p for p in _parks(conv)}
    assert by["email"]["answer"] == "declined" and by["email"]["status"] == "resumed"
    shown = _shown(conv)
    for line in ("The bill is paid; the mail to Ravi still waits for your Send.", "Okay, the mail to Ravi was not sent."):
        assert shown.count(line) == 1
    assert tools.count == {"bazar_run": 1, "email_draft": 1}
    assert _checkpoints(conv) == []


# (A6) her tap arriving while the same chat runs another turn queues behind it (turnrun tickets): never two runs on
# one chat at once - the resume starts only after that turn ended
def test_tap_during_another_run_waits_for_it(g8, monkeypatch):
    svc = g8["svc"]
    gate = {}

    async def slow():
        gate["in"].set()
        await gate["go"].wait()
        return txt("Here is the weather: sunny.")
    brain, tools = _setup(monkeypatch, svc, [[tu(1, "bazar_run")], txt(CARD_SAID), slow, txt(PAID_SAID)])
    conv = _new_conv()
    _turn(conv, "Mera bijli ka bill bhar do")

    async def go():
        from app.agent import run_turn, turnpark
        turnpark.bind_loop()
        gate["in"], gate["go"] = asyncio.Event(), asyncio.Event()
        other = asyncio.create_task(run_turn(conv, "Aaj mausam kaisa hai?", tenant_id="default"))
        await gate["in"].wait()                                       # her other turn is in its model call
        await asyncio.to_thread(svc.decide, "default", tools.cards[0], "approve")
        await asyncio.sleep(0.5)
        assert brain.calls == 3                                       # the resume waits: no second run on the chat
        gate["go"].set()
        await other
        await _drain()
    asyncio.run(asyncio.wait_for(go(), 120))
    assert brain.max_live == 1
    assert brain.calls == 4 and _shown(conv).count(PAID_SAID) == 1
    rows = _shown(conv)
    assert rows.index("Here is the weather: sunny.") < rows.index(PAID_SAID)


# (A7) claim-once still holds on a double tap: the card runs once, the park answers once, ONE resume
def test_double_tap_runs_once_and_resumes_once(g8, monkeypatch):
    from app.agent import turnpark
    from app.bazar.connectors.base import ToolError
    svc = g8["svc"]
    brain, tools = _setup(monkeypatch, svc, [[tu(1, "bazar_run")], txt(CARD_SAID), txt(PAID_SAID), txt("(again)")])
    conv = _new_conv()
    _turn(conv, "Mera bijli ka bill bhar do")

    async def two():
        turnpark.bind_loop()
        res = await asyncio.gather(asyncio.to_thread(svc.decide, "default", tools.cards[0], "approve"),
                                   asyncio.to_thread(svc.decide, "default", tools.cards[0], "approve"),
                                   return_exceptions=True)
        await _drain()
        return res
    res = asyncio.run(asyncio.wait_for(two(), 120))
    assert sum(1 for r in res if isinstance(r, dict)) == 1
    assert sum(1 for r in res if isinstance(r, ToolError)) == 1
    assert brain.calls == 3 and "(again)" not in _shown(conv)
    assert turnpark.answered("bazar", tools.cards[0], "done", "x") is False   # the row is no longer waiting


# (A8) switch off: the card ends the turn as before G8 - no park, the thread cleaned, her tap = the card's own line
def test_switch_off_is_todays_behaviour(g8, monkeypatch):
    svc = g8["svc"]
    brain, tools = _setup(monkeypatch, svc, [[tu(1, "bazar_run")], txt(CARD_SAID), txt("(never)")],
                          extra={"GRAPH_CARD_PARK": "false"})
    conv = _new_conv()
    _turn(conv, "Mera bijli ka bill bhar do")
    assert _parks(conv) == [] and _checkpoints(conv) == []
    _tap(svc, tools.cards[0])
    assert brain.calls == 2 and _done_notice(conv)


# (A9) the old loop (CHAT_GRAPH=false) is unchanged: no park, no graph, the card's own line after her tap
def test_old_loop_unchanged(g8, monkeypatch):
    from app.agent import turngraph

    async def boom(*a, **k):
        raise AssertionError("graph ran with chat_graph off")
    monkeypatch.setattr(turngraph, "run_steps", boom)
    svc = g8["svc"]
    brain, tools = _setup(monkeypatch, svc, [[tu(1, "bazar_run")], txt(CARD_SAID), txt("(never)")], graph=False)
    conv = _new_conv()
    assert _turn(conv, "Mera bijli ka bill bhar do") == CARD_SAID
    assert _parks(conv) == []
    _tap(svc, tools.cards[0])
    assert brain.calls == 2 and _done_notice(conv)


# (A10) a call's brain ask never parks (the call tells its own cards; her tap reaches it as a quiet note)
def test_call_brain_run_never_parks(g8, monkeypatch):
    from app.agent import santosh
    svc = g8["svc"]
    brain, tools = _setup(monkeypatch, svc, [[tu(1, "bazar_run")], txt(CARD_SAID)], extra={"VOICE_BRAIN": "true"})
    conv = _new_conv()

    async def go():
        from app.agent import run_turn
        tok = santosh.VOICE_BRAIN_NOW.set(True)
        try:
            return await run_turn(conv, "bill bhar do", tenant_id="default")
        finally:
            santosh.VOICE_BRAIN_NOW.reset(tok)
    asyncio.run(asyncio.wait_for(go(), 120))
    assert _parks(conv) == []


# (A11) card detection: only cards she must tap (bazar confirm card / pending email draft), nothing else
def test_card_detection():
    from app.agent import turnpark
    assert turnpark.card_of("bazar_run", {"needs_approval": True, "approval_id": "ap1", "card": {"title": "Pay"}}) == \
        {"kind": "bazar", "id": "ap1", "title": "Pay"}
    assert turnpark.card_of("email_draft", {"draft_id": "eml1", "status": "pending_approval", "subject": "Hi"})["kind"] \
        == "email"
    assert turnpark.card_of("email_draft", {"draft_id": "eml1", "status": "sent"}) is None
    assert turnpark.card_of("bazar_run", {"auto_approved": True, "approval_id": "ap1"}) is None
    assert turnpark.card_of("list_reminders", {"rows": [1]}) is None


# ------------------------------------------------------------------ (B) call direct tools on the ledger

def _call(conv, call_id="call-g8"):
    from tests.test_g6_turngraph import _call as g6_call
    c = g6_call(conv, call_id)
    c.user_buf = "Ravi ko message bhejo"
    return c


class CallTools:
    def __init__(self):
        self.count: dict[str, int] = {}
        self.cancel = set()

    async def dispatch(self, name, args, ctx):
        self.count[name] = self.count.get(name, 0) + 1
        if name in self.cancel:
            self.cancel.discard(name)
            raise asyncio.CancelledError()
        if name == "email_draft":
            return {"draft_id": "eml-x", "status": "pending_approval", "note": "tap Send"}
        return {"ok": True, "tool": name, "sent": True}


def _call_setup(monkeypatch, extra=None):
    _settings(monkeypatch, True, {"VOICE_REMINDER_GUARD": "false", **(extra or {})})
    from app import voice
    tools = CallTools()
    monkeypatch.setattr(voice, "dispatch", tools.dispatch)
    return tools


def _exec(c, name, args):
    from app import voice
    async def go():
        slot = {}
        voice._RUN_SLOT.set(slot)
        try:
            out = await c._execute(name, args)
        except Exception as e:   # noqa: BLE001
            out = {"error": str(e)}
        return out, slot
    return asyncio.run(asyncio.wait_for(go(), 60))


# (B1) a direct send through santosh._run_tool on the call's ledger; Gemini re-issuing the SAME send (a reconnect)
# never runs it twice - also after a server restart and a re-dial (a new call id on the same chat)
def test_call_direct_send_is_never_rerun(bz, monkeypatch):  # noqa: F811
    from app.agent import calltools, santosh
    from app.agent import toolledger as L
    tools = _call_setup(monkeypatch)
    seen = []
    real = santosh._run_tool

    async def spy(*a, **k):
        seen.append(a[0])
        return await real(*a, **k)
    monkeypatch.setattr(santosh, "_run_tool", spy)
    chat = _new_conv()
    c = _call(chat)
    out, slot = _exec(c, "hoola_send", {"to": "ravi", "text": "kal milte hain"})
    assert tools.count == {"hoola_send": 1} and seen == ["hoola_send"]   # the single funnel
    assert slot["fact"]["effect"] == "did" and slot["fact"]["object"] == "ravi"
    out2, slot2 = _exec(c, "hoola_send", {"to": "ravi", "text": "kal milte hain"})
    assert tools.count == {"hoola_send": 1}                            # re-issued: not run again
    assert "ALREADY DONE" in json.dumps(out2)
    th = calltools.thread(c)
    assert th == f"{chat}:call" and [r["state"] for r in L.rows(th)] == ["done"]
    c2 = _call(chat, "call-g8-redial")                                  # a re-dial after a restart: new call id
    _exec(c2, "hoola_send", {"to": "ravi", "text": "kal milte hain"})
    assert tools.count == {"hoola_send": 1}


# (B2) a send cut mid-run by a restart stays `intent`: the re-issued call gets the honest "may already have run"
def test_call_direct_send_cut_by_a_restart_is_ambiguous(bz, monkeypatch):  # noqa: F811
    tools = _call_setup(monkeypatch)
    tools.cancel.add("hoola_send")
    chat = _new_conv()
    c = _call(chat)
    with pytest.raises(asyncio.CancelledError):
        from app import voice

        async def go():
            voice._RUN_SLOT.set({})
            await c._execute("hoola_send", {"to": "ravi", "text": "hi"})
        asyncio.run(go())
    out, slot = _exec(c, "hoola_send", {"to": "ravi", "text": "hi"})
    assert tools.count == {"hoola_send": 1}
    assert "MAY ALREADY HAVE RUN" in out["error"] and slot["fact"]["effect"] == "ambiguous"


# (B3) only the NEWEST changing call counts: light on, off, on runs three times; reads never touch the ledger
def test_call_direct_on_off_on_all_run_and_reads_skip_the_ledger(bz, monkeypatch):  # noqa: F811
    from app.agent import calltools
    from app.agent import toolledger as L
    tools = _call_setup(monkeypatch)
    chat = _new_conv()
    c = _call(chat)
    for name in ("home_on", "home_off", "home_on"):
        _exec(c, name, {"entity": "light.hall"})
    assert tools.count == {"home_on": 2, "home_off": 1}
    _exec(c, "email_check", {})
    _exec(c, "email_check", {})
    assert tools.count["email_check"] == 2
    assert all(r["tool"] != "email_check" for r in L.rows(calltools.thread(c)))


# (B4) the facts are on the call record: a card is not done - the spoken 'ho gaya' after only a draft card is
# corrected, and the receipt in the chat says it waits for her tap (made once through its G5 record)
def test_call_direct_facts_card_is_not_done_and_the_receipt_says_so(bz, monkeypatch):  # noqa: F811
    from app import callreceipt, voice
    from app.agent import calltools
    from app.agent import turndeliver as D
    tools = _call_setup(monkeypatch)
    chat = _new_conv()
    c = _call(chat)

    async def go():
        fc = SimpleNamespace(name="email_draft", args={"to": "ravi@example.com", "body": "hi"}, id="fc1")
        c.send_json = lambda *a, **k: asyncio.sleep(0)
        c._answer_tool = lambda *a, **k: asyncio.sleep(0)
        c._ack_watch = c._prog_watch = lambda *a, **k: asyncio.sleep(0)
        c.hold, c.vid, c.gender, c.name = False, None, "f", "Hoola"
        c._did_mark, c._news_sent_at, c._started_at = 0, 0.0, 0.0
        c._tool_runs, c._auto_rescued = 0, set()
        c.stats = {"tools": 0}
        await voice.Call.run_tool(c, None, fc)
    asyncio.run(go())
    assert c.did[-1]["effect"] == "card" and c._did_facts[c._did_n]["effect"] == "card"
    voice.Call._check_spoken_claim(c, "Ravi ko mail bhej diya.")
    assert any("Correction" in s for s in c.said)
    done, failed, running = callreceipt._steps(c.did)
    assert done == [] and any("waiting for your tap" in r for r in running)
    assert calltools.receipt_once(c) is True and calltools.receipt_once(c) is False
    rec = D.get("call:call-g8:receipt")
    assert rec and rec["channels"]["chat"]["cards"] == 1 and rec["outcome"] == "partial"


# (B5) switch off: the call's direct tools go straight to dispatch as in G7 (no ledger, no fact)
def test_call_tools_switch_off(bz, monkeypatch):  # noqa: F811
    from app.agent import calltools
    from app.agent import toolledger as L
    tools = _call_setup(monkeypatch, {"GRAPH_CALL_TOOLS": "false"})
    chat = _new_conv()
    c = _call(chat)
    _, slot = _exec(c, "hoola_send", {"to": "ravi", "text": "a"})
    _exec(c, "hoola_send", {"to": "ravi", "text": "a"})
    assert tools.count == {"hoola_send": 2} and "fact" not in slot
    assert L.rows(calltools.thread(c)) == []


# (A12) an email draft card: her Send runs the REAL send_draft (a fake mailbox), the parked job resumes with "sent"
def test_email_send_tap_resumes_with_the_real_result(g8, monkeypatch):
    from app.mailbox import service as ms
    sent = []

    class Box:
        kind, address, key = "smtp", "me@example.com", "env"

        def send(self, msg, thread=None):
            sent.append(msg)
            return {"message_id": "<m1@example.com>"}
    monkeypatch.setattr(ms, "get_box", lambda tenant, account=None: Box())
    monkeypatch.setattr(ms, "sender_name", lambda tenant, box: "Me")
    svc = g8["svc"]
    brain, tools = _setup(monkeypatch, svc, [[tu(1, "email_draft", to="ravi@example.com")],
                                             txt("The mail to Ravi is ready - tap Send."),
                                             txt("Mail sent to Ravi.")])
    conv = _new_conv()
    _turn(conv, "Ravi ko mail likho")
    assert _parks(conv)[0]["kind"] == "email" and _parks(conv)[0]["status"] == "waiting"

    async def send():
        from app.agent import turnpark
        turnpark.bind_loop()
        out = await asyncio.to_thread(ms.send_draft, "default", tools.drafts[0], {})
        await _drain()
        return out
    asyncio.run(asyncio.wait_for(send(), 120))
    assert len(sent) == 1 and brain.calls == 3
    assert "sent to ravi@example.com" in brain.sent[2]
    assert _shown(conv).count("Mail sent to Ravi.") == 1               # the tap's fact backs the claim: no correction
    assert _parks(conv)[0]["answer"] == "done"
