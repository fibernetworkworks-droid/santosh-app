"""v0.187.0 "REALTIME - the first words fast + the result in her own words":

1. Schema diet: 384 tool specs measured ~568 KB and every one of the up-to-24 model calls re-sent them all -
   15-60 s of dead air before the first word on the production brain (no prompt cache). The diet keeps every
   name / type / enum / required field; prose shrinks with graduated caps (safety-word tools keep their rules).
2. The 5-second ack: a turn silent that long first says "Ek second, dekh raha hoon…" as an EPHEMERAL message -
   no Event row, no push, never in history, the real reply replaces it.
3. say-lines: after every tool step one TRUE line about the result ("12 mails aaye") streams to the phone
   (new `say` STREAM kind), rule-based, no model call, never a guess.
4. kaam_followup: a finished/failed background job gets ONE message in Hoola's own words with the actual
   result (tiny one-shot model call, no tools), queued by kaamwatch, sent by a worker slot, canned line as
   fallback, postponed while her turn runs, deduped when the turn itself already told her.
"""
import asyncio

import pytest
from sqlalchemy import select

import app.kaam_followup as kf
import app.kaamwatch as kw


def run(coro):
    return asyncio.run(coro)


# ---------------- 1. schema diet ----------------

def test_diet_keeps_every_tool_name_and_shrinks_hard():
    from app.agent.tools import DIET_STATS, TOOLS, _RAW_SPECS
    assert len(TOOLS) == len(_RAW_SPECS) >= 300
    names = [t["name"] for t in TOOLS]
    raw_names = [t["name"] for t in _RAW_SPECS]
    assert names == raw_names and len(set(names)) == len(names)     # order + uniqueness untouched
    assert DIET_STATS["raw_chars"] > 500_000
    assert DIET_STATS["diet_chars"] < DIET_STATS["raw_chars"] * 0.75   # at least ~25% off (measured ~33%)


def test_diet_preserves_enums_required_and_types():
    import json
    from app.agent.tools import TOOLS, _RAW_SPECS
    raw_enum = next(t for t in _RAW_SPECS if '"enum"' in json.dumps(t.get("input_schema", {})))
    d = next(t for t in TOOLS if t["name"] == raw_enum["name"])
    assert json.dumps(d, ensure_ascii=False).count('"enum"') == json.dumps(raw_enum, ensure_ascii=False).count('"enum"')
    for raw in _RAW_SPECS[:80]:
        diet = next(t for t in TOOLS if t["name"] == raw["name"])
        rd = raw.get("input_schema") or {}
        dd = diet.get("input_schema") or {}
        assert (rd.get("required") or []) == (dd.get("required") or [])
        assert set((rd.get("properties") or {}).keys()) == set((dd.get("properties") or {}).keys())


def test_diet_keeps_safety_prose_and_trims_ordinary():
    from app.agent.tools import DIET_SAFETY_MAX, _DIET_KEEP_RE, _RAW_SPECS, TOOLS
    safety = [t for t in _RAW_SPECS if len(t.get("description", "")) > DIET_SAFETY_MAX and _DIET_KEEP_RE.search(t["description"])]
    assert safety, "the safety whitelist should catch real safety tools"
    for raw in safety[:5]:
        diet = next(t for t in TOOLS if t["name"] == raw["name"])
        flat = " ".join(raw["description"].split())
        flat_diet = " ".join(diet["description"].split())
        assert flat.startswith(flat_diet[:200]) and len(flat_diet) >= 200   # a clean prefix: the rules survive
    ordinary = [t for t in _RAW_SPECS if len(t.get("description", "")) > 200 and not _DIET_KEEP_RE.search(t["description"])]
    assert ordinary, "ordinary long descriptions exist"
    for raw in ordinary[:5]:
        diet = next(t for t in TOOLS if t["name"] == raw["name"])
        assert len(diet["description"]) <= 141   # 140 + the ellipsis


# ---------------- 2. the 5-second ack ----------------

