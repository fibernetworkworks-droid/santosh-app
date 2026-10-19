"""Santosh Agent Army: every row of the sheet is in, search/filters work, flags (licence, caution, WhatsApp) and API."""
import asyncio

import pytest

from app.bazar import agents as A


def test_all_rows_and_fields_loaded():
    st = A.stats()
    assert st["total"] == 36336
    assert st["tiers"] == {"A · proven": 63, "B · established": 11609, "C · early / niche": 20628, "D · unproven": 4036}
    assert len(st["fields"]) == 37 and st["curated"] == 1849
    assert sum(f["agents"] for f in st["fields"]) == 36336
    refs = {a[A.N] for a in A.agents()}
    assert len(refs) == 36336                     # nothing skipped or merged


def test_search_filters_and_ranking():
    r = A.search("coding", tier="A")
    assert r and all(x["tier"].startswith("A") for x in r) and any(x["name"] == "Cline" for x in r)
    acc = A.search(field="Accounting, tax & audit", limit=40)
    assert len(acc) == 40 and all("Accounting" in (x["field"] + x.get("also_fits", "")) for x in acc)
    fw = A.search("orchestration", kind="Framework / SDK", limit=5)
    assert all(x["kind"] == "Framework / SDK" for x in fw)
    assert A.search("composio")[0]["name"] == "composio"


def test_flags():
    n8n = A.search("n8n", limit=1)[0]
    assert n8n["name"] == "n8n" and "Sustainable Use" in n8n["licence_note"]
    sec = A.search(field="Cybersecurity", limit=5)
    assert all("caution" in x for x in sec)
    d = A.get("composio")
    assert d["link"].startswith("https://github.com/composiohq") and "packages" in d and "how_to_use" in d


def test_tool_and_api(env, monkeypatch):
    monkeypatch.setenv("API_KEY", "")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.agent.tools import Ctx, ToolError, dispatch
    out = asyncio.run(dispatch("agent_army", {"action": "search", "query": "voice call centre", "tier": "A,B"}, Ctx("default", "c")))
    assert out["agents"] and out["total_in_catalogue"] == 36336
    with pytest.raises(ToolError):
        asyncio.run(dispatch("agent_army", {"action": "details", "ref": "no-such-agent-xyz"}, Ctx("default", "c")))
    from fastapi.testclient import TestClient
    from app import main
    c = TestClient(main.app)
    j = c.get("/api/agents/directory", params={"q": "legal contract", "limit": 5}).json()
    assert j["total"] == 36336 and 0 < len(j["agents"]) <= 5
    assert c.get("/api/agents/fields").json()["total"] == 36336
    assert c.get("/api/agents/item/1").json()["name"] == "composio"
