"""v0.649 SACH MEIN ROKO (owner: "IF I TELL ON VOICE CANCLE THIS TASK.... IT SAYS I HAVE CANCLED IT ... STILL WHEN I HAVE COME
BACK ON VOICE IT TELL ... I AM WORKING ON THAT"): a cancel really stops the job, everywhere, and nothing says it is still
running afterwards."""
from __future__ import annotations

import asyncio
import inspect
import types
from datetime import datetime, timedelta, timezone

from app.db import Conversation, Message, session

T = "default"


def _chat(cid: str) -> str:
    with session() as s:
        s.add(Conversation(id=cid, tenant_id=T))
    return cid


def _job(conv: str, key: str, title: str, kind: str = "site_board", label: str = "Website", minutes_ago: float = 5):
    from app.kaamwatch import KaamJob
    at = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    with session() as s:
        s.add(KaamJob(tenant_id=T, conversation_id=conv, key=key, kind=kind, label=label, title=title, state="working",
                      status="building", updated_at=at, moved_at=at, started_at=at))


def _row(key: str):
    from app.kaamwatch import KaamJob
    with session() as s:
        r = s.query(KaamJob).filter_by(key=key).one()
        return r.state, r.status


def test_stop_words():
    from app.kaamstop import wants_stop
    for yes in ("cancel karo", "is kaam ko cancel kar do", "roko", "website wala band karo", "rehne do yeh kaam",
                "stop it", "sab roko", "isko cancle karo"):
        assert wants_stop(yes), yes
    for no in ("reminder cancel karo", "kal ki meeting cancel kar do", "light band karo", "call band karo",
               "pankha band karo", "aaj ka mausam batao", "[Kaam update] roko", "draft cancel karo",
               "ek lambi kahani sunao jisme raja ne yudh roko kaha aur phir sena wapas lauti aur sab khush huye"):
        assert not wants_stop(no), no


def test_cancel_newest_marks_it_stopped_everywhere(env, monkeypatch):
    from app import kaam_followup, kaamstop
    from app.site import service as S
    stopped = []
    monkeypatch.setattr(S, "stop", lambda tenant, ref: stopped.append(ref) or {"ok": True})
    _chat("c1")
    _job("c1", "site_board:old", "Bakery site", minutes_ago=30)
    _job("c1", "site_board:new", "Clinic site", minutes_ago=1)
    kaam_followup.ensure_table()
    with session() as s:
        s.add(kaam_followup.KaamFollowup(tenant_id=T, conversation_id="c1", key="site_board:new", kind="site_board",
                                         label="Website", title="Clinic site", state="done", status="pending"))
    out = kaamstop.cancel(T, "cancel karo", "c1")
    assert out["how"] == "newest" and out["stopped"] == ["Website Clinic site"]
    assert stopped == ["new"]                                   # the kind's own stop really ran
    assert _row("site_board:new") == ("stopped", "cancelled")
    assert _row("site_board:old")[0] == "working"               # only what she meant
    assert "stopped: Website Clinic site" in out["say"] and "Bakery site" in out["say"]   # what still runs is named
    with session() as s:
        assert s.query(kaam_followup.KaamFollowup).filter_by(key="site_board:new").one().status == "skipped"


def test_named_all_and_unmatched(env, monkeypatch):
    from app import kaamstop
    from app.research import runner as R
    from app.site import service as S
    monkeypatch.setattr(S, "stop", lambda tenant, ref: {"ok": True})
    monkeypatch.setattr(R, "stop", lambda tenant, rid: "stopped")
    _chat("c2")
    _job("c2", "site_board:s1", "Mithai shop", minutes_ago=1)
    _job("c2", "research_run:r1", "GST rates research", kind="research_run", label="Research", minutes_ago=3)
    out = kaamstop.cancel(T, "research wala roko", "c2")
    assert out["how"] == "named" and out["stopped"] == ["Research GST rates research"]
    assert _row("site_board:s1")[0] == "working"
    nothing = kaamstop.cancel(T, "invoice wala roko", "c2")       # names something that is not running: touch nothing
    assert nothing["how"] == "unmatched" and nothing["stopped"] == [] and _row("site_board:s1")[0] == "working"
    every = kaamstop.cancel(T, "sab roko", "c2")
    assert every["how"] == "all" and _row("site_board:s1") == ("stopped", "cancelled")


def test_a_running_turn_is_stopped_and_never_rerun(env):
    from app import kaamstop, turn_inbox
    from app.agent import santosh
    _chat("c3")
    iid = turn_inbox.accept(T, "c3", "Sharma ji ko 20 mail bhejo", True, "", "", "")
    turn_inbox.mark(iid, "running")

    async def go():
        lk = santosh._locks["c3"]
        await lk.acquire()                                       # the job she wants cancelled holds the chat
        try:
            return await asyncio.to_thread(kaamstop.cancel, T, "cancel karo", "c3")
        finally:
            lk.release()
    out = asyncio.run(go())
    assert out["stopped"] == ["Sharma ji ko 20 mail bhejo"]
    assert "c3" in santosh._stopped                              # the Stop button's own path
    santosh._stopped.discard("c3")
    with session() as s:
        assert s.get(turn_inbox.TurnInbox, iid).status == "stopped"   # a restart never re-runs it
    assert kaamstop.recently_cancelled("c3")