class _PubSpy:
    def __init__(self):
        self.calls = []

    def publish(self, conv, kind, payload, *a, **kw):
        self.calls.append((conv, kind, payload, kw))
        return {"id": 0, "kind": kind, "payload": payload}

    def publish_live(self, conv, kind, payload, *a, **kw):
        self.calls.append((conv, kind, payload, kw))
        return {"id": 0, "kind": kind, "payload": payload}


def test_ack_goes_out_when_the_turn_is_silent(env, monkeypatch):
    import app.agent.santosh as s
    from app.db import Conversation, Message, session
    conv = "conv_ack1"
    with session() as sdb:
        sdb.add(Conversation(id=conv, tenant_id="default", title="t"))
    spy = _PubSpy()
    monkeypatch.setattr(s, "bus", spy)
    s._ACKED.add(conv)
    s._locks.setdefault(conv, s._locks.get(conv) or __import__("asyncio").Lock())
    async def held():
        async with s._locks[conv]:
            s._ACKED.add(conv)
            await s._ack_later(conv, "m", delay=0)
    run(held())
    acks = [c for c in spy.calls if c[1] == "message" and c[2].get("ack")]
    assert len(acks) == 1 and acks[0][3].get("ephemeral") is True
    assert "dekh" in acks[0][2]["text"] or "Ho raha" in acks[0][2]["text"] or len(acks[0][2]["text"]) < 60
    with session() as sdb:   # ephemeral: nothing saved
        msgs = sdb.scalars(select(Message).where(Message.conversation_id == conv)).all()
    assert not msgs
    assert conv not in s._ACKED


def test_ack_skipped_when_words_already_out_or_turn_over(env, monkeypatch):
    import app.agent.santosh as s
    from app.db import Conversation, Message, session
    conv = "conv_ack2"
    with session() as sdb:
        sdb.add(Conversation(id=conv, tenant_id="default", title="t"))
    spy = _PubSpy()
    monkeypatch.setattr(s, "bus", spy)
    s._locks.setdefault(conv, __import__("asyncio").Lock())

    # (a) the turn already spoke: no ack
    with session() as sdb:
        sdb.add(Message(conversation_id=conv, role="assistant", content=[{"type": "text", "text": "lo"}],
                        display="lo", in_history=True))
    async def held():
        async with s._locks[conv]:
            s._ACKED.add(conv)
            await s._ack_later(conv, "m", delay=0)
    run(held())
    assert not [c for c in spy.calls if c[1] == "message"]

    # (b) the turn is over: no ack
    s._ACKED.add(conv)
    run(s._ack_later(conv, "m", delay=0))
    assert not [c for c in spy.calls if c[1] == "message"]
    assert conv not in s._ACKED


def test_ephemeral_publish_stores_nothing_and_pushes_nowhere(env, monkeypatch):
    import app.events as ev
    import app.push as push_mod
    from app.db import Event, session
    pushed = []
    monkeypatch.setattr(push_mod, "on_event", lambda conv, data: pushed.append(data))
    q = ev.bus.subscribe("conv_eph")
    try:
        ev.bus.publish("conv_eph", "message", {"role": "assistant", "text": "Ek second…"}, ephemeral=True)
        data = q.get_nowait()
        assert data["payload"]["text"] == "Ek second…" and data.get("live") is True
        with session() as sdb:
            rows = sdb.scalars(select(Event).where(Event.conversation_id == "conv_eph")).all()
        assert not rows
        assert not pushed          # no FCM for a word of comfort
    finally:
        ev.bus._subs.get("conv_eph", set()).discard(q)


# ---------------- 3. say-lines ----------------

def test_say_line_rules_are_true_or_silent():
    from app.agent.say import line_for
    assert line_for("Email padha", "email_check", {"error": "x"}) == ""          # errors are the chip's job
    assert line_for("Email padha", "email_check", {"items": [1, 2, 3]}) == "3 mails mile"
    assert line_for("Web search", "web_search", {"count": 5}) == "5 results mile"
    v = line_for("Video", "video_edit", {"url": "https://drive.google.com/file.mp4?x=1&token=y"})
    assert v == "Video taiyar — drive.google.com" and "token" not in v           # query string never shown
    assert line_for("Kuch", "misc", {"note": "no facts here"}) == ""             # no guess, no line
    assert line_for("Poster", "photo_banao", {"ok": True}) == "Poster ho gaya"


