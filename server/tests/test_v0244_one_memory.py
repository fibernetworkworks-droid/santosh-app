"""v0.244 PHASE 3A ONE MEMORY: the voice call and the quick lane read the chat's Phase 2 checkpoint, a cost cap
(CHAT_CONTEXT_MAX_TOKENS) moves the compaction line, the console's memory meter, the greeting with her avatar's name."""
import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.agent import set_client
from app.db import session
from tests.test_v0242_compact import SUMMARY, Model, _chat, _limit, cm  # noqa: F401  (fixture)

CON = Path(__file__).resolve().parents[1] / "app" / "static" / "console"


def _compacted(cm, n=12):  # noqa: F811
    c = _chat(n)
    set_client(Model())
    v = asyncio.run(cm.run(c, "default", "manual"))
    assert v and v["upto_id"]
    return c


# ------------------------------------------------------------------ 1. the call reads the checkpoint
def test_call_starts_from_the_chat_checkpoint(cm):  # noqa: F811
    from app import yaad
    c = _compacted(cm)
    with session() as s:   # a rolling summary exists too: the checkpoint wins, never both
        s.add(yaad.YaadSummary(conversation_id=c, tenant_id="default", upto_id=1, exchanges=10, text="- purana saar"))
    vb = yaad.voice_block("default", c)
    assert "IS CHAT KA SAAR" in vb and "Invoice_March_v3.pdf" in vb and "purana saar" not in vb
    recent = vb.split("Haal ki baatein", 1)[1]
    assert "kaam number 11 karo" in recent and "kaam number 2 karo" not in recent   # only what came AFTER it
    assert len(vb) <= yaad.CALL_MAX_WITH_CHECKPOINT + 200


def test_call_without_checkpoint_is_as_before(cm):  # noqa: F811
    from app import yaad
    c = _chat(6)
    with session() as s:
        s.add(yaad.YaadSummary(conversation_id=c, tenant_id="default", upto_id=1, exchanges=10, text="- purana saar"))
    vb = yaad.voice_block("default", c)
    assert "Purani baaton ka saar:\n- purana saar" in vb and "IS CHAT KA SAAR" not in vb


def test_big_checkpoint_never_pushes_out_the_rest(cm):  # noqa: F811
    from app import yaad
    c = _chat(12)
    set_client(Model(summary="S" * 7900))
    asyncio.run(cm.run(c, "default", "manual"))
    vb = yaad.voice_block("default", c)
    assert "Haal ki baatein" in vb and vb.count("S" * 100) <= yaad.CALL_CHECKPOINT_CHARS // 100


# ------------------------------------------------------------------ 2. the quick lane reads it too
def test_quick_reply_sees_the_checkpoint(cm, monkeypatch):  # noqa: F811
    from app.agent import quick
    c = _compacted(cm)
    seen = {}

    async def fake_ask(system, prompt):
        seen["prompt"] = prompt
        return "Haan, file Invoice_March_v3.pdf hai."
    monkeypatch.setattr(quick, "_ask", fake_ask)
    out = asyncio.run(quick.answer(c, "default", "kaunsi file thi?"))
    assert out and "CHAT KA SAAR" in seen["prompt"] and "Invoice_March_v3.pdf" in seen["prompt"]
    plain = _chat(3)
    asyncio.run(quick.answer(plain, "default", "kya chal raha hai?"))
    assert "CHAT KA SAAR" not in seen["prompt"]      # never compacted: no empty section


# ------------------------------------------------------------------ 3. the cost cap
def test_cost_cap_moves_the_compaction_line(cm, monkeypatch):  # noqa: F811
    from app.agent import context
    from app.config import get_settings
    assert context.budget("claude") == 150000            # 75% of 200k, no cap
    monkeypatch.setenv("CHAT_CONTEXT_MAX_TOKENS", "30000")
    get_settings.cache_clear()
    assert context.budget("claude") == 30000 and context.window("claude") == 40000
    c = _chat(40)
    est, _ = cm.estimate(c)
    monkeypatch.setenv("CHAT_CONTEXT_MAX_TOKENS", str(int(est * 0.9)))   # the model has room; the CAP does not
    get_settings.cache_clear()
    set_client(Model())
    v = asyncio.run(cm.before_turn(c, "default"))
    assert v and v["reason"] == "auto" and v["tokens_after"] < v["tokens_before"]


# ------------------------------------------------------------------ 4. the meter
def test_meter_reading_and_console(cm, monkeypatch):  # noqa: F811
    c = _chat(5)
    client = TestClient(__import__("app.main", fromlist=["app"]).app)
    r = client.get(f"/api/conversations/{c}/context").json()["context"]
    assert r["mode"] == "claude" and r["window"] == 200000 and "full" in r and r["percent"] >= 0
    html = (CON / "v2.html").read_text()
    js = (CON / "v2.js").read_text()
    assert 'id="cMeter"' in html
    assert "async function meter()" in js and "/context`" in js and "meter();               // v0.244" in js


# ------------------------------------------------------------------ 5. the greeting
def test_new_chat_greets_with_her_avatars_name(env):
    from app.avatar.models import Avatar
    from app.db import Message
    with session() as s:
        s.add(Avatar(tenant_id="default", name="Riya", gender="f"))
    client = TestClient(__import__("app.main", fromlist=["app"]).app)
    cid = client.post("/api/conversations").json()["id"]
    with session() as s:
        g = s.query(Message).filter(Message.conversation_id == cid).first()
    assert g.display.startswith("Namaskar! Main Riya hoon") and "Santosh" not in g.display
