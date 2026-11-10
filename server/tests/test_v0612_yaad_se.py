"""v0.612 YAAD SE + SUDHAAR YAAD (owner: "GO 1 2" after the Dots / Grok memory comparison).

1. YAAD SE - Grok's book icon: under a reply, one note naming the memory it actually leaned on (a fact, a past chat by
   its title, a work note...), each line forgettable. A memory handed to the model but never used is not shown.
   Forgetting a past chat keeps the chat in her list; it is only never recalled again.
2. SUDHAAR YAAD - Grok Bot / Dots 'learn how you like things done': a correction becomes a standing preference.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.db import Conversation, session

from tests.test_v0473_hoola_coder import cod  # noqa: F401

T = "default"
REPO = Path(__file__).resolve().parents[2]


def _chat(cid: str, title: str | None = None) -> str:
    with session() as s:
        s.add(Conversation(id=cid, tenant_id=T, title=title))
    return cid


def test_only_memory_the_reply_really_used_is_named(env):
    from app import yaad
    c = _chat("conv_a")
    yaad.note_used(c, [{"source": "fact", "id": 1, "text": "Godown ka pata Plot 44 Bhosari MIDC"},
                       {"source": "fact", "id": 2, "text": "Riya is her daughter; class 5 at DPS"}])
    got = yaad.used_sources(c, "Theek hai, maal Plot 44 Bhosari wale godown se jayega.")
    assert [g["id"] for g in got] == [1] and got[0]["label"] == "Remembered fact"
    assert yaad.used_sources(c, "anything") == []                      # read once per turn


def test_a_past_chat_is_named_by_its_title_and_the_note_is_published(env, monkeypatch):
    from app import yaad
    from app.events import bus
    old = _chat("conv_old", "Mehta Traders ka order")
    c = _chat("conv_now")
    yaad.add_item(T, "decision", "Mehta Traders ko 200 boxes bheje Bhosari godown se", old)
    events = []
    monkeypatch.setattr(bus, "publish", lambda conv, kind, payload: events.append((conv, kind, payload)))
    yaad.turn_block(T, c, "pichhli baar Mehta Traders ko kitne boxes bheje the")
    items = yaad.publish_used(c, "Pichhli baar Mehta Traders ko 200 boxes bheje gaye the, Bhosari godown se.")
    assert items and items[0]["source"] == "chat" and items[0]["label"] == "Mehta Traders ka order"
    kind, payload = events[-1][1], events[-1][2]
    assert kind == "memory_used" and payload["say"].startswith("Yaad se: Mehta Traders ka order")


def test_forgetting_a_past_chat_keeps_the_chat_but_never_recalls_it(env):
    from app import memory, yaad
    old = _chat("conv_forget_me", "Purana quotation")
    c = _chat("conv_here")
    yaad.add_item(T, "decision", "Joshi ko quotation sirf PDF mein bheja", old)
    assert yaad.search(T, "Joshi quotation PDF", conversation_id=c)
    out = memory.unremember(T, "chat", conversation_id=old)
    assert out["ok"] and out["index_rows"] >= 1
    assert yaad.search(T, "Joshi quotation PDF", conversation_id=c) == []
    yaad.add_item(T, "decision", "Joshi ko quotation sirf PDF mein bheja", old)   # a later re-index stays filtered
    assert yaad.search(T, "Joshi quotation PDF", conversation_id=c) == []
    with session() as s:
        assert s.get(Conversation, old) is not None                       # her chat itself stays


def test_forgetting_a_fact_or_a_work_note_from_the_note(cod):
    from app import memory, yaad
    from app.coder import store
    c = _chat("conv_w")
    f = yaad.save_fact(T, "Godown ka pata Plot 44 Bhosari MIDC hai", "user")
    assert memory.unremember(T, "fact", id=f["id"])["ok"]
    oid = store.store_observation(c, T, {"type": "discovery", "title": "Stock sheet updated", "facts": [],
                                         "narrative": "x", "concepts": []})
    assert memory.unremember(T, "work", id=oid)["ok"]
    assert store.recent_observations(T) == []
    assert memory.unremember("someone_else", "fact", id=999)["ok"] is False


def test_the_endpoint(env):
    from fastapi.testclient import TestClient
    from app import yaad
    from app.config import get_settings
    from app.main import app
    f = yaad.save_fact(T, "Godown ka pata Plot 44 Bhosari MIDC hai", "user")
    key = get_settings().api_key
    h = {"Authorization": f"Bearer {key}"} if key else {}
    with TestClient(app) as cl:
        assert cl.post("/api/memory/unremember", json={"source": "fact", "id": f["id"]}, headers=h).status_code == 200
        assert cl.post("/api/memory/unremember", json={"source": "fact", "id": f["id"]}, headers=h).status_code == 404


def test_a_memory_lookup_counts_as_used(env):
    from app import yaad
    from app.agent import desk_tools
    from app.agent.tools import Ctx
    c = _chat("conv_look")
    yaad.save_fact(T, "Supplier Kapoor Steels ka GST state code 27 hai", "user")
    asyncio.run(desk_tools.yaad_khojo(Ctx(tenant_id=T, conversation_id=c), "Kapoor Steels GST state code"))
    got = yaad.used_sources(c, "Kapoor Steels ka GST state code 27 hai.")
    assert got and got[0]["source"] == "fact"


def test_corrections_become_standing_preferences():
    from app import yaad
    from app.agent import prompts
    assert "CORRECTIONS (v0.612" in yaad.FACT_SYSTEM and "WHEN / WANT" in yaad.FACT_SYSTEM
    src = Path(prompts.__file__).read_text()
    assert "never have to correct the same thing twice" in src


def test_both_clients_draw_the_note():
    v2 = (REPO / "server" / "app" / "static" / "console" / "v2.js").read_text()
    assert "kind === 'memory_used'" in v2 and "/api/memory/unremember" in v2 and "'memory_used'," in v2
    st = (REPO / "lib" / "state.dart").read_text()
    chat = (REPO / "lib" / "ui" / "chat_screen.dart").read_text()
    cards = (REPO / "lib" / "ui" / "desk_cards.dart").read_text()
    api = (REPO / "lib" / "api.dart").read_text()
    assert "case 'memory_used':" in st and "MemoryUsedChip(" in chat and "class MemoryUsedChip" in cards
    assert "/api/memory/unremember" in api
    events = (REPO / "server" / "app" / "events.py").read_text()
    assert '"memory_used"' in events


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.758.0"
