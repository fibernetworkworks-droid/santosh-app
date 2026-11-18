"""G9 of docs/LANGGRAPH_TURN_PLAN.md:
(A) Hoola Code's end of a round is judged from what really happened (box exit codes, the push, the PR, CI) - a "done"
    the facts do not back is "not confirmed" on the task card and in tell_end - and its end notice is told ONCE per
    round outcome through a G5 delivery record (a resumed run / a repeat / a restart never tells it twice);
(B) a Video Studio / Create price card PARKS the turn graph like a bazar card (G8) and her tap resumes the SAME job.

Style of test_g8_turngraph.py: a scripted brain, the REAL studio price card (studio.service._ask writes the real
approval into the project's JSON) decided through the REAL studio.service.decide; the paid work itself (a background
job) is not started (studio.service._bg is replaced: the money is never touched in a test)."""
import asyncio
import json

import pytest

from tests.test_bazar import bz  # noqa: F401  (fixture)
from tests.test_g0_turngraph import _new_conv, _rows, _settings, tu, txt
from tests.test_g4_turngraph import gz  # noqa: F401  (fixture)
from tests.test_g8_turngraph import Brain, _drain, _parks, _shown, _checkpoints

T = "default"


# ================================================================ PART A - Hoola Code

def _task(**kw):
    from app.db import session
    from app.devsahayak.models import DevTask
    base = dict(tenant_id=T, number="D-0042", kind="fix", repo="meghana/shop", text="cart crash", base="main",
                status="pr_open", branch="hoola/d-0042", head_sha="a1b2c3d4e5f6a7b8", pr_number=7,
                pr_url="https://github.com/meghana/shop/pull/7", conv="",
                explain="Fixed the empty-cart crash. All tests pass.", test_plan="",
                changes=json.dumps([{"path": "cart.py", "new": "x", "old_sha": "s"}]))
    base.update(kw)
    with session() as s:
        t = DevTask(**base)
        s.add(t)
        s.flush()
        return t.id


def _said(monkeypatch):
    from app.devsahayak import service as S
    got = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": got.append((kind, payload)))
    return got


def _view(tid):
    from app.db import session
    from app.devsahayak import service as S
    from app.devsahayak.models import DevTask
    with session() as s:
        return S.task_view(s.get(DevTask, tid))


def _bash(cmd, rc, timed_out=False):
    return {"k": "bash", "cmd": cmd, "rc": rc, "seconds": 3.1, "timed_out": timed_out, "tail": []}


