"""v0.246 PHASE 3C FENCED SESSIONS: what Hoola picks up inside one Session (console project) stays inside it - facts it
picked up itself, the work diary, running jobs, puri yaad search and Gyaan's chat hits. Her own "yaad rakhna" facts,
pinned facts and older rows stay global. A chat moved between Sessions takes its memory along. MEMORY_FENCE=false =
the old shared memory."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.agent import run_turn, set_client
from app.db import Conversation, MemoryFact, Message, session


def _conv(project=None, title=""):
    with session() as s:
        c = Conversation(tenant_id="default", project_id=project, title=title or None)
        s.add(c)
        s.flush()
        return c.id


@pytest.fixture()
def world(env):
    """Client X Session (two chats), Client Y Session, one general chat; facts of every kind."""
    from app import yaad
    w = SimpleNamespace(x1=_conv("px"), x2=_conv("px"), y=_conv("py"), g=_conv())
    w.fx = yaad.save_fact("default", "Client X ka contact person Anil Joshi hai", "auto", w.x1)["id"]
    w.fy = yaad.save_fact("default", "Client Y ko delivery Thane godown pe chahiye", "auto", w.y)["id"]
    w.fg = yaad.save_fact("default", "Ghar ka internet connection Airtel ka hai", "auto", w.g)["id"]
    with session() as s:
        s.add(MemoryFact(tenant_id="default", text="Mera naam Meghana hai aur main Pune mein rehti hoon"))   # she asked
        s.add(MemoryFact(tenant_id="default", text="Reports hamesha PDF mein chahiye", pinned=True,
                         conversation_id=w.y, source="auto"))                                         # pinned = global
    return w


def _texts(facts):
    return " | ".join(f.text for f in facts)


# ------------------------------------------------------------------ facts
def test_facts_stay_in_their_session(world):
    from app import life
    w = world
    x2 = _texts(life.memory_facts("default", 60, w.x2))
    assert "Client X" in x2 and "Client Y" not in x2 and "Airtel" not in x2           # same Session, other chat: yes
    assert "Meghana" in x2 and "PDF" in x2                                              # hers + pinned: everywhere
    y = _texts(life.memory_facts("default", 60, w.y))
    assert "Client Y" in y and "Client X" not in y
    g = _texts(life.memory_facts("default", 60, w.g))
    assert "Airtel" in g and "Client X" not in g and "Client Y" not in g
    every = _texts(life.memory_facts("default", 60))                                   # no chat (her memory screen)
    assert all(k in every for k in ("Client X", "Client Y", "Airtel", "Meghana"))


def test_context_block_and_recall_by_meaning_are_fenced(world):
    from app import life, yaad
    w = world
    blk = life.context_block("default", w.y)
    assert "Client Y" in blk and "Client X" not in blk and "Meghana" in blk
    near = " | ".join(t for _, t in yaad.relevant_facts("default", "Client X ka contact person kaun hai", top=8,
                                                        conversation_id=w.y))
    assert "Anil" not in near
    near_x = " | ".join(t for _, t in yaad.relevant_facts("default", "Client X ka contact person kaun hai", top=8,
                                                          conversation_id=w.x2))
    assert "Anil" in near_x


def test_auto_facts_are_stamped_with_their_chat(world, monkeypatch):
    from app import yaad
    from app.config import get_settings
    monkeypatch.setenv("MEMORY_AUTO", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(yaad, "_LAST_EXTRACT", {})

    async def fake_ask(system, text):
        return json.dumps({"facts": ["Client Y ka purchase manager Ravi Shetty hai"]})
    monkeypatch.setattr(yaad, "_ask", fake_ask)
    got = asyncio.run(yaad.extract_facts("default", world.y, "Client Y ka purchase manager Ravi Shetty hai, yaad rakhna",
                                         "Theek hai"))
    assert got
    with session() as s:
        assert s.get(MemoryFact, got[0]["id"]).conversation_id == world.y


# ------------------------------------------------------------------ search, diary, jobs
def test_puri_yaad_search_is_fenced(world):
    from app import yaad
    w = world
    yaad.add_item("default", "exchange", "Owner: Client X quotation QZX-7781 final karo | Hoola: ho gaya", w.x1, ref="test-x")
    yaad.add_item("default", "exchange", "Owner: Client Y quotation QZY-5512 final karo | Hoola: ho gaya", w.y, ref="test-y")
    with session() as s:
        s.add(Message(conversation_id=w.x1, role="user", content="raw note ZEBRA-4410 for client X", display="x"))
    assert "QZX-7781" in json.dumps(yaad.search("default", "Client X quotation QZX-7781", top=8))   # her own screen
    from_y = json.dumps(yaad.search("default", "Client X quotation QZX-7781", top=8, conversation_id=w.y))
    assert "QZX-7781" not in from_y                                                     # never from Client Y's chat
    assert "QZX-7781" in json.dumps(yaad.search("default", "Client X quotation QZX-7781", top=8, conversation_id=w.x2))
    assert "QZY-5512" in json.dumps(yaad.search("default", "Client Y quotation QZY-5512", top=8, conversation_id=w.y))
    assert "ZEBRA-4410" not in json.dumps(yaad.search("default", "ZEBRA-4410", top=5, conversation_id=w.y))
    assert "ZEBRA-4410" in json.dumps(yaad.search("default", "ZEBRA-4410", top=5, conversation_id=w.x2))


def test_work_diary_and_running_jobs_are_fenced(world):
    from app import kaamwatch, yaad
    from app.agent.pakka import TaskRun
    w = world
    with session() as s:
        s.add(TaskRun(tenant_id="default", request="Client X ka catalogue PDF banao", outcome="done", conversation_id=w.x1))
        s.add(TaskRun(tenant_id="default", request="Client Y ka bill bhejo", outcome="done", conversation_id=w.y))
        s.add(TaskRun(tenant_id="default", request="purana kaam bina chat ke", outcome="done"))           # pre-v0.246
        s.add(kaamwatch.KaamJob(tenant_id="default", conversation_id=w.x1, key="t:1", kind="site", label="Website",
                                title="Client X ki website", state="working"))
    d = yaad.diary_block("default", w.y)
    assert "Client Y ka bill" in d and "Client X" not in d and "purana kaam" in d
    assert "Client X ka catalogue" in yaad.diary_block("default", w.x2)
    assert "Client X ki website" not in (kaamwatch.block("default", w.y) or "")
    assert "Client X ki website" in kaamwatch.block("default", w.x2)


# ------------------------------------------------------------------ moving, switching off
def test_a_moved_chat_takes_its_memory_along(world):
    from app import life
    w = world
    with session() as s:
        s.get(Conversation, w.x1).project_id = "py"                  # she moves the chat into Client Y's Session
    assert "Anil" in _texts(life.memory_facts("default", 60, w.y))   # its facts went with it
    assert "Anil" not in _texts(life.memory_facts("default", 60, w.x2))


def test_fence_off_is_the_old_shared_memory(world, monkeypatch):
    from app import life
    from app.config import get_settings
    monkeypatch.setenv("MEMORY_FENCE", "false")
    get_settings.cache_clear()
    every = _texts(life.memory_facts("default", 60, world.y))
    assert "Client X" in every and "Airtel" in every


# ------------------------------------------------------------------ end to end + report
class Model:
    def __init__(self):
        self.sent = []
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kw):
        self.sent.append(json.dumps({"system": kw.get("system"), "messages": kw["messages"]}, default=str,
                                    ensure_ascii=False))
        return SimpleNamespace(content=[{"type": "text", "text": "Ho gaya."}], stop_reason="end_turn")


def test_a_turn_in_one_session_never_sees_the_other(world):
    m = Model()
    set_client(m)
    asyncio.run(run_turn(world.y, "Client ka contact person kaun hai?", tenant_id="default"))
    req = m.sent[0]
    assert "Client Y ko delivery" in req and "Meghana" in req
    assert "Client X ka contact" not in req and "Airtel" not in req


def test_context_report(world):
    client = TestClient(__import__("app.main", fromlist=["app"]).app)
    r = client.get("/api/context/report").json()
    assert r["fence"]["on"] is True and "compactions" in r and "gauge" in r and "compact" in r


def test_memory_quiz_plants_its_details(env):
    import importlib.util
    from pathlib import Path
    p = Path(__file__).resolve().parents[1] / "tools" / "memory_quiz.py"
    spec = importlib.util.spec_from_file_location("memory_quiz", p)
    mq = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mq)
    cid = mq._build(120, mq.PLANTS[:5])
    with session() as s:
        texts = [m.content for m in s.query(Message).filter(Message.conversation_id == cid, Message.role == "user")]
    assert len(texts) == 120 and all(any(p[0] == t for t in texts) for p in mq.PLANTS[:5])
