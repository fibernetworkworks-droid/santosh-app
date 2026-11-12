"""v0.605 EK YAAD + JUST IN TIME (owner: "go 1 and 2" after the Claude vs Hoola memory comparison).

1. ONE memory door - Claude keeps one memory per scope; Hoola had six stores, each with its own search, view and
   forget. memory.search_all / everything / reset_all are now the one door (stores stay where they are).
2. JUST IN TIME - Anthropic's context guidance ('the smallest set of high-signal tokens'; Claude looks old chats up
   with a tool call): a 'maybe related' old chat no longer rides every message, and the system prompt carries 15
   newest facts instead of 40 - the rest is one yaad_khojo call away, and that tool is now always in view.
"""
from __future__ import annotations

import asyncio
import json

from app.db import Conversation, MemoryFact, session

from tests.test_v0473_hoola_coder import cod  # noqa: F401  (fixture: coder vault on for this test)

T = "default"


def _chat(cid: str, incognito: bool = False, project: str | None = None) -> str:
    with session() as s:
        s.add(Conversation(id=cid, tenant_id=T, incognito=incognito, project_id=project))
    return cid


def _world():
    """One fact of each store about the same godown, in a normal chat."""
    from app import aboutme, yaad
    from app.agent import sandarbh_tools as S
    from app.agent.tools import Ctx
    from app.coder import store
    c = _chat("conv_main")
    yaad.save_fact(T, "Godown ka pata Plot 44 Bhosari MIDC hai", "user")
    yaad.add_item(T, "decision", "Godown Bhosari se 200 boxes Mehta Traders ko bheje", c)
    store.store_observation(c, T, {"type": "discovery", "title": "Godown Bhosari stock sheet updated",
                                   "facts": [], "narrative": "200 boxes left", "concepts": []})
    ctx = Ctx(tenant_id=T, conversation_id=c)
    asyncio.run(S.kgmemory(ctx, "create", entities=[{"name": "Godown", "type": "place"}]))
    asyncio.run(S.kgmemory(ctx, "observe", observations=[{"entity": "Godown", "contents": ["Bhosari MIDC, 3 loaders"]}]))
    aboutme.ensure_table()
    with session() as s:
        s.add(aboutme.AboutMe(tenant_id=T, text="KAAM: bakery\nGodown Bhosari MIDC mein hai", by="hoola"))
    return c


# ---------------------------------------------------------------- 1. the one door
def test_one_search_reaches_every_store_and_labels_it(cod):
    from app import memory
    c = _world()
    res = memory.search_all(T, c, "godown Bhosari")
    got = {h["source"] for h in res["hits"]}
    assert got == {"fact", "chat", "work", "graph", "page"}, res
    assert all(h["from"] for h in res["hits"])                       # every hit says where it came from
    assert not res.get("skipped")


def test_one_search_keeps_the_fence_incognito_and_her_recall_switch(cod, monkeypatch):
    from app import memory, yaad
    from app.coder import store
    c = _world()
    other = _chat("conv_projx", project="proj_x")                    # another Session
    yaad.save_fact(T, "Godown Hinjewadi wala project X ka hai", "auto", conversation_id=other)
    store.store_observation(other, T, {"type": "discovery", "title": "Godown Hinjewadi project X sheet",
                                       "facts": [], "narrative": "", "concepts": []})
    texts = json.dumps(memory.search_all(T, c, "godown Hinjewadi")["hits"], ensure_ascii=False)
    assert "Hinjewadi" not in texts                                    # Session X's memory stays in Session X
    from app import fence
    monkeypatch.setattr(fence, "prefs", lambda t: {"recall": False, "auto": True})
    res = memory.search_all(T, c, "godown Bhosari")
    assert {h["source"] for h in res["hits"]} <= {"fact", "work", "graph"}   # past chats + page off with her switch