def test_feed_say_accumulates_and_kinds_say(env, monkeypatch):
    import app.livereply as lr
    from app.events import STREAM_KINDS
    assert "say" in STREAM_KINDS
    spy = _PubSpy()
    monkeypatch.setattr(lr, "bus", spy)
    lv = lr.Live("conv_say", "default")
    lv.feed_say("12 mails aaye")
    lv.feed_say("12 mails aaye")          # duplicate: not re-sent
    lv.feed_say("video ban raha hai")
    says = [c for c in spy.calls if c[1] == "say"]
    assert says[-1][2]["text"] == "12 mails aaye  ·  video ban raha hai"
    assert len(says) == 2
    for _ in range(5):
        lv.feed_say(f"line {_}")
    assert len(lv.sayq) == 3              # only the last three stay


# ---------------- 4. kaam_followup ----------------

@pytest.fixture()
def fu(env, monkeypatch):
    """kaamwatch ON, followup ON, one conversation, the model line stubbed, voice + notify spied."""
    monkeypatch.setenv("KAAM_WATCH", "true")
    monkeypatch.setenv("KAAM_FOLLOWUP", "true")
    from app.db import Conversation, session
    conv = "conv_fu"
    with session() as sdb:
        sdb.add(Conversation(id=conv, tenant_id="default", title="t"))
    notices = []
    monkeypatch.setattr(kf, "notify", lambda conv, text: notices.append((conv, text)))
    voices = []
    monkeypatch.setattr(kw, "_voice", lambda tenant, conv, say: voices.append(say))
    return {"conv": conv, "notices": notices, "voices": voices}


def _drain():
    async def go():
        for _ in range(6):
            await asyncio.sleep(0.02)
    run(go())


def tick_drain():
    """One worker tick + let every task it scheduled finish on the SAME loop (asyncio.run cancels stragglers)."""
    async def go():
        await kf.tick()
        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
    run(go())


def test_done_job_reports_in_her_voice(fu, monkeypatch):
    conv = fu["conv"]
    from app.config import get_settings as _gs
    monkeypatch.setattr(_gs(), "agent_wake_turns", False)   # v0.191: pins the one-shot FALLBACK path (auto-restored)
    async def fake_line(r, settings):
        return "Diwali reel taiyaar hai, link yahan hai."
    monkeypatch.setattr(kf, "_model_line", fake_line)
    kw.observe(conv, "video_job", {"id": "v1", "status": "done", "name": "Diwali reel", "url": "https://cdn.f.mp4/a.mp4"})
    from app.db import Message, session
    with session() as sdb:   # the dry kaamwatch line did NOT go out as a message
        msgs = sdb.scalars(select(Message).where(Message.conversation_id == conv)).all()
    assert not msgs
    tick_drain()
    assert fu["notices"] and "Diwali reel taiyaar hai" in fu["notices"][0][1]
    assert fu["voices"] and "Diwali reel" in fu["voices"][0]
    from app.kaam_followup import KaamFollowup
    with session() as sdb:
        row = sdb.scalars(select(KaamFollowup)).all()
    assert len(row) == 1 and row[0].status == "sent" and row[0].link == "https://cdn.f.mp4/a.mp4"


def test_model_failure_falls_back_to_the_honest_line(fu, monkeypatch):
    conv = fu["conv"]
    from app.config import get_settings as _gs
    monkeypatch.setattr(_gs(), "agent_wake_turns", False)   # v0.191: pins the one-shot FALLBACK path (auto-restored)
    async def dead_line(r, settings):
        return ""
    monkeypatch.setattr(kf, "_model_line", dead_line)
    kw.observe(conv, "video_job", {"id": "v2", "status": "done", "name": "Shaami ka video"})
    tick_drain()
    assert fu["notices"], "she is never left without the news"
    assert "✅" in fu["notices"][0][1] and "ho gaya" in fu["notices"][0][1]


