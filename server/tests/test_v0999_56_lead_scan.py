"""v0.999.56 LEAD SCAN - the public Google Maps listings scan (the v0.543 SCRAPE lane) fed to the Lead Generation
employee: Start + Save on the desk's Find leads page, weekly saved scans, leads_desk action=scan for its chat, all in the
background; her switch stays OFF by default and every wall of run_scrape stays where it was."""
import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
T = "default"


@pytest.fixture
def hired(env):
    from app.employee import hire
    from app.leads import pipeline as PL
    hire.hire(T, "leads", trust="seekh")
    PL._SCANS.clear()
    yield
    PL._SCANS.clear()


def _fake_scrape(monkeypatch, calls):
    from app.leads import service as S

    async def fake(tenant, ask, query, near="", center=None, sweep_km=3.0, zoom=15, max_rows=1000, **k):
        calls.append((tenant, query, near, sweep_km, max_rows))
        return {"ok": True, "run": {"kept": 7}}
    monkeypatch.setattr(S, "run_scrape", fake)


def test_scan_is_refused_while_her_switch_is_off(hired, monkeypatch):
    from app.leads import pipeline as PL
    calls = []
    _fake_scrape(monkeypatch, calls)

    async def go():
        with pytest.raises(PL.DeskError, match="off"):
            PL.start_scan(T, "dentists near Pune", {"query": "dentists", "near": "Pune"})
    asyncio.run(go())
    assert calls == []                                   # the default stays OFF: nothing ran


def test_scan_starts_in_the_background_once_on(hired, monkeypatch):
    from app.leads import pipeline as PL
    from app.leads import service as S
    S.set_scrape_optin(T, True, "owner")
    calls = []
    _fake_scrape(monkeypatch, calls)

    async def go():
        r = PL.start_scan(T, "dentists near Pune", {"query": "dentists", "near": "Pune", "sweep_km": 50, "max_rows": 99999})
        assert r["started"] and "Nothing is sent" in r["note"]
        assert r["scan"]["sweep_km"] == 20 and r["scan"]["max_rows"] == 5000      # clamped to the limits
        with pytest.raises(PL.DeskError, match="already running"):
            PL.start_scan(T, "x", {"query": "cafe", "near": "Pune"})
        await PL._SCANS[T]
        assert not PL.scan_running(T)
        with pytest.raises(PL.DeskError, match="where"):
            PL.start_scan(T, "x", {"query": "cafe"})
    asyncio.run(go())
    assert calls == [(T, "dentists", "Pune", 20.0, 5000)]


def test_saved_scan_runs_weekly_only_while_on(hired, monkeypatch):
    from app.leads import pipeline as PL
    from app.leads import service as S
    calls = []
    _fake_scrape(monkeypatch, calls)
    w = PL.save_search(T, "Pune dentists", "SCRAPE", {"query": "dentists", "near": "Pune", "sweep_km": 4}, weekly=True)
    with pytest.raises(PL.DeskError):
        PL.save_search(T, "x", "SCRAPE", {"query": "cafe"})            # no place

    async def tick():
        n = await PL.weekly_tick()
        if PL._SCANS.get(T):
            await PL._SCANS[T]
        return n
    assert asyncio.run(tick()) == 0 and calls == []                  # switch off: skipped, nothing marked
    S.set_scrape_optin(T, True, "owner")
    assert asyncio.run(tick()) == 1
    assert calls == [(T, "dentists", "Pune", 4.0, 500)]
    sv = {x["id"]: x for x in PL.saved(T)}
    assert sv[w["id"]]["runs"] == 1 and sv[w["id"]]["last_kept"] == 7
    assert asyncio.run(tick()) == 0                                  # not twice in a week


def test_desk_route_and_chat_tool(hired, monkeypatch):
    from app.main import app
    from app.leads import pipeline as PL
    from app.leads import service as S
    from app.agent.leadsdesk_tools import leads_desk, LEADSDESK_TOOLS
    from app.agent.tools import Ctx, ToolError
    calls = []
    _fake_scrape(monkeypatch, calls)
    with TestClient(app) as c:
        assert c.post("/api/leads/desk/scan", json={"query": "dentists", "near": "Pune"}).status_code == 400
    with pytest.raises(ToolError, match="off"):
        asyncio.run(leads_desk(Ctx(T, "c1"), action="scan", query="dentists", near="Pune"))
    S.set_scrape_optin(T, True, "owner")
    with pytest.raises(ToolError):
        asyncio.run(leads_desk(Ctx(T, "c1", actor="customer:x"), action="scan", query="dentists", near="Pune"))

    async def go():
        r = await leads_desk(Ctx(T, "c1"), action="scan", query="dentists", near="Pune")
        assert r["started"]
        await PL._SCANS[T]
    asyncio.run(go())
    assert calls and calls[0][1:3] == ("dentists", "Pune")
    sch = LEADSDESK_TOOLS[0]["input_schema"]["properties"]
    assert "scan" in sch["action"]["enum"] and "SCRAPE" in sch["lane"]["enum"]


def test_the_chat_is_told_and_the_page_has_it(hired):
    from app import leadschat
    from app.leads import service as S
    S.set_scrape_optin(T, True, "owner")
    leadschat.forget(T)
    b = leadschat.block(T)
    assert "THE PUBLIC MAPS LISTINGS SCAN" in b and "leads_desk action=scan" in b and "Public Maps listings scan: ON" in b
    js = (ROOT / "server/app/static/console/leadsdesk.js").read_text()
    assert "/api/leads/desk/scan" in js and "Switch on the scan" in js and "Area across (km)" in js