def test_a_late_event_never_brings_it_back(env, monkeypatch):
    from app import kaamstop, kaamwatch
    from app.site import service as S
    monkeypatch.setattr(S, "stop", lambda tenant, ref: {"ok": True})
    monkeypatch.setenv("KAAM_WATCH", "true")
    told = []
    import app.events as events
    monkeypatch.setattr(events, "notify", lambda conv, text, *a, **k: told.append(text))
    _chat("c4")
    _job("c4", "site_board:w1", "Salon site")
    kaamstop.cancel(T, "roko", "c4")
    kaamwatch.observe("c4", "site_board", {"id": "w1", "status": "live", "name": "Salon site"})   # it finished anyway
    assert _row("site_board:w1") == ("stopped", "cancelled")
    assert told == []                                             # not announced as "ho gaya"
    st = kaamwatch.status(T)
    assert st["counts"]["working"] == 0


def test_her_words_stop_the_job_before_the_turn_waits(env, monkeypatch):
    """The whole path: 'cancel karo' is answered from what really stopped - no model call, no waiting for the lock."""
    from app.agent import santosh
    from app.site import service as S
    monkeypatch.setattr(S, "stop", lambda tenant, ref: {"ok": True})
    _chat("c5")
    _job("c5", "site_board:b1", "Bakery site")

    async def go():
        lk = santosh._locks["c5"]
        await lk.acquire()                                       # a long turn is still running in this chat
        try:
            return await asyncio.wait_for(santosh.run_turn("c5", "isko cancel kar do", T, True), 5)
        finally:
            lk.release()
    say = asyncio.run(go())
    santosh._stopped.discard("c5")
    assert say.startswith("Okay, stopped") and "Bakery site" in say
    assert _row("site_board:b1") == ("stopped", "cancelled")
    with session() as s:
        shown = [m.display for m in s.query(Message).filter_by(conversation_id="c5").order_by(Message.id)]
    assert shown[-2:] == ["isko cancel kar do", say]


def test_nothing_running_goes_to_the_brain():
    from app.agent import santosh
    src = inspect.getsource(santosh._run_turn)
    i = src.index("kaamstop.wants_stop(user_text)")
    assert 'if _ks.get("stopped"):' in src[i:i + 400]            # only a REAL stop answers by itself
    assert src.index("kaamstop.wants_stop(user_text)") < src.index("lock = _locks[conversation_id]")


def test_the_tool_never_stops_its_own_turn(env):
    from app.agent import kaam_tools
    src = inspect.getsource(kaam_tools.kaam_status)
    assert "kaamstop.cancel, ctx.tenant_id, str(q or \"\")[:200], ctx.conversation_id,\n                                       ctx.conversation_id" in src
    desc = kaam_tools.KAAM_TOOLS[0]["description"]
    assert "action=stop REALLY cancels" in desc and "NEVER say a job is cancelled" in desc


def test_a_call_drops_the_news_of_a_cancelled_job(env):
    from app import kaamstop, voice
    kaamstop._RECENT["callrec1"] = __import__("time").monotonic()
    said = []
    fake = types.SimpleNamespace(conv="callrec1", stats={}, closed=asyncio.Event(), push_news=said.append,
                                 _tone_tag=lambda: "")

    async def go():
        f = asyncio.get_running_loop().create_future()
        f.set_result("partial words")
        voice.Call._late_result(fake, f, "website banao")
    asyncio.run(go())
    assert said == [] and fake.stats["cancelled_news_dropped"] == 1


def test_gemini_never_claims_a_cancel_itself():
    from app import voice
    assert "Never say a job is cancelled yourself" in voice.PERSONA_BRAIN
    assert "never say it is cancelled before its reply says so" in voice.PERSONA_LEAN


def test_cancel_from_the_next_call_stops_the_job_of_the_last_call(env, monkeypatch):
    """Her exact case: a job given on call 1 (its own record), 'cancel karo' on call 2 (a new record), and call 3 is
    told it is stopped - not 'kaam chal raha hai'."""
    from app import callconv, kaamstop, kaamwatch, turn_inbox
    from app.agent import santosh
    from app.site import service as S
    monkeypatch.setattr(S, "stop", lambda tenant, ref: {"ok": True})
    callconv._KIND.clear()
    callconv._ORIGIN.clear()
    _chat("chat")
    call1 = callconv.open_for(T, "chat", "")
    call2 = callconv.open_for(T, "chat", "")
    _job(call1, "site_board:c1", "Kirana site")
    iid = turn_inbox.accept(T, call1, "kirana ki website banao", True, "", "", "")
    turn_inbox.mark(iid, "running")

    async def go():
        lk = santosh._locks[call1]
        await lk.acquire()                                       # call 1's santosh_kaam job is still running
        try:
            return await asyncio.to_thread(kaamstop.cancel, T, "website wala cancel karo", call2)
        finally:
            lk.release()
    out = asyncio.run(go())
    assert out["stopped"] == ["Website Kirana site"]
    assert call1 in santosh._stopped                             # call 1's running job got the Stop
    santosh._stopped.discard(call1)
    with session() as s:
        assert s.get(turn_inbox.TurnInbox, iid).status == "stopped"
    call3 = callconv.open_for(T, "chat", "")
    blk = kaamwatch.block(T, call3)                              # what the next call reads
    assert "Kirana site: band" in blk and "chal raha hai" not in blk
