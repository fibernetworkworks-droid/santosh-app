"""v0.108 Hoola ki yaad: 40+ exchanges (not messages), compressed older steps, work diary + recall in the current message
only, rolling summary, auto facts with the privacy filter, puri yaad search, the same memory in calls."""
import asyncio
import json
from types import SimpleNamespace

import pytest

from app.agent import run_turn, set_client
from app.db import Conversation, Message, MemoryFact, session


class Model:
    def __init__(self, script=None):
        self.script, self.sent = list(script or []), []
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kw):
        self.sent.append(json.loads(json.dumps({"system": kw.get("system"), "messages": kw["messages"]}, default=str)))
        blocks = self.script.pop(0) if self.script else [{"type": "text", "text": "Ho gaya."}]
        stop = "tool_use" if any(b["type"] == "tool_use" for b in blocks) else "end_turn"
        return SimpleNamespace(content=blocks, stop_reason=stop)


def conv():
    with session() as s:
        c = Conversation(tenant_id="default")
        s.add(c)
        s.flush()
        return c.id


def add_exchange(c, i, steps=0, big=0):
    """One saved exchange: her words, optional tool steps, Hoola's reply (like the chat loop saves them)."""
    with session() as s:
        s.add(Message(conversation_id=c, role="user", content=f"kaam number {i} karo", display=f"kaam number {i} karo"))
        for k in range(steps):
            tid = f"tu_{i}_{k}"
            s.add(Message(conversation_id=c, role="assistant",
                          content=[{"type": "tool_use", "id": tid, "name": "pc_search", "input": {"query": f"file{i}"}}]))
            body = {"status": "ok", "file_id": f"file_{i}_{k}", "count": k + 1, "junk": "x" * big}
            s.add(Message(conversation_id=c, role="user",
                          content=[{"type": "tool_result", "tool_use_id": tid, "content": json.dumps(body)}]))
        s.add(Message(conversation_id=c, role="assistant", content=[{"type": "text", "text": f"Kaam {i} ho gaya."}],
                      display=f"Kaam {i} ho gaya."))


def test_history_keeps_40_plus_exchanges_and_compresses_older_steps(env, monkeypatch):
    monkeypatch.setenv("CHAT_CONTEXT", "hoola")   # v0.237 the v0.108 window is the hoola mode (claude = whole chat)
    from app.config import get_settings
    get_settings.cache_clear()
    from app import yaad
    from app.agent.santosh import _load_history
    c = conv()
    for i in range(63):
        add_exchange(c, i, steps=3 if i % 2 == 0 else 0)
    h = _load_history(c)
    users = [m for m in h if m["role"] == "user" and isinstance(m["content"], str)]
    assert 40 <= len(users) <= 49
    assert users[0]["content"] == "kaam number 20 karo"        # 63 -> start at 20 (blocks of 10)
    assert users[-1]["content"] == "kaam number 62 karo"
    old = next(m for m in h if m["role"] == "assistant" and "⟦kiya:" in json.dumps(m["content"], ensure_ascii=False))
    txt = old["content"][0]["text"]
    assert "pc_search(query=file20) → status=ok, file_id=file_20_0, count=1" in txt and "Kaam 20 ho gaya." in txt
    assert any(b.get("type") == "tool_use" for m in h[-8:] if isinstance(m["content"], list) for b in m["content"])
    # one more exchange: the window start does not move (cache-friendly), the oldest is still number 20
    add_exchange(c, 63)
    h2 = _load_history(c)
    assert next(m for m in h2 if m["role"] == "user")["content"] == "kaam number 20 karo"
    assert yaad.window_start_id(c) > 0
    # a huge job: only the current exchange stays full, older ones are compressed
    add_exchange(c, 64, steps=4, big=30000)
    add_exchange(c, 65, steps=1)
    h3 = _load_history(c)
    assert not any("x" * 1000 in json.dumps(m["content"]) for m in h3[:-3])


def test_gist_and_one_line_keep_the_facts():
    from app import yaad
    g = yaad.gist(json.dumps({"status": "saved", "saved_path": "C:/Inbox/a.xlsx", "count": 4, "other": "ignore"}))
    assert "status=saved" in g and "saved_path=C:/Inbox/a.xlsx" in g and "count=4" in g
    assert yaad.gist("Portal said: session expired", True).startswith("✗ ")


