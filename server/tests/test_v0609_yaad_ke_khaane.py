"""v0.609 YAAD KE KHAANE - the rest of the Claude memory comparison (owner: "FIRST WE COMPLETE MEMORY / CONTEXT WORK").

3. The Claude way of WRITING memory: the live model keeps facts as it chats (remember, replaces=<id> for an update);
   the background extractor only catches what the turn missed - a turn that kept its own memory is not mined again.
4. The controls Claude has: a per-Session "use my main memory" switch (Claude's per-project "Use account memory"),
   an opt-in for sensitive topics (Claude's "Include sensitive topics"), one "Saari yaad mitao" button on the phone.
+  a one-click long-chat memory quiz in vps-ops (memory_quiz / memory_quiz_haiku).
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from app.db import Conversation, session

T = "default"
REPO = Path(__file__).resolve().parents[2]


def _chat(cid: str, project: str | None = None) -> str:
    with session() as s:
        s.add(Conversation(id=cid, tenant_id=T, project_id=project))
    return cid


def _project(name: str = "Shaadi") -> str:
    from app import projects
    return projects.create(T, name)["id"]


# ---------------------------------------------------------------- the per-Session switch
def test_a_session_on_its_own_memory_never_reads_her_main_memory(env):
    from app import aboutme, life, memory, projects, yaad
    pid = _project()
    c = _chat("conv_sess", pid)
    gen = _chat("conv_gen")
    yaad.save_fact(T, "Her bakery is in Pune; Diwali orders peak", "user")             # main (general) memory
    yaad.save_fact(T, "Venue for the shaadi is Royal Lawns, 12 Dec", "auto", conversation_id=c)   # this Session's
    pin = yaad.save_fact(T, "Reports hamesha Marathi mein banana", "user")
    life.pin_fact(T, pin["id"], True)
    aboutme.ensure_table()
    with session() as s:
        s.add(aboutme.AboutMe(tenant_id=T, text="KAAM: bakery Pune", by="hoola"))
    on = life.context_block(T, c)
    assert "bakery is in Pune" in on and "Royal Lawns" in on and "MERE BAARE MEIN" in on
    view = projects.patch(T, pid, use_main_memory=False)
    assert view["use_main_memory"] is False
    off = life.context_block(T, c)
    assert "bakery is in Pune" not in off and "MERE BAARE MEIN" not in off        # her main memory stays out
    assert "Royal Lawns" in off and "Marathi" in off                                # own facts + pinned still ride
    assert not any(h["source"] in ("page", "graph") for h in memory.search_all(T, c, "bakery Pune")["hits"])
    assert "bakery is in Pune" in life.context_block(T, gen)                        # a general chat is unaffected
    projects.patch(T, pid, use_main_memory=True)
    assert "bakery is in Pune" in life.context_block(T, c)


def test_the_switch_rides_the_project_api(env):
    from fastapi.testclient import TestClient
    from app.config import get_settings
    from app.main import app
    pid = _project("Dukaan")
    key = get_settings().api_key
    h = {"Authorization": f"Bearer {key}"} if key else {}
    with TestClient(app) as cl:
        r = cl.patch(f"/api/projects/{pid}", json={"use_main_memory": False}, headers=h)
    assert r.status_code == 200 and r.json()["use_main_memory"] is False


# ---------------------------------------------------------------- sensitive topics: her opt-in
def test_sensitive_topics_are_hers_to_allow_and_some_never(env):
    from app import yaad
    assert yaad.fact_ok("Her mother has diabetes; sugar free sweets only") == "health"
    assert yaad.fact_ok("Her mother has diabetes; sugar free sweets only", sensitive=True) == ""
    assert yaad.fact_ok("Her brother is in jail since March", sensitive=True) == "never"     # Claude never keeps these
    assert yaad.fact_ok("Her salary account is with HDFC", sensitive=True) != ""             # money: never


def test_the_sensitive_switch_reaches_the_fact_writer(env):
    from fastapi.testclient import TestClient
    from app import fence, yaad
    from app.config import get_settings
    from app.main import app
    assert fence.prefs(T)["sensitive"] is False                                              # off by default
    assert yaad.save_fact(T, "Her mother has diabetes; sugar free sweets only", "auto") is None
    key = get_settings().api_key
    h = {"Authorization": f"Bearer {key}"} if key else {}
    with TestClient(app) as cl:
        r = cl.put("/api/memory/settings", json={"sensitive": True}, headers=h)
    assert r.status_code == 200 and r.json()["switches"]["sensitive"] is True
    assert yaad.save_fact(T, "Her mother has diabetes; sugar free sweets only", "auto")


# ---------------------------------------------------------------- the live model writes its own memory
def test_a_turn_that_kept_its_own_memory_is_not_mined_again(env, monkeypatch):
    from app import yaad
    from app.agent import life_tools
    from app.agent.tools import Ctx
    calls = []

    async def fake_extract(*a, **k):
        calls.append(a)
        return []
    monkeypatch.setattr(yaad, "extract_facts", fake_extract)
    c, d = _chat("conv_live"), _chat("conv_quiet")

    async def go():
        await life_tools.remember(Ctx(tenant_id=T, conversation_id=c), "Riya is her daughter; class 5 at DPS")
        yaad.after_turn(T, c, "meri beti Riya DPS mein class 5 mein hai", "Yaad rakh liya.")
        yaad.after_turn(T, d, "mera godown Bhosari mein hai, MIDC wala", "Achha.")
        await yaad.drain()
    asyncio.run(go())
    assert [a[1] for a in calls] == [d]                     # only the turn that did NOT keep its own memory


def test_the_prompt_teaches_the_claude_way(env):
    from app.agent import prompts
    src = Path(prompts.__file__).read_text()
    assert "replaces=<that fact's id>" in src and "YOU keep it as you chat" in src and "yaad_khojo" in src


# ---------------------------------------------------------------- surfaces + the quiz job
def test_phone_console_and_ops_wiring():
    page = (REPO / "lib" / "ui" / "memory_page_screen.dart").read_text()
    assert "Delete all memory" in page and "Sensitive topics too" in page and "memoryReset" in page
    api = (REPO / "lib" / "api.dart").read_text()
    assert "/api/memory/reset" in api and "'confirm': 'RESET'" in api and "'sensitive': sensitive" in api
    pj = (REPO / "server" / "app" / "static" / "console" / "projects.js").read_text()
    assert 'data-a="mainmem"' in pj and "use_main_memory" in pj
    ops = (REPO / ".github" / "workflows" / "vps-ops.yml").read_text()
    assert "- memory_quiz\n" in ops and "- memory_quiz_haiku\n" in ops and "tools/memory_quiz.py --modes full,compact" in ops
    quiz = (REPO / "server" / "tools" / "memory_quiz.py").read_text()
    assert "test_model([])" in quiz


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.744.0"
