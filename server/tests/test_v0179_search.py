"""v0.179 Console v2 phase 4: sidebar + search power. FTS5 search (chatsearch) that finds words across every chat
with the event id to jump to, hides taken-back and hidden-branch messages, stays inside her tenant, keeps indexing
on its own (watermark), the in-chat find endpoint, and the console files that carry the find bar / jump rail /
shortcut registry."""
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.test_v161_stream import KEY, StreamingClaude, _text

H = {"Authorization": f"Bearer {KEY}"}


@pytest.fixture
def cs(env, monkeypatch):
    monkeypatch.setenv("CHAT_SESSIONS", "true")
    monkeypatch.setenv("CONSOLE_STREAM", "true")
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app import main
    with TestClient(main.app) as c:
        yield c


def _say(c, conv, text, brain):
    from app.agent import set_client
    set_client(brain)
    r = c.post(f"/api/conversations/{conv}/messages", json={"text": text}, headers=H)
    assert r.status_code == 202, r.text


def _search(c, q):
    return c.get("/api/conversations/search", params={"q": q}, headers=H).json()["results"]


def test_fts_search_finds_words_across_chats_with_event_ids(cs):
    c = cs
    old = c.post("/api/conversations", headers=H).json()["id"]
    _say(c, old, "Sharma ji ka kiraya agreement kab khatam hoga?", StreamingClaude([[_text(["Agreement 31 March ko khatam hai."])]]))
    new = c.post("/api/conversations", headers=H).json()["id"]
    _say(c, new, "aaj ka mausam kaisa hai?", StreamingClaude([[_text(["Dhoop hai, barish ka chance nahi."])]]))
    hits = _search(c, "agreement")
    mine = [h for h in hits if h["conversation_id"] == old]
    assert mine and all(h["event_id"] > 0 for h in mine), hits          # every hit can jump to its message
    user_hit = next(h for h in mine if h["role"] == "user")
    assert "agreement" in user_hit["snippet"].lower() and "<<" in user_hit["snippet"]   # FTS5 snippet marks
    assert user_hit["title"].startswith("Sharma ji")                    # title fill from the first message
    assert not [h for h in hits if h["conversation_id"] == new]         # the other chat has nothing to say here
    c.patch(f"/api/conversations/{old}", json={"title": "Sharma ji ka agreement"}, headers=H)
    titles = [h for h in _search(c, "Sharma") if h["role"] == "title"]
    assert titles and titles[0]["event_id"] == 0                        # the chat's own name matches too


def test_search_stays_inside_her_tenant(cs):
    c = cs
    mine = c.post("/api/conversations", headers=H).json()["id"]
    _say(c, mine, "boring kaam wali baat about geyser repair", StreamingClaude([[_text(["Theek hai."])]]))
    r = c.get("/api/conversations/search", params={"q": "geyser"}, headers={"Authorization": "Bearer wrong-key"})
    assert r.status_code in (401, 403)
    from app.db import Conversation, Message, session
    with session() as s:                                                # a stranger's chat with the same words
        other = Conversation(tenant_id="someone-else", title="doosre ka chat")
        s.add(other); s.flush()
        s.add(Message(conversation_id=other.id, role="user", content=[], display="geyser repair ho gaya hai"))
        s.commit()
    hits = _search(c, "geyser")
    assert all(h["conversation_id"] == mine for h in hits)              # only her own rows come back


def test_search_hides_taken_back_and_hidden_branch_messages(cs):
    c = cs
    conv = c.post("/api/conversations", headers=H).json()["id"]
    _say(c, conv, "ye message thoda galat tha aboutPlot", StreamingClaude([[_text(["Ok, samajh gayi."])]]))
    assert any("aboutPlot" in h["snippet"] for h in _search(c, "aboutPlot"))
    from app.db import Event, Message, session
    with session() as s:                                                # she took it back (v0.173 tombstone)
        ev = s.scalars(select(Event).where(Event.conversation_id == conv, Event.kind == "message")).all()
        for e in ev:
            if (e.payload or {}).get("role") == "user":
                e.payload = {**e.payload, "taken_back": True}
        s.commit()
    assert not [h for h in _search(c, "aboutPlot") if h["role"] == "user"]
    with session() as s:                                                # an edit hides the old version (hid: branch)
        m = s.scalars(select(Message).where(Message.conversation_id == conv, Message.role == "assistant",
                                             Message.display.like("%samajh%"))).first()
        assert m is not None
        m.branch = "hid:g1:0"
        s.commit()
    assert not [h for h in _search(c, "samajh") if h["role"] == "assistant"]
    with session() as s:                                                # branch switch shows it again
        m = s.scalars(select(Message).where(Message.conversation_id == conv, Message.role == "assistant",
                                             Message.display.like("%samajh%"))).first()
        m.branch = None
        s.commit()
    assert [h for h in _search(c, "samajh") if h["role"] == "assistant"]