def test_turn_gets_diary_and_recall_without_saving_it(env):
    from app.agent.pakka import TaskRun
    c = conv()
    with session() as s:
        s.add(TaskRun(tenant_id="default", request="MAC wali sheet ko nayi sheet se milao", outcome="partial", steps=6,
                      left="Haan ka intezaar"))
    m = Model([[{"type": "text", "text": "Haan, MAC wali sheet ka kaam baaki hai."}]])
    set_client(m)
    try:
        out = asyncio.run(run_turn(c, "kal wala kaam kahan tak hua?"))
    finally:
        set_client(None)
    assert "baaki" in out
    last_user = m.sent[0]["messages"][-1]
    blob = json.dumps(last_user, ensure_ascii=False)
    assert "[Hoola ki yaad" in blob and "MAC wali sheet" in blob and "Haan ka intezaar" in blob
    with session() as s:
        saved = [r.content for r in s.query(Message).filter(Message.conversation_id == c).all()]
    assert not any("Hoola ki yaad" in json.dumps(x, ensure_ascii=False) for x in saved)


def test_rolling_summary_for_exchanges_outside_the_window(env):
    from app import yaad
    c = conv()
    for i in range(55):
        add_exchange(c, i, steps=1)
    changed = asyncio.run(yaad.refresh_summary("default", c))
    assert changed
    summ = yaad.summary_block(c)
    assert "kaam number 0 karo" in summ and "file_id=file_0_0" in summ
    assert not asyncio.run(yaad.refresh_summary("default", c))      # nothing new: no change
    m = Model([[{"type": "text", "text": "Theek."}]])
    set_client(m)
    try:
        asyncio.run(run_turn(c, "aur kya baaki hai"))
    finally:
        set_client(None)
    assert "PURANI BAATEIN" in json.dumps(m.sent[0]["system"], ensure_ascii=False)


def test_privacy_filter_for_facts():
    from app import yaad
    ok = ["Riya is her daughter; class 5 at DPS", "Her shop Patil Steel is in Akola", "Always send quotations as PDF"]
    bad = ["Her OTP is 482913", "Her salary is Rs 45,000", "She has diabetes and takes medicine",
           "Aadhaar 2345 6789 0124", "Her bank account no 123456789012", "Her caste is X", "Balance 20k in SBI"]
    assert all(yaad.fact_ok(t) == "" for t in ok)
    assert all(yaad.fact_ok(t) != "" for t in bad)


def test_auto_facts_saved_deduped_and_chip(env, monkeypatch):
    from app import yaad
    monkeypatch.setenv("MEMORY_AUTO", "true")
    from app.config import get_settings
    get_settings.cache_clear()

    async def fake_ask(system, text):
        return json.dumps({"facts": ["Riya is her daughter; she studies at DPS Akola", "Her salary is Rs 40,000"]})
    monkeypatch.setattr(yaad, "_ask", fake_ask)
    c = conv()
    yaad._LAST_EXTRACT.clear()
    saved = asyncio.run(yaad.extract_facts("default", c, "meri beti Riya DPS Akola mein padhti hai", "Achha!"))
    assert [f["text"] for f in saved] == ["Riya is her daughter; she studies at DPS Akola"]
    with session() as s:
        row = s.query(MemoryFact).one()
        assert row.source == "auto"
    from app.db import Event
    with session() as s:
        ev = s.query(Event).filter(Event.conversation_id == c, Event.kind == "memory_saved").one()
        assert ev.payload["facts"][0]["text"].startswith("Riya")
    yaad._LAST_EXTRACT.clear()
    again = asyncio.run(yaad.extract_facts("default", c, "meri beti Riya DPS Akola mein padhti hai yaad hai", "Haan"))
    assert again == []                       # same fact: not saved twice
    yaad._LAST_EXTRACT.clear()
    assert asyncio.run(yaad.extract_facts("default", c, "ok", "")) == []     # too short: no model call


