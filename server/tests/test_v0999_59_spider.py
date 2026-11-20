"""v0.999.59 HOOLA SPIDER - Scrapy's way of crawling inside Hoola, offline.

Fetches are monkeypatched to local scrapling Responses; robots via the monkeypatched gate; sleeps removed."""
import asyncio
import shutil
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401

from app import spider as SP
from app.agent import scrape_tools as st
from app.agent.tools import Ctx, TOOLS, HANDLERS, FAMILY_OF

CTX = Ctx(tenant_id="spider-t1", conversation_id="c1")
BASE = "https://93.184.216.34"


def _list_page(n, nxt=True):
    cards = "".join(f'<article class="p"><h3><a href="/item/{n}-{i}" title="Book {n}-{i}">B</a></h3>'
                    f'<p class="price">₹{100 + i}.50</p></article>' for i in range(3))
    more = f'<li class="next"><a href="/page/{n + 1}?utm_source=x">next</a></li>' if nxt else ""
    return (f"<html><head><title>Page {n}</title></head><body>{cards}<ul>{more}</ul>"
            f'<a href="https://elsewhere.com/x">out</a><a href="/item/{n}-0">dup</a></body></html>')


def _resp(html, url, status=200):
    from scrapling.engines.toolbelt.custom import Response
    return Response(url=url, content=html, status=status, reason="OK", cookies={}, headers={},
                    request_headers={}, _log=False)


SPEC = {"name": "books", "start_urls": [f"{BASE}/page/1"],
        "item": {"container": "article.p", "fields": {"title": "h3 a::attr(title)", "price": ".price|number",
                                                        "link": "h3 a::attr(href)|url"}},
        "next_page": "li.next a", "max_pages": 10, "pipelines": {"required": ["title"], "dedup": "link"}}


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    shutil.rmtree(Path("data") / "scraping" / CTX.tenant_id, ignore_errors=True)

    async def _nosleep(*_a, **_k):
        return None
    monkeypatch.setattr(SP, "_sleep", _nosleep)
    monkeypatch.setattr(st, "_robots_allowed", lambda *a, **k: True)
    st._ROBOTS_CACHE.clear()
    SP._RUNNING.clear()
    yield
    shutil.rmtree(Path("data") / "scraping" / CTX.tenant_id, ignore_errors=True)


def _site(monkeypatch, pages, calls=None):
    def fake(url, tenant_id, *a, **k):
        if calls is not None:
            calls.append(url)
        key = url.split("?")[0]
        if key not in pages:
            return _resp("<html><body>nope</body></html>", url, 404)
        v = pages[key]
        return v(url) if callable(v) else _resp(v, url)
    monkeypatch.setattr(st, "_fetch", fake)


def _run_all():
    async def go():
        for _ in range(5):
            await SP.tick()
            await SP.drain()
    asyncio.run(go())


def test_registered_and_family():
    assert len(TOOLS) == 634 and "spider" in HANDLERS and FAMILY_OF["spider"] == "spider"


def test_spec_refuses_login_and_bad_bits():
    for bad in ({"start_urls": [BASE], "fields": {"a": "h1"}, "cookies": {"x": 1}},
                {"start_urls": [BASE], "fields": {"a": "h1"}, "follow": [{"allow": "(", "headers": {}}]},
                {"start_urls": ["ftp://x"], "fields": {"a": "h1"}},
                {"start_urls": [BASE], "fields": {"a": "h1|explode"}},
                {"start_urls": [BASE], "fields": {}}):
        with pytest.raises(SP.SpiderError):
            SP.validate(bad)
    clean = SP.validate({"start_urls": [BASE], "fields": {"a": "h1"}, "max_pages": 99999})
    assert clean["max_pages"] == SP.MAX_PAGES and clean["allowed_domains"] == ["93.184.216.34"]


def test_canonical_drops_tracking_and_fragment():
    assert SP.fingerprint("https://A.com/x?b=2&utm_source=z&a=1#top") == SP.fingerprint("https://a.com/x?a=1&b=2")


