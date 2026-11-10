"""v0.758 NEWS IN THE BOX (owner: "lets do next" after data.gov.in went live): newsdata.io + gnews.io on ONE server key
each (NEWSDATA_API_KEY / GNEWS_API_KEY in the VPS .env), never in any app, never to the model. Offline (MockTransport)."""
import asyncio
from urllib.parse import parse_qs, urlparse

import httpx

from app.config import get_settings
from app.publicapis import box as BX
from app.publicapis import service as S


def _mock(monkeypatch, seen):
    from app import web
    monkeypatch.setattr(S, "_transport", httpx.MockTransport(
        lambda req: (seen.append(str(req.url)), httpx.Response(200, json={"status": "success", "results": [{"title": "t"}],
                                                                           "articles": [{"title": "t"}]}))[1]))
    monkeypatch.setattr(web, "_public_host", lambda host: None)


def test_india_news_on_the_newsdata_server_key(env, monkeypatch):
    seen = []
    monkeypatch.setattr(get_settings(), "newsdata_api_key", "nd-key-1234")
    _mock(monkeypatch, seen)
    r = asyncio.run(BX.call("t1", "aaj ki news hindi mein", {"language": "hi"}))
    assert r["ok"] and r["api"]["recipe"] == "news_india" and "nd-key-1234" not in str(r)
    q = parse_qs(urlparse(seen[0]).query)
    assert q["apikey"] == ["nd-key-1234"] and q["country"] == ["in"] and q["language"] == ["hi"]


def test_gnews_search_and_headlines_on_their_own_key(env, monkeypatch):
    seen = []
    monkeypatch.setattr(get_settings(), "gnews_api_key", "gn-key-1234")
    _mock(monkeypatch, seen)
    r = asyncio.run(BX.call("t1", "news about monsoon", {"query": "monsoon"}, api="news_search"))
    assert r["ok"] and urlparse(seen[0]).path == "/api/v4/search"
    assert parse_qs(urlparse(seen[0]).query)["apikey"] == ["gn-key-1234"]
    r = asyncio.run(BX.call("t1", "top headlines", {"category": "business"}, api="news_headlines"))
    assert r["ok"] and parse_qs(urlparse(seen[1]).query)["category"] == ["business"]


def test_no_news_key_says_which_env_line_is_missing(env, monkeypatch):
    seen = []
    monkeypatch.setattr(get_settings(), "newsdata_api_key", "")
    _mock(monkeypatch, seen)
    r = asyncio.run(BX.call("t1", "latest news", api="news_india"))
    assert not r["ok"] and seen == [] and "NEWSDATA_API_KEY" in r["tried"][0]["key_needed"]


def test_a_big_news_answer_is_slimmed_never_cut_off_text(env, monkeypatch):
    from app import web
    big = {"status": "success", "totalResults": 900, "nextPage": "x",
           "results": [{"title": f"t{i}", "link": f"https://n.example/{i}", "description": "d" * 2000, "content": "c" * 9000,
                        "source_name": "Src", "category": ["top", "business"], "pubDate": "2026-11-10"} for i in range(40)]}
    monkeypatch.setattr(get_settings(), "newsdata_api_key", "nd-key-1234")
    monkeypatch.setattr(S, "_transport", httpx.MockTransport(lambda req: httpx.Response(200, json=big)))
    monkeypatch.setattr(web, "_public_host", lambda host: None)
    r = asyncio.run(BX.call("t1", "latest news", api="news_india"))
    d = r["data"]
    assert r["ok"] and isinstance(d, dict) and d["shown"] == 10 and d["totalResults"] == 900 and "nextPage" not in d
    first = d["results"][0]
    assert first["title"] == "t0" and "content" not in first and len(first["description"]) == 301
    assert first["category"] == "top, business"
