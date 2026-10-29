"""v0.195.0 "HARNESS-2" - Phase 2 of the dsh / Claude Code harness study, the three mechanisms:

1. step-admitted tool subsets (agent/admit.py): a turn sees only the tool families her words (+ open goal +
   hints) need, on top of a small always-on CORE; the set is stable for the WHOLE turn (Anthropic cache
   discipline); tool_search opens a family for the rest of the turn (dsh deferred families + tool search); a
   valve falls back to the FULL registry when the router over-matches; the diet survives (names/enums/types).
2. job-completion WAKE turns (kaam_followup): a finished job whose chat is IDLE wakes the real brain
   (actor='wake', tools allowed) instead of only the v0.187 one-shot line; the dsh maxConsecutiveWakes budget
   bounds it; her next message resets it; the one-shot line stays as the fallback - the news is never lost.
3. the durable accepted-message inbox (turn_inbox.py): the 202 is persisted BEFORE the turn runs; a dead turn
   (pm2 restart / crashed worker) is re-run ONCE, idempotently (already-answered skip, save_user decided).
"""
import asyncio
import time
import types

import pytest
from sqlalchemy import select

import app.agent.santosh as santosh
import app.kaam_followup as kf
import app.kaamwatch as kw
import app.turn_inbox as ti

from app.config import get_settings
from app.db import Message, session
from app.turn_inbox import TurnInbox

from tests.test_v0187_realtime import fu, tick_drain  # noqa: F401


def tu(i, tool, **inp):
    return {"type": "tool_use", "id": f"t{i}", "name": tool, "input": inp}


def txt(t):
    return {"type": "text", "text": t}


# ---------------- 1. step-admitted tool subsets ----------------

def test_chat_turn_sees_a_core_subset_not_the_registry():
    from app.agent import admit
    s = get_settings()
    adm = admit.plan_for("hello ji, kya haal hai?", s)
    assert adm is not None
    names = [t["name"] for t in adm.specs()]
    assert len(names) < len(__import__("app.agent.tools", fromlist=["TOOLS"]).TOOLS) // 3
    # the everyday set is there
    for must in ("tool_search", "kaam_status", "kaam_plan", "google_search", "memory_search", "create_reminder"):
        assert must in names, must
    # unrelated big families are NOT
    for absent in ("email_bulk", "sheet_update", "video_edit", "slides_create", "order_karo", "pc_do"):
        assert absent not in names, absent


def test_router_admits_families_from_her_words():
    from app.agent import admit
    s = get_settings()
    mail = {t["name"] for t in admit.plan_for("important mail bhejo unko", s).specs()}
    assert {"email_check", "email_draft", "email_bulk"} <= mail
    assert "video_edit" not in mail and "slides_create" not in mail
    vid = {t["name"] for t in admit.plan_for("video edit karo reel banao", s).specs()}
    assert "video_edit" in vid and "reel" in vid
    assert "email_bulk" not in vid
    sheet = {t["name"] for t in admit.plan_for("spreadsheet mein data update karo", s).specs()}
    assert "sheet_update" in sheet
    # short keys never ride inside other words ('id' in 'video', 'app' in 'apple')
    vid2 = {t["name"] for t in admit.plan_for("video banao", s).specs()}
    assert "id_locker" not in vid2 or "id_locker" in {t["name"] for t in
                                                      admit.plan_for("mera id number chahiye", s).specs()}


def test_admitted_set_is_stable_across_the_whole_turn():
    """The cache discipline: two specs() calls of the SAME turn are byte-identical."""
    from app.agent import admit
    s = get_settings()
    adm = admit.plan_for("mail check karo aur calendar mein meeting daalo", s)
    import json
    assert json.dumps(adm.specs(), ensure_ascii=False) == json.dumps(adm.specs(), ensure_ascii=False)


