"""v0.714 HAR CHAT ALAG (owner: "WHY OTHER CHAT MSG IS COME IN OTHER SESSION CHAT ... DAILY COWORKER MSG SHOULD NOT BE
MERGED WITH NEW CHAT OR ANY OTHER CHAT. KEEP EVERY SESSION INDEPENDENT"): background / daily messages land in her own
pinned 'Hoola updates' chat (they used to go to whichever chat she had open), and a chat turn reads only its own chat's
jobs and cards."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.db import Conversation, Message, session

import pytest

T = "default"


@pytest.fixture(autouse=True)
def _alone(monkeypatch):
    monkeypatch.setenv("CHAT_ALONE", "true")   # conftest keeps the old rule for older suites
    from app.config import get_settings
    get_settings.cache_clear() if hasattr(get_settings, "cache_clear") else None
    yield


def _chat(cid):
    with session() as s:
        s.add(Conversation(id=cid, tenant_id=T))
    from app import convs
    convs._CACHE.clear()
    convs.mark(T, cid)
    return cid


def test_background_goes_to_updates_chat_not_the_open_chat(env):
    from app import convs
    from app.net.service import home_conv
    _chat("work1")
    _chat("newchat")                       # she opened a new chat
    home = home_conv(T)
    assert home not in ("work1", "newchat")
    assert convs.is_updates(home) and home == convs.updates_chat(T)   # one, reused
    with session() as s:
        c = s.get(Conversation, home)
        assert c.title == "Hoola updates" and c.pinned
    # the updates chat is never picked as "her last chat" by the newest-chat fallback
    with session() as s:
        from app.convs import ConvFocus
        f = s.get(ConvFocus, T)
        if f:
            s.delete(f)
    assert convs.current(T) != home


def test_inside_her_turn_the_tool_speaks_in_that_chat(env):
    from app import convs
    _chat("a1")
    _chat("b1")
    tok = convs.TURN.set("a1")
    try:
        assert convs.notice_chat(T) == "a1"
    finally:
        convs.TURN.reset(tok)
    assert convs.is_updates(convs.notice_chat(T))


def test_switch_off_keeps_old_rule(env, monkeypatch):
    from app import convs
    from app.config import get_settings
    _chat("x1")
    monkeypatch.setenv("CHAT_ALONE", "false")
    get_settings.cache_clear() if hasattr(get_settings, "cache_clear") else None
    assert convs.notice_chat(T) == "x1"


def test_cards_of_other_chats_never_reach_a_chat_turn(env):
    from app import events
    from app.events import bus
    _chat("old")
    bus.publish("old", "email_draft", {"id": "eml_9", "to": "a@b.com", "subject": "Diwali offer", "status": "pending"})
    _chat("fresh")
    blk = events.card_news_block(T, datetime.now(timezone.utc) - timedelta(seconds=5), "kya kya pending hai?", "fresh")
    assert "Diwali offer" not in blk
    blk = events.card_news_block(T, datetime.now(timezone.utc) - timedelta(seconds=5), "kya kya pending hai?", "old")
    assert "Diwali offer" in blk


def test_job_block_is_this_chats_only(env):
    from app import kaamwatch
    from app.db import now
    _chat("j1")
    _chat("j2")
    with session() as s:
        s.add(kaamwatch.KaamJob(tenant_id=T, conversation_id="j1", key="k1", kind="website", label="Website",
                                title="Sweet shop site", state="working", status="running", updated_at=now()))
        s.add(kaamwatch.KaamJob(tenant_id=T, conversation_id="", key="k2", kind="seo", label="SEO",
                                title="Daily SEO check", state="done", status="done", updated_at=now()))
    assert "Sweet shop site" in kaamwatch.block(T, "j1")
    b2 = kaamwatch.block(T, "j2")
    assert "Sweet shop site" not in b2 and "Daily SEO check" not in b2


def test_routine_runs_in_updates_chat(env):
    import inspect
    from app import worker
    src = inspect.getsource(worker.run_routines) + inspect.getsource(worker.morning_briefings)
    assert src.count("updates_chat(") >= 2
    assert "notice_chat" in inspect.getsource(worker._home_conv)


def test_turn_sets_its_chat():
    import inspect
    from app.agent import santosh
    assert "TURN.set(conversation_id)" in inspect.getsource(santosh._run_turn)
    assert "conversation_id)" in inspect.getsource(santosh._chat_memory).split("card_news_block(")[1][:120]


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.899.0")
