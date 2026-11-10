"""v0.754 KEYED BOX (owner: the key list -> "Open Government India (data.gov.in) -- GOT THIS" -> "I HAVE NOT PUT ANY KEY
IN APP --- IT SHOULD NOT SEEN IN APP --- IT IS FOR HOOLA FOR ALL USER").

A box recipe may need a key. data.gov.in has ONE server key (DATA_GOV_IN_API_KEY in the VPS .env) used for every user:
nothing in any app, never shown to the model, placed where the API's own docs say (query `api-key`). No key = the box
skips the recipe and says the server owner must add it. All offline (MockTransport)."""
import asyncio
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from app.config import get_settings
from app.publicapis import box as BX
from app.publicapis import service as S

GOV = "government-open-government-india"


def _mock(handler, monkeypatch):
    from app import web
    monkeypatch.setattr(S, "_transport", httpx.MockTransport(handler))
    monkeypatch.setattr(web, "_public_host", lambda host: None)


@pytest.fixture
def server_key(monkeypatch):
    monkeypatch.setattr(get_settings(), "data_gov_in_api_key", "srv-key-1234")


def test_without_the_server_key_the_mandi_recipe_is_skipped_and_says_how(env, monkeypatch):
    seen = []
    monkeypatch.setattr(get_settings(), "data_gov_in_api_key", "")
    _mock(lambda req: (seen.append(str(req.url)), httpx.Response(200, json={}))[1], monkeypatch)
    r = asyncio.run(BX.call("t1", "onion mandi bhav", {"commodity": "Onion"}, api="mandi_price"))
    assert not r["ok"] and seen == []
    t = r["tried"][0]
    assert t["recipe"] == "mandi_price" and "DATA_GOV_IN_API_KEY" in t["key_needed"] and "Never ask" in t["key_needed"]


def test_one_server_key_serves_every_user_in_the_right_place(env, monkeypatch, server_key):
    seen = []

    def handler(req):
        seen.append(str(req.url))
        return httpx.Response(200, json={"total": 1, "records": [{"market": "Akola", "commodity": "Onion",
                                                                  "modal_price": "1800"}]})
    _mock(handler, monkeypatch)
    for tenant in ("t1", "someone-else"):                                     # no user saved anything in any app
        r = asyncio.run(BX.call(tenant, "aaj onion ka mandi bhav", {"commodity": "Onion", "state": "Maharashtra",
                                                                  "district": "Akola"}))
        assert r["ok"] and r["api"]["recipe"] == "mandi_price" and r["data"]["records"][0]["modal_price"] == "1800"
        assert "srv-key-1234" not in str(r)                                   # the key never reaches the model
    q = parse_qs(urlparse(seen[0]).query)
    assert q["api-key"] == ["srv-key-1234"] and len(seen) == 2
    assert q["filters[commodity]"] == ["Onion"] and q["filters[district]"] == ["Akola"] and q["limit"] == ["20"]


def test_a_filter_value_cannot_add_its_own_parameter(env, monkeypatch, server_key):
    seen = []
    _mock(lambda req: (seen.append(str(req.url)), httpx.Response(200, json={"records": []}))[1], monkeypatch)
    asyncio.run(BX.call("t1", "mandi", {"commodity": "Onion&api-key=evil"}, api="mandi_price"))
    q = parse_qs(urlparse(seen[0]).query)
    assert q["api-key"] == ["srv-key-1234"] and q["filters[commodity]"] == ["Onion&api-key=evil"]


def test_any_gov_dataset_by_resource_id(env, monkeypatch, server_key):
    seen = []
    _mock(lambda req: (seen.append(str(req.url)), httpx.Response(200, json={"records": [{"a": 1}]}))[1], monkeypatch)
    r = asyncio.run(BX.call("t1", "data.gov.in dataset", {"resource_id": "abc-123"}, api="india_gov_dataset"))
    assert r["ok"] and urlparse(seen[0]).path == "/resource/abc-123"
    from app.agent import publicapi_tools as P
    assert "mandi_price" in P.PUBLICAPI_TOOLS[0]["description"]