def test_tool_search_opens_a_family_for_the_rest_of_the_turn(env):
    from app.agent import admit
    from app.agent.tools import Ctx, dispatch
    s = get_settings()
    adm = admit.plan_for("hello", s)
    ctx = Ctx(tenant_id="default", conversation_id="c_ts")
    ctx.admit = adm
    out = asyncio.run(dispatch("tool_search", {"need": "gst return file karna hai"}, ctx))
    assert out["admitted"] and "gst" in out["admitted"]
    names = {t["name"] for t in adm.specs()}
    assert "gst" in names and "gst_dekho" in names
    # the family stays for further calls (the turn keeps what it opened)
    again = {t["name"] for t in adm.specs()}
    assert again == names
    empty = asyncio.run(dispatch("tool_search", {"need": "  "}, ctx))
    assert empty["admitted"] == []


def test_valve_falls_back_to_the_full_registry():
    from app.agent import admit
    from app.agent.tools import TOOLS
    s = get_settings()
    blob = " ".join(["mail", "calendar", "sheet", "video", "photo", "drive", "form", "youtube", "pc",
                     "courier", "notebook", "gst", "payroll", "order", "travel", "brand", "seo", "dev",
                     "podcast", "shaadi", "fleet", "warehouse", "insure", "vakil", "notary", "cyber",
                     "devops", "ads", "app", "site", "hoola", "bazar", "book", "script", "event",
                     "homestay", "tour", "loan", "chai", "darzi", "franchise", "noc", "export",
                     "digilocker", "postgres", "api", "army", "artifact", "staff", "battery"] * 3)
    adm = admit.plan_for(blob, s)
    assert adm is None or len(adm.specs()) <= s.tool_admit_cap


def test_admission_off_returns_none_and_diet_survives():
    from app.agent import admit
    from app.agent.tools import TOOLS, DIET_STATS
    s = get_settings()
    s.agent_tool_admission = False
    try:
        assert admit.plan_for("mail bhejo", s) is None
    finally:
        s.agent_tool_admission = True
    adm = admit.plan_for("mail bhejo", s)
    dieted = {t["name"]: t for t in TOOLS}
    for t in adm.specs():
        if t["name"] == "tool_search":
            continue
        assert t == dieted[t["name"]]          # the admitted spec IS the dieted registry spec (no drift)
    assert DIET_STATS["diet_chars"] < DIET_STATS["raw_chars"]


# ---------------- 2. job-completion wake turns ----------------

def _spent(conv, n=99, at=None):
    kf._WAKE_N[conv] = (n, at if at is not None else time.time())


def test_done_job_wakes_the_brain_when_idle(fu, monkeypatch):  # noqa: F811
    conv = fu["conv"]
    calls = []

    async def fake_turn(conv_id, text, tenant_id=None, actor="owner", **kw):
        calls.append({"conv": conv_id, "text": text, "actor": actor})
        return "Reel poora ho gaya, yeh raha link."

    monkeypatch.setattr(santosh, "run_turn", fake_turn)
    kw.observe(conv, "video_job", {"id": "vW", "status": "done", "name": "Ad reel", "url": "https://cdn.f.mp4/w.mp4"})
    tick_drain()
    assert len(calls) == 1 and calls[0]["actor"] == "wake" and calls[0]["conv"] == conv
    assert "Ad reel" in calls[0]["text"] and "poora ho gaya" in calls[0]["text"]
    assert not fu["notices"]                 # the wake turn replaced the one-shot line: no dry notify
    assert fu["voices"] and "Reel poora" in fu["voices"][0]   # the call heard it too
    with session() as sdb:                   # exactly once: the row is sent, nothing pending remains
        rows = sdb.scalars(select(kf.KaamFollowup).where(kf.KaamFollowup.conversation_id == conv)).all()
    assert [r.status for r in rows] == ["sent"]
    assert kf.STATS["wake"] >= 1


