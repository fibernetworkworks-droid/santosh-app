"""v0.603 YAAD SACH - her memory keeps its three promises (owner: "NOW LETS WORK ON HOOLA AI CONTEXT / MEMORY" -> GO).

Found by probing the real code, not by reading it:
1. INCOGNITO SACH - an incognito chat's ask, tool rows and an observation reached the Coder vault (the capture
   boundary never asked) and could ride the primer of her OTHER chats; the knowledge graph accepted writes there too.
2. NAYA PURANA HATAYE - 'godown Bhosari' then 'godown ab Chakan': both facts rode every prompt side by side (or, with
   meaning search on, the update could be dropped as a 'duplicate' and the old value won).
3. BHOOL JAO HAR JAGAH - forgetting a fact deleted one row; the copies in the Coder vault, the knowledge graph and her
   'Mere baare mein' page stayed.
"""
from __future__ import annotations

import asyncio
import json

from app.coder import capture, observer, store
from app.db import Conversation, MemoryFact, session

from tests.test_v0473_hoola_coder import _obs_xml, _run, _settings, cod  # noqa: F401  (fixture)

T = "default"


def _chat(cid: str, incognito: bool = False) -> str:
    with session() as s:
        s.add(Conversation(id=cid, tenant_id=T, incognito=incognito))
    return cid


def _facts() -> list[str]:
    with session() as s:
        return [f.text for f in s.query(MemoryFact).filter(MemoryFact.tenant_id == T).order_by(MemoryFact.id)]


# ---------------------------------------------------------------- 1. incognito
def test_incognito_chat_leaves_nothing_in_the_coder_vault(cod):
    sec = _chat("conv_sec", incognito=True)
    pub = _chat("conv_pub")

    async def brain(system, user, settings):
        return _obs_xml(title="Riya ki school fees ka plan")
    observer._call_brain = brain
    capture.turn_prompt(T, sec, "meri beti Riya ki school fees ka plan")
    capture.tool_observed(T, sec, "web_search", {"q": "DPS fees"}, "fees 1.2 lakh", True, 9, "t1", "owner")
    capture.session_started(T, sec, "chat")
    assert capture.save_memory(T, sec, "Riya ki fees ka plan yaad rakhna") is None
    capture.turn_prompt(T, pub, "godown ka stock check karo")                     # a normal chat is still captured
    _run(observer.tick(_settings()))
    with store.db() as c:
        assert c.execute("SELECT COUNT(*) FROM prompts WHERE conv=?", (sec,)).fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM tool_uses WHERE conv=?", (sec,)).fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM prompts WHERE conv=?", (pub,)).fetchone()[0] == 1
    assert store.session_row(sec) is None
    assert not any("Riya" in r["title"] for r in store.recent_observations(T))


def test_old_incognito_traces_are_swept_and_late_events_dropped(cod):
    sec = _chat("conv_old_sec", incognito=True)
    keep = _chat("conv_keep")
    # what a pre-v0.603 server wrote: words, a tool row, an observation and a spooled event
    store.note_prompt(sec, "Riya ki fees ka secret plan")
    store.note_tool_use(sec, T, "web_search", "q", True, 5, "fees 1.2 lakh", "t1")
    store.store_observation(sec, T, {"type": "discovery", "title": "Riya fees plan secret", "facts": [],
                                     "narrative": "x", "concepts": []})
    store.store_observation(keep, T, {"type": "discovery", "title": "Godown stock counted", "facts": [],
                                      "narrative": "y", "concepts": []})
    from app.coder import spool
    spool.spool_event("observation", {"conv": sec, "tenant": T, "tool": "x", "args": {}, "result": "r",
                                      "ok": True, "ms": 1, "turn_id": "", "actor": "", "at": "", "seq": 1})

    async def brain(system, user, settings):
        return _obs_xml(title="Riya leaked again")
    observer._call_brain = brain
    _run(observer.tick(_settings()))
    titles = [r["title"] for r in store.recent_observations(T)]
    assert "Godown stock counted" in titles
    assert not any("Riya" in t for t in titles)
    with store.db() as c:
        assert c.execute("SELECT COUNT(*) FROM prompts WHERE conv=?", (sec,)).fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM tool_uses WHERE conv=?", (sec,)).fetchone()[0] == 0
    assert not spool.drain()                     # the late event was consumed unread, not left to retry