def test_search_keeps_up_without_a_manual_reindex(cs):
    c = cs
    conv = c.post("/api/conversations", headers=H).json()["id"]
    _say(c, conv, "pehli baat inverter ke baare mein", StreamingClaude([[_text(["Theek hai."])]]))
    assert _search(c, "inverter")
    _say(c, conv, "doosri baat inverter ki warranty ke baare mein", StreamingClaude([[_text(["Note kar liya."])]]))
    hits = _search(c, "inverter warr")
    assert hits and any("warranty" in h["snippet"].lower() for h in hits)   # prefix words, no quotes needed
    hits = _search(c, "inverter warranty")
    assert any("warranty" in h["snippet"].lower() for h in hits)            # the new message is found, no reindex
    from app import chatsearch
    from app.db import session
    with session() as s:
        top = s.execute(chatsearch.sqltext("SELECT value FROM search_meta WHERE key='indexed_id'")).first()
    assert top and int(top[0]) > 0                                          # the watermark really moved


def test_find_in_chat_endpoint(cs):
    c = cs
    conv = c.post("/api/conversations", headers=H).json()["id"]
    _say(c, conv, "GST ka sawaal pehli baar", StreamingClaude([[_text(["GST ka jawab pehli baar."])]]))
    _say(c, conv, "mausam ki baat beech mein", StreamingClaude([[_text(["Garmi hai."])]]))
    _say(c, conv, "GST ka doosra sawaal", StreamingClaude([[_text(["GST ka doosra jawab."])]]))
    r = c.get(f"/api/conversations/{conv}/find", params={"q": "gst"}, headers=H).json()
    assert r["total"] == 4 and len(r["matches"]) == 4
    ids = [m["event_id"] for m in r["matches"]]
    assert ids == sorted(ids)                                               # document order: oldest first
    assert all(m["snippet"] for m in r["matches"])
    r0 = c.get(f"/api/conversations/{conv}/find", params={"q": "  "}, headers=H).json()
    assert r0 == {"total": 0, "matches": []}
    other = c.post("/api/conversations", headers=H).json()["id"]            # another tenant cannot walk her chat
    from app.db import Conversation, session
    with session() as s:
        s.get(Conversation, conv).tenant_id = "koi-aur"
        s.commit()
    assert c.get(f"/api/conversations/{conv}/find", params={"q": "gst"}, headers=H).status_code == 404


def test_search_survives_hinglish_and_hindi_text(cs):
    c = cs
    conv = c.post("/api/conversations", headers=H).json()["id"]
    _say(c, conv, "नमस्ते, किराया कब जमा होगा?", StreamingClaude([[_text(["अगले हफ्ते जमा हो जाएगा।"])]]))
    _say(c, conv, "Doodh wali list bana do", StreamingClaude([[_text(["Doodh, ande, ghee likh liya."])]]))
    hits = _search(c, "किराया")
    assert hits and any("किराया" in h["snippet"] for h in hits)             # Devanagari in, Devanagari out
    hits = _search(c, "doodh lis")
    assert any(h["role"] == "user" for h in hits)                           # prefix + two words, no quotes needed
    r = c.get(f"/api/conversations/{conv}/find", params={"q": '"doodh wali list"'}, headers=H).json()
    assert r["total"] == 1                                                  # quoted = the whole phrase


def test_console_files_carry_the_search_power(env):
    from pathlib import Path
    base = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
    v2 = (base / "v2.js").read_text()
    cl = (base / "chatlist.js").read_text()
    html = (base / "v2.html").read_text()
    assert "id=\"jrail\"" in v2 and "function drawRail" in v2 and "dayLabel" in v2      # the day jump rail
    assert "function openFind" in v2 and "/find?q=" in v2 and "fhit" in v2             # the in-chat find bar
    assert "const KEYS" in v2 and "openKeys" in v2 and "normCombo" in v2               # the shortcut registry
    assert "FIND_SEQ" in cl and "&lt;&lt;" in cl                                       # FTS marks painted safely
    from app.main import APP_VERSION
    assert f"?v={APP_VERSION}" in html                                                 # cache busts moved too
    assert APP_VERSION == "0.185.3"    # conscious-bump guard: moves with every release (bump with pubspec)