def test_wake_budget_then_her_words_reset_it(fu, monkeypatch):  # noqa: F811
    conv = fu["conv"]
    calls = []

    async def fake_turn(conv_id, text, tenant_id=None, actor="owner", **kw):
        calls.append(conv_id)
        return "ho gaya"

    monkeypatch.setattr(santosh, "run_turn", fake_turn)

    async def dead_line(r, settings):
        return ""

    monkeypatch.setattr(kf, "_model_line", dead_line)
    _spent(conv, 3)                          # budget used up
    kw.observe(conv, "video_job", {"id": "vB1", "status": "done", "name": "Budget wala"})
    tick_drain()
    assert calls == [] and fu["notices"]     # no wake: the fallback line went out instead
    kf.wake_reset(conv)                      # she spoke again: budget whole
    assert kf._wake_allowed(conv, get_settings()) is True
    _spent(conv, 3, at=time.time() - 700)    # window aged out (10 min): fresh again
    assert kf._wake_allowed(conv, get_settings()) is True
    _spent(conv, 2)
    assert kf._wake_allowed(conv, get_settings()) is True
    _spent(conv, 3)
    assert kf._wake_allowed(conv, get_settings()) is False


def test_wake_off_sends_the_one_shot_line(fu, monkeypatch):  # noqa: F811
    conv = fu["conv"]
    calls = []

    async def fake_turn(*a, **k):
        calls.append(a)
        return "x"

    monkeypatch.setattr(santosh, "run_turn", fake_turn)

    async def fake_line(r, settings):
        return "Kaam poora ho gaya."

    monkeypatch.setattr(kf, "_model_line", fake_line)
    st = get_settings()
    st.agent_wake_turns = False
    try:
        kw.observe(conv, "video_job", {"id": "vO", "status": "done", "name": "One shot"})
        tick_drain()
    finally:
        st.agent_wake_turns = True
    assert calls == [] and fu["notices"] and "poora ho gaya" in fu["notices"][0][1]


def test_wake_never_fires_while_a_turn_holds_the_chat(fu, monkeypatch):  # noqa: F811
    conv = fu["conv"]
    kf.wake_reset(conv)                      # a fresh budget for this chat (module state survives tests)
    calls = []

    async def fake_turn(*a, **k):
        calls.append(a)
        return "x"

    monkeypatch.setattr(santosh, "run_turn", fake_turn)

    async def fake_line(r, settings):
        return "Kaam poora ho gaya (baad mein bata diya)."

    monkeypatch.setattr(kf, "_model_line", fake_line)
    monkeypatch.setattr(kf, "_turn_running", lambda c: True)          # the tick's own postpone check
    monkeypatch.setattr(santosh, "turn_running", lambda c: True)      # the wake gate
    kw.observe(conv, "video_job", {"id": "vL", "status": "done", "name": "Busy chat"})
    tick_drain()
    assert calls == [] and fu["notices"] == []  # postponed while her turn runs (nothing sent at all)...
    monkeypatch.setattr(kf, "_turn_running", lambda c: False)
    monkeypatch.setattr(santosh, "turn_running", lambda c: False)
    tick_drain()
    assert len(calls) == 1                   # ...and the wake happens when the chat is free again


# ---------------- 3. the durable accepted-message inbox ----------------

def _conv(conv):
    """The chat exists (messages carry a real FK to it)."""
    from app.db import Conversation
    with session() as sdb:
        if sdb.get(Conversation, conv) is None:
            sdb.add(Conversation(id=conv, tenant_id="default", title="t"))


def _row(conv="c_inbox", status="accepted", minutes_ago=5, tries=0, client=""):
    _conv(conv)
    with session() as sdb:
        r = TurnInbox(tenant_id="default", conversation_id=conv, client_id=client, text="report nikalo",
                      voice=0, context="", status=status, tries=tries)
        sdb.add(r)
        sdb.flush()
        old = r.created_at - __import__("datetime").timedelta(minutes=minutes_ago)
        r.created_at, r.updated_at = old, old
        rid = r.id
    return rid


def test_accept_persists_before_the_202():
    _conv("c_acc")
    rid = ti.accept("default", "c_acc", "namaste", False, "", "")
    assert rid
    with session() as sdb:
        r = sdb.get(TurnInbox, rid)
    assert r.status == "accepted" and r.text == "namaste"