def test_check_one_page_saves_nothing(monkeypatch):
    _site(monkeypatch, {f"{BASE}/page/1": _list_page(1)})
    out = asyncio.run(HANDLERS["spider"](CTX, action="check", spec=SPEC))
    assert out["ok"] and out["items_found"] == 3
    assert out["sample"][0]["price"] == 100.5 and out["sample"][0]["link"] == f"{BASE}/item/1-0"
    assert out["fields_always_empty"] == []
    assert not (Path("data") / "scraping" / CTX.tenant_id / "spider.db").exists() or SP.list_spiders(CTX.tenant_id) == []


def test_full_run_paginates_dedups_offsite_and_exports(monkeypatch):
    calls = []
    _site(monkeypatch, {f"{BASE}/page/{n}": _list_page(n, nxt=n < 3) for n in (1, 2, 3)}, calls)
    asyncio.run(HANDLERS["spider"](CTX, action="save", spec=SPEC))
    r = asyncio.run(HANDLERS["spider"](CTX, action="run", name="books"))
    assert r["new"] and r["status"] == "queued"
    again = asyncio.run(HANDLERS["spider"](CTX, action="run", name="books"))
    assert again["new"] is False and again["run_id"] == r["run_id"]
    _run_all()
    s = asyncio.run(HANDLERS["spider"](CTX, action="status"))
    assert s["status"] == "done" and s["items"] == 9 and s["pages_read"] == 3
    assert "finished" in s["close_reason"]
    assert all("elsewhere.com" not in c for c in calls)
    items = asyncio.run(HANDLERS["spider"](CTX, action="items", limit=50))
    assert items["total"] == 9 and items["items"][0]["_url"].startswith(BASE)
    data, ext = SP.export_bytes(items["items"], "csv")
    assert ext == ".csv" and b"Book 1-0" in data
    x, ext2 = SP.export_bytes(items["items"], "xlsx")
    assert ext2 == ".xlsx" and x[:2] == b"PK"


def test_robots_and_limits(monkeypatch):
    _site(monkeypatch, {f"{BASE}/page/{n}": _list_page(n) for n in range(1, 30)})
    SP.save_spider(CTX.tenant_id, SPEC | {"max_items": 4})
    SP.start_run(CTX.tenant_id, "books")
    _run_all()
    run = SP.get_run(CTX.tenant_id)
    assert run["stats"]["items"] == 4 and "item limit" in run["close_reason"]
    monkeypatch.setattr(st, "_robots_allowed", lambda *a, **k: False)
    st._ROBOTS_CACHE.clear()
    SP.save_spider(CTX.tenant_id, SPEC | {"name": "b2"})
    SP.start_run(CTX.tenant_id, "b2")
    _run_all()
    r2 = SP.get_run(CTX.tenant_id)
    assert r2["stats"]["robots_skipped"] == 1 and r2["stats"]["items"] == 0


def test_retry_then_success(monkeypatch):
    hits = {"n": 0}

    def flaky(url):
        hits["n"] += 1
        return _resp("busy", url, 503) if hits["n"] == 1 else _resp(_list_page(1, nxt=False), url)
    _site(monkeypatch, {f"{BASE}/page/1": flaky})
    SP.save_spider(CTX.tenant_id, SPEC)
    SP.start_run(CTX.tenant_id, "books")
    _run_all()
    run = SP.get_run(CTX.tenant_id)
    assert run["stats"]["retries"] == 1 and run["stats"]["items"] == 3
    assert run["checkpoint"]["delays"]["93.184.216.34"] >= 1.0


def test_stop(monkeypatch):
    _site(monkeypatch, {f"{BASE}/page/1": _list_page(1)})
    SP.save_spider(CTX.tenant_id, SPEC)
    r = SP.start_run(CTX.tenant_id, "books")
    out = asyncio.run(HANDLERS["spider"](CTX, action="stop", run_id=r["id"]))
    assert out["stopped"] and out["status"] == "stopped"


def test_formula_guard_in_csv():
    data, _ = SP.export_bytes([{"a": "=HYPERLINK(1)"}], "csv")
    assert b"'=HYPERLINK" in data
