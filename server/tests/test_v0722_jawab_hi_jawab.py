"""v0.722 JAWAB HI JAWAB (owner, screenshot: she asked "FIND THE 5 MILLION DOLLOR BUSINESS IDEA FOR AI SAAS PRODUCT" and
got "Here's what's going on right now: Just finished ... The result should be in your chat above ... Open projects on your
desk: HandLink ISP Portal (S-0006) ... Mindrhythm (A-0011) ..." - CHECK THE PROMPT TO HOOLA AND ITS REPLY).
Root cause: the answer was made by a background agent crew; its deliverable (AgentTeam.result, up to 24k chars) never
reached the chat - the follow-up wake turn carried a 400-char snippet + "1-3 lines" + "check the state with tools", and
kaam_status read her WHOLE desk. Now the crew's wake fetches the deliverables and writes the real answer, every wake
talks about its own job only, and kaam_status inside a wake sees only that chat's jobs."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace


def _row(kind, key, state="done", title="5M dollar AI SaaS idea", detail="3 ideas found"):
    return SimpleNamespace(kind=kind, key=key, state=state, title=title, detail=detail, label="Agent team", link="")


def test_a_finished_crew_writes_the_answer_not_a_status():
    from app import kaam_followup as K
    t = K._wake_text(_row("agent_team", "agent_team:tm_abc123"))
    assert "<team_result_due team=\"tm_abc123\">" in t
    assert "agent_status tool with action=check, id=tm_abc123" in t
    assert "ACTUAL ANSWER TO HER QUESTION" in t and "do not list other jobs / projects / cards" in t
    assert "kaam_status" in t and "do not write 'the answer is above'" in t
    assert "1-3 short lines" not in t                         # the old snippet-sized answer is gone for crews
    assert "team_result_due" in K._wake_text(_row("agent_team", "agent_team:x", state="failed"))
    assert "team_result_due" not in K._wake_text(_row("agent_team", "agent_team:x", state="stopped"))


def test_every_other_wake_stays_on_its_own_job():
    from app import kaam_followup as K
    t = K._wake_text(_row("video_job", "video_job:v1"))
    assert "Talk ONLY about THIS job - do not list other jobs / projects / cards." in t
    assert "only if it really is written above in this chat" in t


def test_kaam_status_in_a_wake_sees_only_this_chat(env, monkeypatch):
    monkeypatch.setenv("CHAT_ALONE", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    from app import kaamwatch
    from app.agent import kaam_tools
    from app.agent.tools import Ctx
    rows = [{"key": "site:1", "kind": "site", "label": "Website", "title": "HandLink ISP Portal", "state": "waiting",
             "status": "", "conversation_id": "other_chat", "stage": "", "detail": "", "link": "", "pct": -1,
             "minutes_since_change": 0},
            {"key": "agent_team:t1", "kind": "agent_team", "label": "Agent team", "title": "5M AI SaaS idea",
             "state": "done", "status": "", "conversation_id": "this_chat", "stage": "", "detail": "", "link": "",
             "pct": 100, "minutes_since_change": 0}]
    monkeypatch.setattr(kaamwatch, "jobs", lambda tenant, hours=24, limit=30: list(rows))
    wake = asyncio.run(kaam_tools.kaam_status(Ctx(tenant_id="t", conversation_id="this_chat", actor="wake")))
    assert [j["title"] for j in wake["jobs"]] == ["5M AI SaaS idea"]
    owner = asyncio.run(kaam_tools.kaam_status(Ctx(tenant_id="t", conversation_id="this_chat", actor="owner")))
    assert len(owner["jobs"]) == 2                                # her own "kya hua" question still sees everything
    get_settings.cache_clear()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.split(".")[1] >= "722"