def test_failed_job_asks_for_her_word(fu, monkeypatch):
    conv = fu["conv"]
    from app.config import get_settings as _gs
    monkeypatch.setattr(_gs(), "agent_wake_turns", False)   # v0.191: pins the one-shot FALLBACK path (auto-restored)
    async def dead_line(r, settings):
        return ""
    monkeypatch.setattr(kf, "_model_line", dead_line)
    kw.observe(conv, "video_job", {"id": "v3", "status": "failed", "name": "Ad reel", "error": "render crash"})
    tick_drain()
    assert fu["notices"] and "❌" in fu["notices"][0][1] and "ruk gaya" in fu["notices"][0][1]


def test_running_turn_postpones_the_report(fu, monkeypatch):
    import app.agent.santosh as s
    from app.kaam_followup import KaamFollowup
    from app.db import session
    conv = fu["conv"]
    from app.config import get_settings as _gs
    monkeypatch.setattr(_gs(), "agent_wake_turns", False)   # v0.191: pins the one-shot FALLBACK path (auto-restored)
    calls, notices = [], []
    async def fake_line(r, settings):
        calls.append(r.title)
        return f"{r.label} {r.title} taiyaar hai."
    monkeypatch.setattr(kf, "_model_line", fake_line)
    monkeypatch.setattr(kf, "notify", lambda conv, text: notices.append(text))
    kw.observe(conv, "video_job", {"id": "v4", "status": "done", "name": "Wait wala"})
    async def held():
        async with s._locks.setdefault(conv, __import__("asyncio").Lock()):
            await kf.tick()
            pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
    run(held())
    assert not calls and not notices
    with session() as sdb:
        row = sdb.scalars(select(KaamFollowup)).all()
    assert len(row) == 1 and row[0].status == "pending" and row[0].tries >= 1
    tick_drain()              # turn over now: the report goes
    assert notices and "Wait wala" in notices[0]


def _never(sent):
    async def fake(r, settings):
        sent.append("SHOULD NOT RUN")
        return f"{r.label} {r.title} ho gaya."
    return fake


def test_the_turns_own_reply_stops_the_duplicate(fu, monkeypatch):
    from app.db import Message, session
    conv = fu["conv"]
    monkeypatch.setattr(kf, "_model_line", _never([]))
    kw.observe(conv, "video_job", {"id": "v5", "status": "done", "name": "Pehle hi bata diya"})
    with session() as sdb:   # the turn's own reply already named the job + the result
        sdb.add(Message(conversation_id=conv, role="assistant", content=[{"type": "text", "text": "Pehle hi bata diya — video ban gayi hai."}],
                        display="Pehle hi bata diya — video ban gayi hai.", in_history=True))
    tick_drain()
    assert not fu["notices"]
    from app.kaam_followup import KaamFollowup
    with session() as sdb:
        row = sdb.scalars(select(KaamFollowup)).all()
    assert row[0].status == "skipped"


def test_enqueue_dedupes_same_job_and_state(fu):
    from app.kaam_followup import KaamFollowup
    from app.db import session
    conv = fu["conv"]
    job = {"key": "video_job:v9", "kind": "video_job", "label": "Video edit", "title": "Ek hi", "state": "done",
           "detail": "", "link": "", "pct": -1, "stage": "", "waiting_say": "", "push": False}
    assert kf.enqueue("default", conv, job) is True
    assert kf.enqueue("default", conv, job) is False
    from app.kaam_followup import KaamFollowup
    with session() as sdb:
        rows = sdb.scalars(select(KaamFollowup).where(KaamFollowup.key == "video_job:v9")).all()
    assert len(rows) == 1


# ---------------- version ----------------

def test_version():
    from app.config import get_settings
    from app.main import APP_VERSION
    assert APP_VERSION == "0.231.0"
    assert get_settings().agent_ack_after_s == 5.0