def test_the_tool_is_the_one_door_and_always_in_view(cod):
    from app.agent import admit, desk_tools
    from app.agent.tools import Ctx
    from app.config import get_settings
    c = _world()
    out = asyncio.run(desk_tools.yaad_khojo(Ctx(tenant_id=T, conversation_id=c), "godown Bhosari"))
    assert {h["source"] for h in out["hits"]} >= {"fact", "chat", "work"}
    only = asyncio.run(desk_tools.yaad_khojo(Ctx(tenant_id=T, conversation_id=c), "godown Bhosari", kind="decision"))
    assert only["hits"] and all(h["kind"] == "decision" for h in only["hits"])   # the old kind filter still works
    adm = admit.plan_for("namaste", get_settings())
    assert adm is not None and "yaad_khojo" in {t["name"] for t in adm.specs()}


def test_one_view_of_everything(cod):
    from app import memory
    _world()
    ev = memory.everything(T)
    assert ev["fact_count"] == 1 and ev["chat_index_count"] >= 1 and ev["work_note_count"] == 1
    assert ev["graph_count"] == 1 and "Bhosari" in ev["page"]


def test_reset_everything_keeps_her_chats(cod):
    from app import aboutme, memory
    from app.coder import store
    c = _world()
    out = memory.reset_all(T)
    assert out["facts"] == 1 and out["chat_index"] >= 1 and out["work"] >= 1 and out["graph"] == 1 and out["page"] == 1
    assert memory.search_all(T, c, "godown Bhosari")["hits"] == []
    assert aboutme.get(T)["text"] == "" and store.recent_observations(T) == []
    with session() as s:
        assert s.get(Conversation, c) is not None                          # her chat itself stays


def test_reset_endpoint_needs_the_word(cod):
    from fastapi.testclient import TestClient
    from app.config import get_settings
    from app.main import app
    _world()
    key = get_settings().api_key
    h = {"Authorization": f"Bearer {key}"} if key else {}
    with TestClient(app) as cl:
        assert cl.post("/api/memory/reset", json={}, headers=h).status_code == 400
        assert cl.get("/api/memory/everything", headers=h).json()["fact_count"] == 1
        r = cl.post("/api/memory/reset", json={"confirm": "RESET"}, headers=h)
    assert r.status_code == 200 and r.json()["removed"]["facts"] == 1


# ---------------------------------------------------------------- 2. just in time
def test_a_maybe_related_old_chat_no_longer_rides_every_message(env):
    from app import yaad
    c = _chat("conv_jit")
    yaad.add_item(T, "decision", "Mehta Traders ko 200 boxes bheje Bhosari godown se", _chat("conv_old"))
    plain = yaad.turn_block(T, c, "Mehta Traders ke liye naya quotation banao")
    assert "Purani yaad" not in plain                                  # fetched by yaad_khojo, not pasted
    past = yaad.turn_block(T, c, "pichhli baar Mehta Traders ko kitne boxes bheje the")
    assert "Purani yaad" in past and "200 boxes" in past                # her own pointer at the past still brings it


def test_system_prompt_carries_15_newest_facts_not_40(env, monkeypatch):
    from app import life, yaad
    from app.config import get_settings
    for i in range(60):
        yaad.save_fact(T, f"Client number {i:02d} ka sheher alag hai: city{i:02d}", "user")
    blk = life.context_block(T)
    listed = [ln for ln in blk.splitlines() if ln.startswith("- ") and "city" in ln]
    assert len(listed) == 15 and "city59" in blk and "city10" not in blk
    assert "yaad_khojo" in blk                                         # the model is told where the rest is
    monkeypatch.setenv("MEMORY_RECENT_FACTS", "40")
    get_settings.cache_clear()
    old = life.context_block(T)
    get_settings.cache_clear()
    assert len([ln for ln in old.splitlines() if ln.startswith("- ") and "city" in ln]) == 40
    assert len(blk) < len(old) * 0.5                                    # measured: under half the old size


def test_a_fact_beyond_the_15_still_reaches_the_turn_by_meaning(env):
    from app import yaad
    yaad.save_fact(T, "Riya is her daughter; class 5 at DPS Akola", "user")
    for i in range(30):
        yaad.save_fact(T, f"Client number {i:02d} ka sheher alag hai: city{i:02d}", "user")
    from app.life import context_block
    assert "Riya" not in context_block(T)                               # past the 15 newest: not in the prompt
    blk = yaad.turn_block(T, _chat("conv_riya"), "Riya DPS Akola class 5 ki fees kab bharni hai")
    assert "Riya is her daughter" in blk                                # old fact, by meaning, for this message


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.844.0"