@pytest.fixture
def dev(env, monkeypatch):
    monkeypatch.setenv("DEV_TRUTH", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# (A1) "All tests pass" while the last pytest in the box exited 1 and CI is still running: the card says not
# confirmed, and tell_end does NOT say "ready" - it says what is not confirmed
def test_false_done_claim_is_reported_unconfirmed(dev, monkeypatch):
    from app.devsahayak import around as AR
    said = _said(monkeypatch)
    tid = _task(steps=json.dumps([_bash("cd server && python -m pytest -q", 0), _bash("python -m pytest -q", 1)]),
                ci=json.dumps({"state": "pending"}))
    tr = _view(tid)["truth"]
    assert tr["confirmed"] is False
    by = {c["claim"]: c for c in tr["claims"]}
    assert by["tests"]["verdict"] == "failed" and "exit code 1" in by["tests"]["why"]   # the LAST run decides
    assert by["pr"]["verdict"] == "true"                                                # the PR object exists
    assert "Not confirmed" in tr["line"] and "tests pass" in tr["line"]
    out = AR.tell_end(T, tid)
    assert out["end"] == "needs_you"
    assert "not everything is confirmed" in out["say"] and "ready for you" not in out["say"]
    assert len(said) == 1 and said[0][1]["end"] == "needs_you"


# (A1b) the same words, backed by the facts (the last pytest exited 0, CI green): confirmed, the old "ready" line
def test_backed_done_claim_is_confirmed(dev, monkeypatch):
    from app.devsahayak import around as AR
    _said(monkeypatch)
    tid = _task(steps=json.dumps([_bash("npm test", 1), _bash("npm test", 0)]), ci=json.dumps({"state": "success"}))
    tr = _view(tid)["truth"]
    assert tr["confirmed"] is True and tr["line"] == ""
    out = AR.tell_end(T, tid)
    assert out["end"] == "done" and out["say"].endswith("The pull request is ready for you to look at.")


# (A1c) claims the facts cannot back at all: no PR object, nothing pushed, no test ever ran - each said as such;
# plans and hedges ("should pass") are not claims
def test_claims_without_any_fact_and_hedges(dev):
    from app.devsahayak import truth as TR
    tid = _task(status="ready", pr_number=0, pr_url="", head_sha="", explain="Pushed the fix and opened a PR. Tests pass.",
                test_plan="Run pytest - all tests should pass.")
    tr = _view(tid)["truth"]
    by = {c["claim"]: c["verdict"] for c in tr["claims"]}
    assert by == {"tests": "none", "pr": "none", "push": "none"} and tr["confirmed"] is False
    assert TR.claims("Run pytest; all tests should pass. Will the PR be ready?") == []
    assert TR.claims("The bug is not fixed yet.") == []


# (A2) told ONCE: a repeat call, a resumed run ending in the same state, a restart between the send and the stamp -
# nothing is told again; a NEW round (rounds + 1) is a new outcome and is told once
def test_tell_end_told_once_across_repeat_and_resume(dev, monkeypatch):
    from app.agent import turndeliver as D
    from app.db import session
    from app.devsahayak import around as AR
    from app.devsahayak import truth as TR
    from app.devsahayak.models import DevTask
    said = _said(monkeypatch)
    tid = _task(steps=json.dumps([_bash("pytest", 0)]), ci=json.dumps({"state": "success"}))
    assert AR.tell_end(T, tid)["end"] == "done"
    assert AR.tell_end(T, tid) is None                    # a double call
    assert AR.tell_end(T, tid) is None                    # _resume_cut_runs re-ran the round: same outcome
    assert len(said) == 1
    with session() as s:
        key = TR.end_key(s.get(DevTask, tid))
    rec = D.get(key)
    assert rec["kind"] == "dev" and rec["channels"]["push"]["state"] == "sent"
    # a restart AFTER the stamp went to intent but before sent: maybe sent = never sent again
    D.stamp(key, "push", D.INTENT)
    assert AR.tell_end(T, tid) is None and len(said) == 1
    with session() as s:                                 # her revise ran a new round: told once more
        s.get(DevTask, tid).rounds = 1
    assert AR.tell_end(T, tid)["end"] == "done" and AR.tell_end(T, tid) is None
    assert len(said) == 2


# (A2b) the resume path itself: service._in_thread's finally calls tell_end; a resumed run of the same round tells
# nothing new
def test_resumed_background_run_does_not_tell_twice(dev, monkeypatch):
    from app.devsahayak import around as AR
    from app.devsahayak import service as S
    said = _said(monkeypatch)
    monkeypatch.setattr(AR, "make_hint", lambda tid: "")
    tid = _task(steps=json.dumps([_bash("pytest", 0)]), ci=json.dumps({"state": "success"}))
    import threading
    done = threading.Event()

    def work():
        done.set()
    for _ in range(2):                                    # the first run, then the run a restart resumed
        done.clear()
        S._in_thread(T, tid, work, job={"what": "start", "words": ""})
        for _i in range(200):
            if tid not in S._RUNNING:
                break
            import time
            time.sleep(0.02)
    assert [k for k, _ in said if k == "devsahayak_task"] == ["devsahayak_task"]


# (A3) dev_truth off = exactly the old behaviour: no truth on the card, every call publishes, "ready" is said
def test_dev_truth_off_is_the_old_behaviour(env, monkeypatch):
    monkeypatch.setenv("DEV_TRUTH", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.agent import turndeliver as D
    from app.devsahayak import around as AR
    said = _said(monkeypatch)
    tid = _task(steps=json.dumps([_bash("pytest", 1)]), ci=json.dumps({"state": "pending"}))
    assert "truth" not in _view(tid)
    a, b = AR.tell_end(T, tid), AR.tell_end(T, tid)
    assert a == b and a["end"] == "done" and "ready for you" in a["say"]
    assert len(said) == 2
    assert not [r for r in D.rows() if r["kind"] == "dev"]
    get_settings.cache_clear()


# ================================================================ PART B - studio price card parks the graph

CARD = "The price card is ready. Tap Haan to paint the opening picture."
MADE = "Started: the opening picture is being painted; it arrives as its own card."
NOT_MADE = "Okay, I did not paint it."


class StudioTools:
    """video_studio = the REAL studio price card: a real project, a real pending approval (studio.service._ask)."""

    def __init__(self):
        self.count: dict[str, int] = {}
        self.cards: list[str] = []

    async def dispatch(self, name, args, ctx):
        self.count[name] = self.count.get(name, 0) + 1
        if name == "video_studio":
            from app.studio import service as ss
            proj = "Diwali reel"
            if not any(p["project"] == proj for p in ss.listing(ctx.tenant_id, hidden=True)):
                await ss.create(ctx.tenant_id, proj, conversation_id=ctx.conversation_id)
            st = await ss.studio(ctx.tenant_id)
            out = await ss._ask(ctx.tenant_id, st, proj, {"kind": "keyframes", "shot_ids": ["s1"], "usd": 0.1, "shots": 1,
                                                          "seconds": 0, "models": ["nano-banana-pro"]})
            self.cards.append(out["waiting_owner"])
            return out
        return {"ok": True, "tool": name}


@pytest.fixture
def g9(gz, monkeypatch):  # noqa: F811
    from app.agent import turnpark
    from app.studio import service as ss
    turnpark._LOOP.clear()
    turnpark._LOCKS.clear()
    ss._studios.clear()
    started = []

    def no_bg(tenant, project, coro):              # the paid job is never started in a test
        started.append(project)
        coro.close()
    monkeypatch.setattr(ss, "_bg", no_bg)
    yield {"started": started, **gz}
    turnpark._LOOP.clear()
    turnpark._LOCKS.clear()
    ss._studios.clear()


def _setup(monkeypatch, script, graph=True, extra=None):
    _settings(monkeypatch, graph, {"AGENT_STEER": "false", "QUICK_LANE": "false", "VOICE_RING_QUIET": "0-0",
                                   "PUSH_QUIET": "0-0", "STUDIO_MONTH_USD": "60", "GRAPH_CARD_PARK": "true",
                                   **(extra or {})})
    from app.agent import santosh, set_client
    tools = StudioTools()
    monkeypatch.setattr(santosh, "dispatch", tools.dispatch)
    brain = Brain(script)
    set_client(brain)
    return brain, tools


def _turn(conv, ask):
    from app.agent import run_turn
    return asyncio.run(asyncio.wait_for(run_turn(conv, ask, tenant_id=T), 120))


def _tap(aid, yes=True):
    async def go():
        from app.agent import turnpark
        from app.studio import service as ss
        turnpark.bind_loop()
        out = await ss.decide(T, aid, yes)
        await _drain()
        return out
    return asyncio.run(asyncio.wait_for(go(), 120))


def _status(aid):
    from app.studio import service as ss
    st = ss.studio_sync(T)
    for p in ss.listing(T, hidden=True):
        a = (st.load(p["project"]).get("approvals") or {}).get(aid)
        if a:
            return a["status"]
    return ""


# (B1) a studio price card parks the graph run; her Haan runs the action through studio.decide exactly as before
# (approved, the paid job started ONCE), and the SAME thread resumes - told that the job is started, not finished
def test_studio_price_card_parks_and_her_tap_resumes(g9, monkeypatch):
    from app.agent import turnpark
    brain, tools = _setup(monkeypatch, [[tu(1, "video_studio", action="keyframes")], txt(CARD), txt(MADE)])
    conv = _new_conv()
    assert _turn(conv, "Is reel ki pehli tasveer bana do") == CARD
    parks = _parks(conv)
    assert len(parks) == 1 and parks[0]["kind"] == "studio" and parks[0]["card"] == tools.cards[0]
    assert parks[0]["status"] == "waiting" and parks[0]["tool"] == "video_studio"
    assert _checkpoints(conv)
    assert turnpark.still_waiting({"kind": "studio", "id": tools.cards[0]}) is True    # tenant read off the park row
    out = _tap(tools.cards[0], True)
    assert out["status"] == "approved" and _status(tools.cards[0]) == "approved"
    assert g9["started"] == ["Diwali reel"]                                           # the action ran once
    assert brain.calls == 3 and tools.count == {"video_studio": 1}                    # the card tool never re-ran
    flat = brain.sent[-1]
    assert turnpark.LINE_PREFIX in flat and "it RAN" in flat and "NOT ready" in flat
    assert json.loads(flat)[-1]["role"] == "user"
    assert _shown(conv).count(MADE) == 1 and _shown(conv).count(CARD) == 1
    assert _parks(conv)[0]["status"] == "resumed" and _parks(conv)[0]["answer"] == "done"
    assert _checkpoints(conv) == []
    assert turnpark.still_waiting({"kind": "studio", "id": tools.cards[0]}) is False


# (B2) Not now: resumes as declined, nothing was made, and a retry of the same card is refused by the ledger runner
def test_studio_decline_resumes_declined_and_is_never_retried(g9, monkeypatch):
    brain, tools = _setup(monkeypatch, [[tu(1, "video_studio", action="keyframes")], txt(CARD),
                                        [tu(2, "video_studio", action="keyframes")], txt(NOT_MADE)])
    conv = _new_conv()
    _turn(conv, "Is reel ki pehli tasveer bana do")
    out = _tap(tools.cards[0], False)
    assert out["status"] == "rejected" and g9["started"] == []
    assert tools.count == {"video_studio": 1}                                          # the retry never ran
    assert "Not now" in brain.sent[2]
    assert "Not now on this exact video_studio" in brain.sent[3]
    assert _shown(conv).count(NOT_MADE) == 1
    assert _parks(conv)[0]["answer"] == "declined"


# (B3) a card made outside a graph run (the old loop) or with the park switch off: no park, decide is exactly as before
@pytest.mark.parametrize("graph,park", [(False, "true"), (True, "false")])
def test_studio_card_outside_a_graph_run_behaves_as_today(g9, monkeypatch, graph, park):
    from app.agent import turnpark
    brain, tools = _setup(monkeypatch, [[tu(1, "video_studio", action="keyframes")], txt(CARD)], graph=graph,
                          extra={"GRAPH_CARD_PARK": park})
    conv = _new_conv()
    _turn(conv, "Is reel ki pehli tasveer bana do")
    assert _parks(conv) == []
    calls = []
    real = turnpark.answered
    monkeypatch.setattr(turnpark, "answered", lambda *a, **k: calls.append(a) or real(*a, **k))
    out = _tap(tools.cards[0], True)
    assert out["status"] == "approved" and g9["started"] == ["Diwali reel"]
    assert calls and calls[0][:3] == ("studio", tools.cards[0], "done")
    assert brain.calls == 2                                                            # nothing resumed


# (B4) the card_of branch: only a studio price card result (an id "sa..." with a rupee price) is a studio card
def test_card_of_studio_branch():
    from app.agent import turnpark
    c = turnpark.card_of("video_studio", {"waiting_owner": "saabc123", "inr": 9, "usd": 0.1, "project": "P"})
    assert c["kind"] == "studio" and c["id"] == "saabc123" and c["project"] == "P"
    assert turnpark.card_of("employee_x", {"status": "waiting_owner", "ask_id": "ea1"}) is None
    assert turnpark.card_of("video_studio", {"waiting_owner": "saabc", "usd": 0.1}) is None