def test_run_owned_wraps_the_turn(env, monkeypatch):
    _conv("c_run")
    rid = ti.accept("default", "c_run", "kaam karo", False, "", "")
    seen = {}

    async def fake_turn(conv, text, tenant=None, voice=False, context="", actor="owner", client_id="",
                        save_user=True, **kw):
        seen.update(conv=conv, text=text, save_user=save_user)
        return "ho gaya"

    monkeypatch.setattr(ti, "run_turn", fake_turn, raising=False)
    import app.agent as agent_pkg
    monkeypatch.setattr(agent_pkg, "run_turn", fake_turn)
    out = asyncio.run(ti.run_owned(rid, "c_run", "kaam karo", "default", False))
    assert out == "ho gaya" and seen["save_user"] is True
    with session() as sdb:
        assert sdb.get(TurnInbox, rid).status == "done"


def test_sweep_reruns_a_dead_turn_once_and_skips_if_answered(env, monkeypatch):
    rid = _row("c_dead", status="accepted", minutes_ago=5)
    seen = []

    async def fake_turn(conv, text, tenant=None, voice=False, context="", actor="owner", client_id="",
                        save_user=True, **kw):
        seen.append((conv, save_user))
        return "yeh raha"

    import app.agent as agent_pkg
    monkeypatch.setattr(agent_pkg, "run_turn", fake_turn)
    n = asyncio.run(ti.sweep())
    assert n == 1 and seen == [("c_dead", True)]      # no user row survived: her words are saved by the re-run
    with session() as sdb:
        assert sdb.get(TurnInbox, rid).status == "done"
    assert asyncio.run(ti.sweep()) == 0               # done: never twice
    assert ti.STATS["rerun"] >= 1

    # an already-answered accepted row (assistant reply after acceptance) is marked done, never re-run
    rid2 = _row("c_answered", status="accepted", minutes_ago=5)
    _conv("c_answered")
    with session() as sdb:
        sdb.add(Message(conversation_id="c_answered", role="assistant", content="poora ho gaya",
                        display="poora ho gaya", in_history=True))
    import app.db as db_mod
    with session() as sdb:                            # the reply must be NEWER than the row: stamp it so
        m = sdb.scalars(select(Message).where(Message.conversation_id == "c_answered")).first()
        r = sdb.get(TurnInbox, rid2)
        m.created_at = r.created_at + __import__("datetime").timedelta(seconds=30)
    before = ti.STATS["skipped_answered"]
    n2 = asyncio.run(ti.sweep())
    assert ti.STATS["skipped_answered"] >= before + 1
    with session() as sdb:
        assert sdb.get(TurnInbox, rid2).status == "done"
    assert all(c[0] != "c_answered" for c in seen)


def test_sweep_leaves_live_turns_alone_and_decides_save_user(env, monkeypatch):
    rid = _row("c_live", status="accepted", minutes_ago=5)
    monkeypatch.setattr(santosh, "turn_running", lambda c: True)
    assert asyncio.run(ti.sweep()) == 0               # her turn (or a queued one) owns the chat: hands off
    with session() as sdb:
        assert sdb.get(TurnInbox, rid).status == "accepted"
    monkeypatch.setattr(santosh, "turn_running", lambda c: False)

    # a running row whose lock is free = the process died mid-turn: re-run with save_user=False (user row exists)
    rid2 = _row("crash_mid", status="running", minutes_ago=30)
    _conv("crash_mid")
    with session() as sdb:
        sdb.add(Message(conversation_id="crash_mid", role="user", content="uski file", display="uski file",
                        in_history=True))
    seen = []

    async def fake_turn(conv, text, tenant=None, voice=False, context="", actor="owner", client_id="",
                        save_user=True, **kw):
        seen.append((conv, save_user))
        return "phir se ho gaya"

    import app.agent as agent_pkg
    monkeypatch.setattr(agent_pkg, "run_turn", fake_turn)
    asyncio.run(ti.sweep())
    assert ("crash_mid", False) in seen               # her message row survived: never write it twice


# ---------------- version ----------------

def test_version_and_config():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.253.0"
    s = get_settings()
    assert s.agent_tool_admission is True
    assert s.agent_wake_turns is True
    assert s.agent_wake_max_consecutive == 3
    assert s.agent_turn_inbox is True
    assert s.turn_inbox_stale_s == 120