def test_incognito_chat_cannot_write_the_knowledge_graph(env):
    from app.agent import sandarbh_tools as S
    from app.agent.tools import Ctx
    sec, pub = _chat("conv_kg_sec", incognito=True), _chat("conv_kg_pub")
    out = asyncio.run(S.kgmemory(Ctx(tenant_id=T, conversation_id=sec), "create",
                                 entities=[{"name": "Riya", "type": "person"}]))
    assert out["ok"] is False and "incognito" in json.dumps(out)
    ok = asyncio.run(S.kgmemory(Ctx(tenant_id=T, conversation_id=pub), "create",
                                entities=[{"name": "Riya", "type": "person"}]))
    assert ok["ok"] is True
    read = asyncio.run(S.kgmemory(Ctx(tenant_id=T, conversation_id=sec), "read"))   # reading her graph is fine
    assert read["ok"] is True and "Riya" in json.dumps(read)


# ---------------------------------------------------------------- 2. an update replaces the old fact
def test_update_replaces_the_outdated_fact(env):
    from app import yaad
    from app.life import context_block
    old = yaad.save_fact(T, "Godown ka pata Plot 44, Bhosari MIDC hai", "auto")
    new = yaad.save_fact(T, "Godown ka pata ab Plot 12, Chakan MIDC hai", "auto", replaces=[old["id"]])
    assert new["id"] and new["replaced"] == ["Godown ka pata Plot 44, Bhosari MIDC hai"]
    assert _facts() == ["Godown ka pata ab Plot 12, Chakan MIDC hai"]
    blk = context_block(T)
    assert "Chakan" in blk and "Bhosari" not in blk


def test_an_update_that_reads_like_the_old_fact_is_not_dropped_as_a_duplicate(env):
    from app import yaad
    old = yaad.save_fact(T, "Her city is Pune", "auto")
    assert yaad.save_fact(T, "Her city is Pune now", "auto") is None             # a true duplicate stays refused
    got = yaad.save_fact(T, "Her city is Mumbai now", "auto", replaces=[old["id"]])
    assert got["id"] and _facts() == ["Her city is Mumbai now"]


def test_a_pinned_fact_is_never_retired_by_an_update(env):
    # v0.661 YAAD SAHI: still never RETIRED - her pinned fact is updated IN PLACE and stays pinned (before, the old
    # value stayed beside the new one under 'ALWAYS keep in mind')
    from app import life, yaad
    pin = yaad.save_fact(T, "Reports hamesha Marathi mein banana", "auto")
    life.pin_fact(T, pin["id"], True)
    got = yaad.save_fact(T, "Reports ab English mein banana", "auto", replaces=[pin["id"]])
    assert got["id"] == pin["id"] and got["pinned"] and got["replaced"] == ["Reports hamesha Marathi mein banana"]
    assert _facts().count("Reports ab English mein banana") == 1
    assert "Reports hamesha Marathi mein banana" not in _facts()