def test_relevant_facts_by_meaning_beyond_the_newest(env):
    from app import yaad
    with session() as s:
        s.add(MemoryFact(tenant_id="default", text="Riya ki school DPS Akola hai, class teacher Mrs Rao"))
        for i in range(60):
            s.add(MemoryFact(tenant_id="default", text=f"Supplier number {i} ka order har mahine"))
    with session() as s:
        newest = {f.id for f in s.query(MemoryFact).order_by(MemoryFact.id.desc()).limit(40)}
    got = yaad.relevant_facts("default", "Riya ki school fees kab bharni hai", newest)
    assert any("Mrs Rao" in t for _, t in got)


def test_puri_yaad_search_finds_index_and_raw_tool_output(env):
    from app import yaad
    c = conv()
    add_exchange(c, 1, steps=1)
    with session() as s:
        s.add(Message(conversation_id=c, role="user", content=[{"type": "tool_result", "tool_use_id": "z",
                                                                "content": "{\"order_ref\": \"OD4471XQ\"}"}]))
    yaad.index_recent("default", c, 5)
    hits = yaad.search("default", "kaam number 1")
    assert hits and "kaam number 1" in hits[0]["text"]
    raw = yaad.search("default", "OD4471XQ")
    assert any("OD4471XQ" in h["text"] for h in raw)


def test_voice_call_gets_the_same_memory(env):
    from app import voice, yaad
    c = conv()
    for i in range(5):
        add_exchange(c, i, steps=1)
    blk = yaad.voice_block("default", c)
    assert "HOOLA KI YAAD" in blk and "kaam number 4 karo" in blk and "⟦" not in blk.split("kiya:")[0][-5:]
    call = SimpleNamespace(recent=[("u" * 300, "r" * 300)] * 20)
    seed = voice.Call._reseed(call, False)
    assert len(seed) > 3000 and "HOOLA KI YAAD" in seed
    assert voice.Call._reseed(call, True) is None


def test_jaanch_reports_memory_and_voice_settings(env, monkeypatch):
    from app import jaanch, voice
    r = asyncio.run(jaanch._memory("default"))
    assert r["id"] == "memory" and "yaadein" in r["detail"]
    monkeypatch.setattr(voice, "UNSUPPORTED", {"session_resumption"})
    v = asyncio.run(jaanch._voice_settings())
    assert v["ok"] is False and "session_resumption" in v["detail"]
    monkeypatch.setattr(voice, "UNSUPPORTED", set())
    assert asyncio.run(jaanch._voice_settings())["ok"] is True


def test_memory_api_delete_and_search(env):
    from fastapi.testclient import TestClient
    from app.main import app
    with session() as s:
        s.add(MemoryFact(tenant_id="default", text="Her office is in Akola", source="auto"))
    cl = TestClient(app)
    h = {}
    got = cl.get("/api/memory", headers=h).json()
    fid = got["facts"][0]["id"]
    assert got["facts"][0]["auto"] is True
    after = cl.delete(f"/api/memory/{fid}", headers=h).json()
    assert after["facts"] == []
    assert "health" in cl.get("/api/yaad", headers=h).json()


def test_meaning_search_with_stored_vectors(env, monkeypatch):
    """With an embedding model: vectors are stored in the background and searched with numpy."""
    import time
    from app import semantic, yaad

    def vec(t):
        v = [0.0] * 32
        for w in t.lower().split():
            v[hash(w.strip(".,:")) % 32] += 1.0
        return v
    monkeypatch.setattr(semantic, "_EMB", object())
    monkeypatch.setattr(semantic, "_vecs", lambda texts: [vec(t) for t in texts])
    yaad.add_item("default", "job", "Router ka quotation Kulkarni ko bheja", "c1", "j1")
    yaad.add_item("default", "job", "Bijli ka bill bhar diya", "c1", "j2")
    from app.db import session as _s
    end = time.time() + 5
    while time.time() < end:
        with _s() as s:
            if all(r.vec for r in s.query(yaad.YaadItem).all()):
                break
        time.sleep(0.05)
    hits = yaad.search("default", "Kulkarni quotation", words=False)
    assert hits and hits[0]["ref"] == "j1" and hits[0]["score"] > 0.4
    monkeypatch.setattr(semantic, "_EMB", None)
