"""v0.348 MOSPI BUILT IN: official Government of India statistics from MoSPI's own MCP for every user (no Connect tap),
routed by statistics words, guide says MoSPI not a search summary, big answers trimmed by whole rows."""
import asyncio
import json

import pytest

CPI = {"data": [{"base_year": "2024", "year": "2026", "month": "September", "state": "All India", "sector": "Combined",
                 "division": "CPI (General)", "group": None, "index": "109.49", "inflation": "5.54"},
                {"base_year": "2024", "year": "2026", "month": "September", "state": "All India", "sector": "Combined",
                 "division": "Food and beverages", "group": None, "index": "111.77", "inflation": "7.36"}],
       "msg": "Data fetched successfully"}


@pytest.fixture
def fake(env, monkeypatch):
    from app import mospi as ms
    ms._CACHE.clear()
    calls = []

    async def rpc(name, args, timeout=60.0):
        calls.append((name, args))
        if name == "get_data":
            return {"content": [{"type": "text", "text": json.dumps(CPI)}]}
        return {"structuredContent": {"datasets": {"CPI": {"name": "Consumer Price Index"}}}}
    monkeypatch.setattr(ms, "_rpc", rpc)
    return calls


def _ctx():
    from app.agent.tools import Ctx
    return Ctx(tenant_id="default", conversation_id="c1")


def test_cpi_comes_from_mospi_with_source(fake):
    from app.agent import tools
    out = asyncio.run(tools.HANDLERS["mospi"](_ctx(), action="data", dataset="cpi",
                                              filters={"base_year": "2024", "year": 2026, "state_code": "1", "x": None}))
    rows = json.loads(out["result"])["data"]
    assert rows[0]["inflation"] == "5.54" and "group" not in rows[0]          # empty fields dropped
    assert out["source"].startswith("MoSPI") and "Do not add numbers" in out["note"]
    name, args = fake[0]
    assert name == "get_data" and args["dataset"] == "CPI"
    assert args["filters"] == {"base_year": "2024", "year": 2026, "state_code": "1", "limit": "50"}
    asyncio.run(tools.HANDLERS["mospi"](_ctx(), action="data", dataset="CPI",
                                        filters={"base_year": "2024", "year": 2026, "state_code": "1"}))
    assert len(fake) == 1                                                       # cached


def test_steps_need_a_dataset_and_a_known_action(fake):
    from app.agent import tools
    with pytest.raises(tools.ToolError, match="dataset"):
        asyncio.run(tools.HANDLERS["mospi"](_ctx(), action="metadata"))
    with pytest.raises(tools.ToolError, match="action"):
        asyncio.run(tools.HANDLERS["mospi"](_ctx(), action="delete"))
    out = asyncio.run(tools.HANDLERS["mospi"](_ctx(), action="datasets"))
    assert "Consumer Price Index" in out["result"] and fake[-1] == ("list_datasets", {})


def test_big_answers_drop_whole_rows(fake):
    from app.agent import mospi_tools as mt
    big = {"data": [{"i": n, "text": "x" * 200} for n in range(400)]}
    out, dropped = mt._compact(big)
    assert dropped > 0 and len(json.dumps(out)) <= mt.MAX_CHARS and out["data"][0]["i"] == 0


def test_routed_read_only_and_guide_scoped(env):
    from app.agent import admit, draftcheck, prompts, tools
    from app.agent.santosh import PARALLEL_SAFE
    assert tools.FAMILY_OF["mospi"] == "mospi" and "mospi" in PARALLEL_SAFE and draftcheck._is_read("mospi")
    for ask in ("India ki latest CPI inflation kitni hai?", "GDP growth rate kya hai", "Maharashtra mein berozgari",
                "mehngai kitni badhi", "WPI ka latest data", "PLFS unemployment rate"):
        assert "mospi" in admit.route(ask), ask
    for ask in ("Rahul ko mail bhejo", "kal ka mausam", "meri meeting kab hai"):
        assert "mospi" not in admit.route(ask), ask
    assert "call `mospi`" in prompts.system_text({"mospi"}) and "call `mospi`" not in prompts.system_text({"email"})


def test_featured_card_says_built_in(env):
    from app.bazar import featured
    c = featured.get("mospi")
    assert c["native"] and "built in" in c["native"] and featured.public(c)["native"]


def test_switch_off(env, monkeypatch):
    monkeypatch.setenv("MOSPI_ENABLED", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.agent import tools
    with pytest.raises(tools.ToolError, match="off"):
        asyncio.run(tools.HANDLERS["mospi"](_ctx(), action="datasets"))


def test_network_failure_is_retried_once_and_named(env, monkeypatch):
    """v0.349: the live server's call failed with 'MoSPI did not respond'; one retry, the exact reason kept + logged."""
    import httpx

    from app import mospi as ms
    ms._CACHE.clear()
    tries = []

    class Boom:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json=None, headers=None):
            tries.append(headers.get("User-Agent", ""))
            raise httpx.ConnectTimeout("timed out")

    async def no_sleep(_):
        return None
    monkeypatch.setattr(ms.httpx, "AsyncClient", Boom)
    monkeypatch.setattr(ms.asyncio, "sleep", no_sleep)
    with pytest.raises(ms.MospiError, match="timeout"):
        asyncio.run(ms.call("datasets"))
    assert len(tries) == 2 and tries[0].startswith("Hoola/")          # retried once; not python-httpx's default UA
    assert ms.LAST_ERROR["why"].startswith("timeout") and ms.check()["ok"] is False