def test_extractor_update_retires_only_a_fact_it_was_shown(env, monkeypatch):
    from app import yaad
    from app.config import get_settings
    monkeypatch.setenv("MEMORY_AUTO", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(yaad, "_LAST_EXTRACT", {})
    c = _chat("conv_up")
    old = yaad.save_fact(T, "Godown ka pata Plot 44, Bhosari MIDC hai", "auto")
    other = yaad.save_fact(T, "Riya is her daughter; class 5 at DPS", "auto")
    seen = {}

    async def fake_ask(system, text):
        seen["prompt"] = text
        return json.dumps({"facts": [{"text": "Godown ab Plot 12, Chakan MIDC mein hai",
                                      "replaces": [old["id"], other["id"], 99999]}]})
    monkeypatch.setattr(yaad, "_ask", fake_ask)
    events = []
    from app.events import bus
    monkeypatch.setattr(bus, "publish", lambda conv, kind, payload: events.append((kind, payload)))
    saved = asyncio.run(yaad.extract_facts(T, c, "Godown ab Plot 12, Chakan MIDC mein shift ho gaya hai", "Theek hai"))
    assert f"[{old['id']}]" in seen["prompt"]                                   # the model sees ids
    facts = _facts()
    assert "Godown ab Plot 12, Chakan MIDC mein hai" in facts
    assert "Godown ka pata Plot 44, Bhosari MIDC hai" not in facts
    if f"[{other['id']}]" not in seen["prompt"]:                                # never shown -> never retired
        assert "Riya is her daughter; class 5 at DPS" in facts
    assert saved and saved[0]["replaced"]
    say = [p["say"] for k, p in events if k == "memory_saved"][0]
    assert "purana hataya" in say and "Bhosari" in say


def test_plain_string_facts_still_parse(env):
    from app import yaad
    items = yaad._parse_fact_items('{"facts": ["Riya is her daughter", {"text": "Godown in Chakan now", "replaces": [3]}]}')
    assert items == [{"text": "Riya is her daughter", "replaces": []},
                     {"text": "Godown in Chakan now", "replaces": [3]}]
    assert yaad._parse_facts('{"facts": ["Riya is her daughter"]}') == ["Riya is her daughter"]


def test_remember_tool_can_replace_an_old_fact(env):
    from app import yaad
    from app.agent import life_tools
    from app.agent.tools import Ctx
    old = yaad.save_fact(T, "Supplier Kapoor Steels Bhosari mein hai", "user")
    out = asyncio.run(life_tools.remember(Ctx(tenant_id=T, conversation_id=_chat("conv_rem")),
                                          "Supplier Kapoor Steels ab Chakan mein hai", replaces=old["id"]))
    assert out["saved"] and out["replaced"] == "Supplier Kapoor Steels Bhosari mein hai"
    assert _facts() == ["Supplier Kapoor Steels ab Chakan mein hai"]


# ---------------------------------------------------------------- 3. forget everywhere
def test_carries_needs_the_facts_own_words():
    from app.yaad import carries
    assert carries("Godown Plot 44 Bhosari MIDC", "KAAM: godown at Plot 44, Bhosari MIDC (Pune)")
    assert not carries("Godown Plot 44 Bhosari MIDC", "Riya is her daughter")
    assert not carries("hai", "hai hai hai")                                    # too few content words to match


def test_forget_removes_the_fact_from_every_memory(cod):
    from app import aboutme, yaad
    from app.agent import life_tools, sandarbh_tools as S
    from app.agent.tools import Ctx
    pub = _chat("conv_forget")
    ctx = Ctx(tenant_id=T, conversation_id=pub)
    f = yaad.save_fact(T, "Godown ka pata Plot 44 Bhosari MIDC hai", "user")
    store.store_observation(pub, T, {"type": "discovery", "title": "Godown at Plot 44 Bhosari MIDC",
                                     "facts": [], "narrative": "stock moved", "concepts": []})
    store.store_observation(pub, T, {"type": "discovery", "title": "Riya school DPS class 5",
                                     "facts": [], "narrative": "", "concepts": []})
    asyncio.run(S.kgmemory(ctx, "create", entities=[{"name": "Godown", "type": "place"}]))
    asyncio.run(S.kgmemory(ctx, "observe", observations=[{"entity": "Godown",
                                                          "contents": ["Plot 44 Bhosari MIDC", "Has 3 loaders"]}]))
    aboutme.ensure_table()
    with session() as s:
        s.add(aboutme.AboutMe(tenant_id=T, text="KAAM: bakery\nGodown Plot 44 Bhosari MIDC\nLOG: Riya beti", by="hoola"))
    out = asyncio.run(life_tools.forget(ctx, f["id"]))
    assert out["forgotten"] and out["also_removed"]["coder"] == 1 and out["also_removed"]["kg"] == 1
    assert out["also_removed"]["about_me"] == 1
    titles = [r["title"] for r in store.recent_observations(T)]
    assert titles == ["Riya school DPS class 5"]                                 # only the copy went
    graph = json.dumps(asyncio.run(S.kgmemory(ctx, "read")), ensure_ascii=False)
    assert "Bhosari" not in graph and "Has 3 loaders" in graph
    page = aboutme.get(T)["text"]
    assert "Bhosari" not in page and "bakery" in page and "Riya" in page


def test_forget_from_the_memory_screen_also_cleans_everywhere(env):
    from fastapi.testclient import TestClient
    from app import aboutme, yaad
    from app.main import app
    f = yaad.save_fact(T, "Godown ka pata Plot 44 Bhosari MIDC hai", "user")
    aboutme.ensure_table()
    with session() as s:
        s.add(aboutme.AboutMe(tenant_id=T, text="Godown Plot 44 Bhosari MIDC\nKAAM: bakery", by="hoola"))
    with TestClient(app) as cl:
        from app.config import get_settings
        key = get_settings().api_key
        r = cl.delete(f"/api/memory/{f['id']}", headers={"Authorization": f"Bearer {key}"} if key else {})
    assert r.status_code == 200
    assert "Bhosari" not in aboutme.get(T)["text"]


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.894.0"
