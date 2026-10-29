"""v0.248 PHASE 3B CLAUDE-STYLE MEMORY: "Mere baare mein" (her memory page: built for active owners from GLOBAL
facts + general chats only, her edits win, loaded in every chat / call), haal_ki_chats (her other chats by time,
fenced, never incognito), incognito chats (read memory, write nothing), and her two switches."""
import asyncio
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.agent import run_turn, set_client
from app.db import Conversation, MemoryFact, Message, session


def _conv(project=None, incognito=None, title=None):
    with session() as s:
        c = Conversation(tenant_id="default", project_id=project, incognito=incognito, title=title)
        s.add(c)
        s.flush()
        return c.id


def _say(conv, text, role="user", at=None):
    with session() as s:
        m = Message(conversation_id=conv, role=role, content=text if role == "user" else [{"type": "text", "text": text}],
                    display=text)
        if at is not None:
            m.created_at = at
        s.add(m)


class Writer:
    """Scripted Claude: the page writer echoes what it was given (so the test sees what went IN); chat says Ho gaya."""

    def __init__(self):
        self.page_in, self.chat = [], []
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kw):
        sysm = kw.get("system")
        if isinstance(sysm, str) and sysm.startswith("You keep ONE short memory page"):
            got = kw["messages"][0]["content"][0]["text"]
            self.page_in.append(got)
            return SimpleNamespace(content=[{"type": "text", "text": "KAAM - bakery chalati hai, Pune\nPASAND - "
                                             "reports Marathi mein; OTP 482913 kabhi nahi"}], stop_reason="end_turn")
        self.chat.append(json.dumps({"system": sysm, "messages": kw["messages"]}, default=str, ensure_ascii=False))
        return SimpleNamespace(content=[{"type": "text", "text": "Ho gaya."}], stop_reason="end_turn")


@pytest.fixture()
def w(env):
    g, x, inc = _conv(), _conv("px"), _conv(incognito=True)
    with session() as s:
        s.add(MemoryFact(tenant_id="default", text="Meri bakery Pune mein hai"))                          # global
        s.add(MemoryFact(tenant_id="default", text="Client X ka discount code XDISC", conversation_id=x,
                         source="auto"))                                                                  # Session's own
    _say(g, "Main reports hamesha Marathi mein leti hoon")
    _say(x, "Client X ke liye naya catalogue chahiye")
    _say(inc, "Mera doctor appointment secret hai")
    m = Writer()
    set_client(m)
    return SimpleNamespace(g=g, x=x, inc=inc, m=m)


# ------------------------------------------------------------------ Mere baare mein
def test_page_is_built_from_global_facts_and_general_chats_only(w):
    from app import aboutme
    v = asyncio.run(aboutme.rebuild("default"))
    fed = w.m.page_in[0]
    assert "Meri bakery Pune mein hai" in fed and "Marathi" in fed
    assert "XDISC" not in fed and "Client X" not in fed          # a Session's details never reach the page
    assert "doctor" not in fed                                     # nor an incognito chat
    assert v["text"].startswith("KAAM") and "482913" not in v["text"] and "****" in v["text"]
    assert asyncio.run(aboutme.rebuild("default")) is None         # nothing new: no second model call
    assert len(w.m.page_in) == 1


def test_page_rides_every_chat_and_her_edit_wins(w):
    from app import aboutme, life
    aboutme.set_text("default", "KAAM - main bakery chalati hoon (HER)")
    assert "MERE BAARE MEIN" in life.context_block("default", w.x) and "(HER)" in life.context_block("default", w.g)
    _say(w.g, "Ab main cafe bhi khol rahi hoon")
    asyncio.run(aboutme.rebuild("default"))
    assert w.m.page_in[-1].startswith("HER EDIT") and "(HER)" in w.m.page_in[-1]


def test_due_only_for_active_owners_once_a_day(w):
    from app import aboutme
    assert aboutme.due_tenants() == ["default"]
    asyncio.run(aboutme.rebuild("default"))
    assert aboutme.due_tenants() == []


# ------------------------------------------------------------------ switches
def test_switches(w):
    from app import aboutme, fence, life, yaad
    client = TestClient(__import__("app.main", fromlist=["app"]).app)
    aboutme.set_text("default", "KAAM - bakery")
    r = client.put("/api/memory/settings", json={"auto": False, "recall": False}).json()
    assert r["switches"] == {"auto": False, "recall": False}
    assert asyncio.run(aboutme.rebuild("default")) is None                     # auto off: no rebuild
    assert "MERE BAARE MEIN" not in life.context_block("default", w.g)          # recall off: page not loaded
    from app.agent.recall_tools import find
    assert find("default", w.g, "aaj")["off"] is True
    asyncio.run(yaad.extract_facts("default", w.g, "Mera naya godown Bhosari mein hai yaad rakhna", "ok"))
    client.put("/api/memory/settings", json={"recall": True})
    assert fence.prefs("default") == {"auto": False, "recall": True}


