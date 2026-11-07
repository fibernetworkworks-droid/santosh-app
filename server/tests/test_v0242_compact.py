"""v0.242 FULL CLAUDE MODE Phase 2: compact - one careful checkpoint summary when the chat is nearly full, prepared
in the background at 60%, switched in at 75%, built on the previous one, never holding secrets, never failing."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.agent import run_turn, set_client
from app.db import Event, session
from tests.test_v108_memory import add_exchange, conv

SUMMARY = ("1. LAKSHYA - March ke invoices bhejne hain\n2. USKE SHABD - \"Sharma ji ki file ka naam Invoice_March_v3.pdf "
           "rakhna\"\n4. KAAM HUA - file_0_0 bani\n7. ABHI - kaam number 55 chal raha tha")


@pytest.fixture()
def cm(env, monkeypatch):
    from app.agent import compact, context
    monkeypatch.setattr(context, "RATIO", {})
    monkeypatch.setattr(context, "LIMIT_SEEN", {})
    monkeypatch.setattr(context, "LAST", {})
    monkeypatch.setattr(compact, "FORCE", set())
    monkeypatch.setattr(compact, "_LOCKS", {})
    monkeypatch.setattr(compact, "STATS", {k: 0 for k in compact.STATS})
    return compact


def _limit(monkeypatch, n):
    monkeypatch.setenv("CHAT_CONTEXT_LIMIT_CLAUDE", str(int(n)))
    from app.config import get_settings
    get_settings.cache_clear()


class Model:
    """Scripted Claude: the checkpoint writer gets `summary`, the chat gets 'Ho gaya.'; every request is kept."""

    def __init__(self, summary=SUMMARY, chat_fail=0):
        self.summary, self.chat_fail = summary, chat_fail
        self.chat, self.writer = [], []
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kw):
        sysm = kw.get("system")
        if isinstance(sysm, str) and sysm.startswith("You write the CHECKPOINT"):
            self.writer.append(kw["messages"][0]["content"][0]["text"])
            if isinstance(self.summary, Exception):
                raise self.summary
            return SimpleNamespace(content=[{"type": "text", "text": self.summary}], stop_reason="end_turn")
        self.chat.append(json.loads(json.dumps(kw["messages"], default=str)))
        if self.chat_fail:
            self.chat_fail -= 1
            raise RuntimeError("Error code: 400 - prompt is too long: 250000 tokens > 200000 maximum")
        return SimpleNamespace(content=[{"type": "text", "text": "Ho gaya."}], stop_reason="end_turn")


def _chat(n, steps=1, big=1200):
    c = conv()
    for i in range(n):
        add_exchange(c, i, steps=steps, big=big)
    return c


def _events(c, kind="compact"):
    with session() as s:
        return [e.payload for e in s.scalars(select(Event).where(Event.conversation_id == c, Event.kind == kind)).all()]


# ------------------------------------------------------------------ the checkpoint
def test_full_chat_compacts_before_the_turn_and_keeps_the_newest_word_for_word(cm, monkeypatch):
    c = _chat(60)
    est, _ = cm.estimate(c)
    _limit(monkeypatch, est / 0.9)                      # 90% full: over the 75% line
    m = Model()
    set_client(m)
    out = asyncio.run(run_turn(c, "ab Sharma ji ko bhejo", tenant_id="default"))
    assert out == "Ho gaya." and len(m.writer) >= 1
    a = cm.active(c)
    assert a and a["reason"] == "auto" and "Invoice_March_v3.pdf" in a["summary"] and a["tokens_after"] < a["tokens_before"]
    sent = m.chat[0]
    first = sent[0]["content"] if isinstance(sent[0]["content"], str) else sent[0]["content"][0]["text"]
    assert first.startswith(cm.OPEN) and "Invoice_March_v3.pdf" in first
    words = json.dumps(sent, ensure_ascii=False)
    for i in range(56, 60):                             # the newest 4 exchanges stay word for word
        assert f"kaam number {i} karo" in words and f"file_{i}_0" in words
    assert "kaam number 3 karo" not in words            # older ones live in the summary now
    assert "ab Sharma ji ko bhejo" in words
    ev = _events(c)
    assert len(ev) == 1 and ev[0]["exchanges"] == 56 and ev[0]["before_pct"] > ev[0]["after_pct"]
    from app.agent import context
    assert context.LAST[c]["form"] == "full"            # after compaction it fits again: no safety net


def test_history_after_a_checkpoint(cm, monkeypatch):
    from app import yaad
    c = _chat(20)
    set_client(Model())
    v = asyncio.run(cm.run(c, "default", "manual"))
    assert v and v["exchanges"] == 16
    h = yaad.full_history(c)
    assert h[0]["content"].startswith(cm.OPEN)
    users = [m["content"] for m in h[1:] if m["role"] == "user" and isinstance(m["content"], str)]
    assert users == [f"kaam number {i} karo" for i in range(16, 20)]
    cm._LOCKS.clear()                                   # a pm2 restart: the checkpoint comes from the database
    assert yaad.full_history(c)[0]["content"].startswith(cm.OPEN)


def test_second_checkpoint_builds_on_the_first(cm, monkeypatch):
    c = _chat(12)
    m = Model()
    set_client(m)
    asyncio.run(cm.run(c, "default", "manual"))
    for i in range(12, 24):
        add_exchange(c, i, steps=1)
    m.summary = SUMMARY + "\n6. BAAKI - April wale bhi"
    v = asyncio.run(cm.run(c, "default", "manual"))
    assert "PICHHLA SAAR:\n" + SUMMARY in m.writer[-1]  # the first summary is folded forward, never lost
    assert v["exchanges"] == 20 and "April" in v["summary"]
    assert len(cm.recent(c)) == 2 and cm.recent(c)[1]["status"] == "replaced"


def test_draft_at_60_percent_is_switched_in_at_75_without_a_wait(cm, monkeypatch):
    c = _chat(30)
    est, _ = cm.estimate(c)
    _limit(monkeypatch, est / 0.65)                     # 65%: prepare only
    m = Model()
    set_client(m)

    async def go():
        assert await cm.before_turn(c, "default") is None
        await cm.drain()
    asyncio.run(go())
    assert len(m.writer) == 1 and cm.active(c) is None and cm.STATS["prepared"] == 1
    _limit(monkeypatch, est / 0.85)                     # now over the line: the draft is used, no new writing
    v = asyncio.run(cm.before_turn(c, "default"))
    assert v and v["status"] == "active" and len(m.writer) == 1 and cm.STATS["draft_used"] == 1


# ------------------------------------------------------------------ safety
def test_summary_never_keeps_secrets(cm):
    c = _chat(8)
    set_client(Model(summary=SUMMARY + "\nOTP 482913 diya tha, card 4111 1111 1111 1111, account 123456789012"))
    v = asyncio.run(cm.run(c, "default", "manual"))
    assert "482913" not in v["summary"] and "4111" not in v["summary"] and "123456789012" not in v["summary"]
    assert "Invoice_March_v3.pdf" in v["summary"]


def test_no_model_still_compacts_with_plain_lines(cm):
    c = _chat(10)
    set_client(Model(summary=RuntimeError("down")))
    v = asyncio.run(cm.run(c, "default", "auto"))
    assert v and v["model"] == "plain" and "kaam number 0 karo" in v["summary"] and cm.STATS["fallback"] == 1


def test_too_long_marks_the_chat_and_the_next_turn_compacts_first(cm, monkeypatch):
    c = _chat(20)
    m = Model(chat_fail=1)
    set_client(m)
    assert asyncio.run(run_turn(c, "aage badho", tenant_id="default")) == "Ho gaya."
    assert c in cm.FORCE and cm.active(c) is None
    asyncio.run(run_turn(c, "ek aur", tenant_id="default"))
    a = cm.active(c)
    assert a and a["reason"] == "overflow" and c not in cm.FORCE


def test_off_switches(cm, monkeypatch):
    c = _chat(30)
    est, _ = cm.estimate(c)
    _limit(monkeypatch, est / 0.9)
    set_client(Model())
    monkeypatch.setenv("CHAT_COMPACT", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    assert asyncio.run(cm.before_turn(c, "default")) is None and cm.active(c) is None
    monkeypatch.setenv("CHAT_COMPACT", "true")
    monkeypatch.setenv("CHAT_CONTEXT", "hoola")
    get_settings.cache_clear()
    assert asyncio.run(cm.before_turn(c, "default")) is None and cm.active(c) is None


def test_safety_net_never_shortens_the_checkpoint(cm, monkeypatch):
    _limit(monkeypatch, 20000)
    from app.agent import context
    head = cm.OPEN + "S" * 6000
    hist = [{"role": "user", "content": [{"type": "text", "text": head}, {"type": "text", "text": "pehli baat"}]}]
    for i in range(80):
        hist += [{"role": "assistant", "content": [{"type": "text", "text": "theek " + "z" * 600}]},
                 {"role": "user", "content": f"baat {i} " + "y" * 600}]
    out, form = context.fit(hist, "sys", [], "claude", "", turn_start=len(hist) - 1)
    assert form == "net"
    assert out[0]["role"] == "user" and out[0]["content"] == head      # whole, first, never cut
    sq = context.squeeze(hist, "", turn_start=len(hist) - 1)
    assert sq[0]["content"] == head


# ------------------------------------------------------------------ by hand
def test_manual_compact_endpoints(cm, monkeypatch):
    client = TestClient(__import__("app.main", fromlist=["app"]).app)
    small = _chat(3)
    set_client(Model())
    r = client.post(f"/api/conversations/{small}/compact").json()
    assert r["compact"] is None and "chhoti" in r["say"]
    c = _chat(12)
    r = client.post(f"/api/conversations/{c}/compact").json()
    assert r["compact"]["reason"] == "manual" and r["compact"]["exchanges"] == 8
    g = client.get(f"/api/conversations/{c}/compact").json()
    assert g["active"]["summary"].startswith("1. LAKSHYA") and g["health"]["stats"]["manual"] == 1
    from app.agent import santosh
    monkeypatch.setitem(santosh._locks, c, SimpleNamespace(locked=lambda: True))
    assert client.post(f"/api/conversations/{c}/compact").status_code == 409
