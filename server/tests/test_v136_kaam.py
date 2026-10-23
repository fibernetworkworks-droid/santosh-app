"""v0.136 Kaam ki nigraani: every long job is watched live and she is told (chat + call); Hoola answers from the real state."""
from datetime import timedelta

from sqlalchemy import select

from app.db import Conversation, Message, session


def _conv(tenant="default"):
    with session() as s:
        c = Conversation(tenant_id=tenant)
        s.add(c)
        s.flush()
        return c.id


def _notes(conv):
    with session() as s:
        return [m.display for m in s.scalars(select(Message).where(Message.conversation_id == conv,
                                                                   Message.role == "assistant")).all()]


def test_app_job_told_on_every_real_change(env, monkeypatch):
    monkeypatch.setenv("KAAM_WATCH", "true")
    from app import kaamwatch
    from app.events import bus
    conv = _conv()
    base = {"id": "app1", "number": "A-0001", "name": "Kirana App", "board": {"now": "Home", "pct": 10}}
    bus.publish(conv, "app_board", {**base, "status": "designing", "say": "Screens ban rahi hain"})
    n = _notes(conv)
    assert len(n) == 1 and "kaam shuru" in n[0] and "A-0001" in n[0]
    # small moves inside 5 min: no spam
    bus.publish(conv, "app_board", {**base, "status": "designing", "board": {"now": "Cart", "pct": 40}})
    assert len(_notes(conv)) == 1
    # waiting for her tap
    bus.publish(conv, "app_board", {**base, "status": "ready", "say": "App design v1 taiyaar. 'Design pakka' dabaiye."})
    n = _notes(conv)
    assert len(n) == 2 and "aapki baari" in n[-1] and "Design pakka" in n[-1]
    bus.publish(conv, "app_board", {**base, "status": "ready", "say": "same"})
    assert len(_notes(conv)) == 2                                  # same state never told twice
    bus.publish(conv, "app_board", {**base, "status": "approved", "say": "Design pakka (v1)."})
    assert "ho gaya" in _notes(conv)[-1]
    # Android build: failure has the error
    bus.publish(conv, "app_android", {"id": "app1", "number": "A-0001", "name": "Kirana App", "status": "building",
                                      "now": "Gradle"})
    bus.publish(conv, "app_android", {"id": "app1", "number": "A-0001", "name": "Kirana App", "status": "failed",
                                      "error": "build machine nahi mila"})
    assert "dikkat" in _notes(conv)[-1] and "build machine" in _notes(conv)[-1]
    st = kaamwatch.status("default")
    assert st["counts"]["done"] == 1 and st["counts"]["failed"] == 1
    blk = kaamwatch.block("default")
    assert "KAAM KI HAALAT" in blk and "ho gaya" in blk and "dekh raha hoon" in blk
    # not my tenant -> nothing
    assert kaamwatch.block("other") == ""


def test_progress_lines_throttled_and_stuck_watchdog(env, monkeypatch):
    monkeypatch.setenv("KAAM_WATCH", "true")
    monkeypatch.setenv("KAAM_PROGRESS_S", "0")
    from app import kaamwatch
    from app.events import bus
    conv = _conv()
    v = {"id": "v1", "title": "Diwali reel", "status": "watching", "stage": "Footage dekh raha hoon", "progress": 10}
    bus.publish(conv, "video_job", v)
    bus.publish(conv, "video_job", {**v, "status": "rendering", "stage": "Video jod raha hoon", "progress": 60})
    n = _notes(conv)
    assert "kaam shuru" in n[0] and "chal raha" in n[1] and "60%" in n[1]
    # stuck: nothing moved for longer than KAAM_STUCK_S
    with session() as s:
        r = s.scalars(select(kaamwatch.KaamJob)).first()
        r.moved_at = r.moved_at - timedelta(minutes=30)
    assert kaamwatch.tick() == 1
    assert "atka" in _notes(conv)[-1]
    assert kaamwatch.tick() == 0                                   # told once
    bus.publish(conv, "video_job", {**v, "status": "done", "stage": "Taiyaar", "progress": 100})
    assert "ho gaya" in _notes(conv)[-1]


def test_job_started_inside_her_turn_is_not_repeated_and_dup_is_skipped(env, monkeypatch):
    monkeypatch.setenv("KAAM_WATCH", "true")
    from app import kaamwatch
    from app.events import bus, notify
    conv = _conv()
    monkeypatch.setattr(kaamwatch, "_turn_running", lambda c: True)
    bus.publish(conv, "site_board", {"id": "s1", "number": "W-0001", "name": "Salon site", "status": "planned", "say": "plan"})
    assert _notes(conv) == []                                     # the reply of that turn says it
    monkeypatch.setattr(kaamwatch, "_turn_running", lambda c: False)
    # the job's own service already said it: not said twice
    with session() as s:
        r = s.scalars(select(kaamwatch.KaamJob)).first()
        r.started_at = r.started_at - timedelta(minutes=10)
    bus.publish(conv, "site_board", {"id": "s1", "number": "W-0001", "name": "Salon site", "status": "ready", "say": "taiyaar"})
    assert _notes(conv) == []                                     # still waiting for her: same state, nothing new
    notify(conv, "Website W-0001 Salon site live ho gayi")
    bus.publish(conv, "site_board", {"id": "s1", "number": "W-0001", "name": "Salon site", "status": "live", "say": "live"})
    assert len(_notes(conv)) == 1
    assert kaamwatch.STATS["skipped_dup"] >= 1


def test_voice_note_and_tool(env, monkeypatch):
    monkeypatch.setenv("KAAM_WATCH", "true")
    import asyncio
    from app import kaamwatch, voice
    from app.agent.tools import HANDLERS, Ctx
    from app.events import bus
    conv = _conv()
    got = []

    class FakeLoop:
        def call_soon_threadsafe(self, fn, *a):
            fn(*a)

    class FakeCall:
        tenant = "default"

        def push(self, kind, text):
            got.append(text)
    voice.ACTIVE[conv] = [(FakeLoop(), FakeCall())]
    try:
        bus.publish(conv, "operator_task", {"id": "op1", "title": "Bijli bill", "status": "running", "stage": "Login"})
        bus.publish(conv, "operator_task", {"id": "op1", "title": "Bijli bill", "status": "done", "summary": "Bill PDF mila"})
    finally:
        voice.ACTIVE.pop(conv, None)
    assert any("Kaam update" in t and "ho gaya" in t for t in got)
    out = asyncio.run(HANDLERS["kaam_status"](Ctx("default", conv), q="bijli"))
    assert out["counts"]["done"] == 1 and "Bijli" in out["say"]
    # unknown kinds and plain messages are ignored
    bus.publish(conv, "typing", {"on": True})
    bus.publish(conv, "random_card", {"text": "hi"})
    assert len(kaamwatch.jobs("default")) == 1