# ------------------------------------------------------------------ recent chats by time
def test_recent_chats_by_time_fenced_and_never_incognito(w):
    from app.agent.recall_tools import find
    g2 = _conv(title="Kal ki baat")
    _say(g2, "Kal tay hua ki Sharma ji ko 50 boxes jayenge", at=datetime.now(timezone.utc) - timedelta(days=1))
    today = find("default", w.g, "aaj")
    titles = json.dumps(today, ensure_ascii=False)
    assert "doctor" not in titles and "Client X" not in titles                 # incognito + other Session: never
    assert all(c["conversation_id"] != w.g for c in today["chats"])            # never the chat she is in
    kal = find("default", w.g, "kal")
    assert kal["count"] == 1 and "50 boxes" in json.dumps(kal, ensure_ascii=False)
    from_x = find("default", w.x, "aaj")
    assert all(c["conversation_id"] in () for c in from_x["chats"])          # Session X sees only Session X chats


def test_recent_chats_tool_is_always_offered(env):
    from app.agent.admit import CORE_FAMILIES
    from app.agent.tools import FAMILY_OF, HANDLERS
    assert "haal_ki_chats" in HANDLERS and FAMILY_OF["haal_ki_chats"] == "recall" and "recall" in CORE_FAMILIES


# ------------------------------------------------------------------ incognito
def test_incognito_chat_reads_memory_but_writes_nothing(w, monkeypatch):
    from app import yaad
    from app.agent.pakka import TaskRun
    from app.config import get_settings
    monkeypatch.setenv("MEMORY_AUTO", "true")
    get_settings.cache_clear()
    called = []

    async def fake_extract(*a, **k):
        called.append(a)
        return []
    monkeypatch.setattr(yaad, "extract_facts", fake_extract)
    asyncio.run(run_turn(w.inc, "Mera BP thoda high hai, doctor ko kal dikhana hai", tenant_id="default"))
    asyncio.run(yaad.drain())
    sent = next(c for c in w.m.chat if "INCOGNITO CHAT" in c)               # the reply call (not the auto title)
    assert "Meri bakery Pune" in sent                                       # reads her global memory
    with session() as s:
        assert s.query(yaad.YaadItem).filter(yaad.YaadItem.conversation_id == w.inc).count() == 0
        assert s.query(TaskRun).filter(TaskRun.conversation_id == w.inc).count() == 0
    assert called == []                                                     # no fact picking from incognito
    assert "doctor" not in json.dumps(yaad.search("default", "doctor BP", top=5, conversation_id=w.g))


def test_incognito_remember_is_refused(w):
    from app.agent.life_tools import remember
    from app.agent.tools import Ctx, ToolError
    ctx = Ctx(tenant_id="default", conversation_id=w.inc)
    with pytest.raises(ToolError):
        asyncio.run(remember(ctx, "BP ki dawai subah leni hai"))


def test_incognito_new_chat_endpoints(env):
    client = TestClient(__import__("app.main", fromlist=["app"]).app)
    b = client.get("/api/bootstrap", params={"new": "true", "incognito": "true"}).json()
    assert b["incognito"] is True and b["conversation_new"] is True
    with session() as s:
        g = s.query(Message).filter(Message.conversation_id == b["conversation_id"]).first()
    assert g.display.startswith("🕶 Incognito chat")
    normal = client.post("/api/conversations").json()
    assert normal["incognito"] is False and normal["id"] != b["conversation_id"]
    lst = client.get("/api/conversations").json()["conversations"]
    assert any(c["id"] == b["conversation_id"] and c["incognito"] for c in lst) or lst == []


def test_about_endpoints(w):
    client = TestClient(__import__("app.main", fromlist=["app"]).app)
    r = client.put("/api/memory/about", json={"text": "KAAM - bakery; card 4111 1111 1111 1111"}).json()
    assert "4111" not in r["about"]["text"] and r["about"]["by"] == "her"
    g = client.get("/api/memory/about").json()
    assert g["switches"] == {"auto": True, "recall": True} and g["about"]["text"].startswith("KAAM")
    rb = client.post("/api/memory/about/rebuild").json()
    assert rb["changed"] is True and rb["about"]["by"] == "hoola"
    assert client.delete("/api/memory/about").json()["about"]["text"] == ""
