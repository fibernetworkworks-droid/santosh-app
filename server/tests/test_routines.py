"""Automatic jobs (routines) and voice-mode messages."""
import asyncio
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import life, worker
from app.agent.life_tools import cancel_routine, create_routine, list_routines
from app.agent.tools import ToolError
from app.db import Event, Routine, as_utc, now, session
from tests.test_life import IST, conv_ctx


def test_hourly_repeat():
    t = datetime(2026, 10, 18, 9, 30, tzinfo=IST)
    assert life.next_due(t, "hourly", IST).astimezone(IST) == datetime(2026, 10, 18, 10, 30, tzinfo=IST)


def test_routine_runs_by_itself_and_reschedules(env, monkeypatch):
    ctx = conv_ctx()
    with pytest.raises(ToolError):
        asyncio.run(create_routine(ctx, "Old", "x", "2020-01-01T07:00"))
    first = (datetime.now(IST) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
    r = asyncio.run(create_routine(ctx, "Subah ka mausam", "Check weather and tell the user.", first, "daily"))
    once = asyncio.run(create_routine(ctx, "Ek baar", "Say hello.", first, "none"))
    assert {x["id"] for x in asyncio.run(list_routines(ctx))["routines"]} == {r["id"], once["id"]}
    assert "Subah ka mausam" in life.context_block("default")

    calls = []

    async def fake_turn(conv, text, tenant_id=None, voice=False):
        calls.append((conv, text))
        return "Aaj Pune mein dhoop hai."

    import app.agent
    monkeypatch.setattr(app.agent, "run_turn", fake_turn)
    with session() as s:
        for rid in (r["id"], once["id"]):
            s.get(Routine, rid).next_run = now() - timedelta(seconds=5)

    async def tick():
        await worker.run_routines()
        await asyncio.gather(*list(worker._routine_tasks))
        await worker.run_routines()          # nothing is due any more
        await asyncio.gather(*list(worker._routine_tasks))

    asyncio.run(tick())
    assert len(calls) == 2
    assert all(c[0] == ctx.conversation_id and "[Automatic job" in c[1] for c in calls)
    with session() as s:
        d = s.get(Routine, r["id"])
        assert d.status == "active" and d.run_count == 1 and d.last_result.startswith("Aaj Pune")
        assert as_utc(d.next_run) > now() + timedelta(hours=22)
        assert s.get(Routine, once["id"]).status == "done"
        kinds = [e.kind for e in s.query(Event).filter(Event.conversation_id == ctx.conversation_id)]
    assert "routines" in kinds

    asyncio.run(cancel_routine(ctx, r["id"]))
    assert asyncio.run(list_routines(ctx))["routines"] == []


def test_routine_api_and_voice_flag(env, monkeypatch):
    from app import main
    seen = []

    async def fake_turn(conv, text, tenant_id=None, voice=False):
        seen.append(voice)
        return "ok"

    monkeypatch.setattr(main, "run_turn", fake_turn)
    with TestClient(main.app) as c:
        h = c.get("/healthz").json()
        assert "routines" in h["features"] and h["version"] == "0.38.0"
        conv = c.post("/api/conversations").json()["id"]
        assert c.post(f"/api/conversations/{conv}/messages", json={"text": "namaste", "voice": True}).status_code == 202
        assert c.post(f"/api/conversations/{conv}/messages", json={"text": "hi"}).status_code == 202
        assert seen == [True, False]
        with session() as s:
            ro = Routine(tenant_id="default", conversation_id=conv, title="T", instruction="i",
                         next_run=now() + timedelta(hours=1), repeat="daily")
            s.add(ro); s.flush(); rid = ro.id
        assert [x["id"] for x in c.get("/api/routines").json()["routines"]] == [rid]
        assert c.post(f"/api/routines/{rid}/cancel").status_code == 200
        assert c.get("/api/routines").json()["routines"] == []
        assert c.post("/api/routines/nope/cancel").status_code == 404
