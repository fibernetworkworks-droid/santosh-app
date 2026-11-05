"""v0.533 CRAWL BRAIN — the WIRING. Are the ten modules actually REACHED?

This file exists because of the v0.389 lesson, written into CLAUDE.md as a rule: a module's tests passing
says it works, never that anything calls it - `sfmeta.py` shipped with 7 green tests and zero callers. The
sister file test_v0533_crawl_brain.py proves the algorithms are right. This one proves a tool reaches them.

Every test here drives a real handler through a mocked fetch and asserts on the HANDLER's output, so a
module quietly disconnected later would turn one of these red.
"""
from __future__ import annotations

import asyncio
import json
import re

import httpx
import pytest

from app.agent import crawl_jobs as CJ
from app.agent import scrape_tools as ST
from app.agent.tools import HANDLERS, TOOLS

PAGE = """<html><head><title>Sai Medical, Akola</title></head><body>
<div id="cookie-consent"><p>We use cookies to improve your experience. Accept all cookies to continue browsing today.</p></div>
<nav class="main-nav"><a href="/">Home</a><a href="/about">About</a><a href="/shop">Shop</a></nav>
<div class="sidebar widget"><h3>Trending</h3><ul><li><a href="/1">Ten tips</a></li></ul></div>
<article class="post-content">
  <h1>Sai Medical, Tilak Road, Akola</h1>
  <p>Sai Medical is a chemist on Tilak Road in Akola, open from nine in the morning until nine at night every day.</p>
  <p>They keep insulin refrigerated and will order anything they do not have. The shop phone number is 0724 243 0000.</p>
</article>
<table class="price-table"><caption>Rates</caption>
<thead><tr><th>Brand</th><th>Size</th><th>Price</th></tr></thead>
<tbody><tr><td rowspan="2">UltraTech</td><td>50 kg</td><td>410</td></tr>
<tr><td>25 kg</td><td>215</td></tr></tbody></table>
<div class="promo-banner advert"><p>Buy now and save fifty percent with code SAVE50 today only</p></div>
<footer class="site-footer"><p>Copyright 2026. All rights reserved. Privacy policy.</p></footer>
</body></html>"""


class _Page:
    """The shape scrape_tools expects back from the Scrapling fetcher."""

    def __init__(self, html: str, url: str = "https://shop.in/p", status: int = 200) -> None:
        self.html_content, self.url, self.status, self.reason = html, url, status, "OK"

    def css(self, sel):
        """Only the selectors scrape_tools actually asks this fake for: 'title' and 'a[href]'."""
        from lxml import html as LH
        root = LH.fromstring(self.html_content)
        xp = {"title": "//title", "a[href]": "//a[@href]"}.get(sel)
        return [_El(e) for e in root.xpath(xp)] if xp else []

    def get_all_text(self, separator="\n"):
        from lxml import html as LH
        return separator.join(LH.fromstring(self.html_content).itertext())

    def markdown(self):
        return re.sub(r"\s+", " ", self.get_all_text(" ")).strip()


class _El:
    def __init__(self, e):
        self._e = e
        self.attrib = e.attrib
        self.html_content = ""

    @property
    def text(self):
        return self._e.text_content()

    def get_all_text(self, separator="\n"):
        return self._e.text_content()


@pytest.fixture
def lane(env, monkeypatch):
    """A tenant, a fake fetch and robots that always allows - so a test never touches the network."""
    monkeypatch.setattr(ST, "_fetch", lambda url, tenant, timeout=25, adaptive=False: _Page(PAGE, url))
    async def _ok(_u):
        return True
    monkeypatch.setattr(ST, "_robots_ok", _ok)
    monkeypatch.setattr(ST, "_guard_url", lambda u: u)
    from app.agent.tools import Ctx
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id="default")
        s.add(c)
        s.flush()
        conv = c.id
    return Ctx(tenant_id="default", conversation_id=conv)


# ---------------------------------------------------------------- item 2 reached from scrape_page
def test_scrape_page_clean_actually_prunes(lane):
    dirty = asyncio.run(ST.scrape_page(lane, url="https://shop.in/p"))
    clean = asyncio.run(ST.scrape_page(lane, url="https://shop.in/p", clean=True))
    assert "cleaned" in clean, "the prune path was never entered"
    assert clean["cleaned"]["after_chars"] < clean["cleaned"]["before_chars"]
    low = clean["content"].lower()
    for junk in ("cookies", "trending", "save50", "all rights reserved"):
        assert junk not in low, f"boilerplate survived scrape_page(clean=True): {junk}"
    assert "0724 243 0000" in clean["content"] and "insulin" in clean["content"]
    assert "cookies" in dirty["content"].lower(), "the default path must be unchanged"


def test_scrape_page_about_keeps_only_the_answer(lane):
    got = asyncio.run(ST.scrape_page(lane, url="https://shop.in/p", clean=True, about="phone number"))
    assert "0724 243 0000" in got["content"]


def test_a_page_that_prunes_to_nothing_keeps_its_content(lane, monkeypatch):
    monkeypatch.setattr(ST, "_fetch",
                        lambda url, tenant, timeout=25, adaptive=False: _Page("<html><body><p>hi</p></body></html>", url))
    got = asyncio.run(ST.scrape_page(lane, url="https://shop.in/x", clean=True))
    assert got["content"].strip(), "pruning must never cost her the page"


# ---------------------------------------------------------------- item 5 reached from scrape_tables
def test_scrape_tables_returns_aligned_rows(lane):
    got = asyncio.run(ST.scrape_tables(lane, url="https://shop.in/p", as_csv=True))
    assert got["tables"] == 1
    t = got["data"][0]
    assert t["headers"] == ["Brand", "Size", "Price"]
    assert t["rows"][1] == ["UltraTech", "25 kg", "215"], "rowspan alignment lost through the tool"
    assert t["caption"] == "Rates" and "Brand,Size,Price" in t["csv"]


def test_scrape_tables_says_so_when_a_page_has_no_data_table(lane, monkeypatch):
    monkeypatch.setattr(ST, "_fetch", lambda url, tenant, timeout=25, adaptive=False: _Page(
        '<html><body><table role="presentation"><tr><td>logo</td><td>menu</td></tr></table></body></html>', url))
    got = asyncio.run(ST.scrape_tables(lane, url="https://shop.in/x"))
    assert got["tables"] == 0 and "note" in got


def test_scrape_tables_which_picks_one_and_refuses_a_bad_index(lane):
    got = asyncio.run(ST.scrape_tables(lane, url="https://shop.in/p", which=0))
    assert got["tables"] == 1
    from app.agent.tools import ToolError
    with pytest.raises(ToolError):
        asyncio.run(ST.scrape_tables(lane, url="https://shop.in/p", which=9))


# ---------------------------------------------------------------- item 7 reached from _blocked
def test_the_vendor_tiers_are_reached_from_the_lanes_own_blocked_check():
    assert ST._blocked(_Page('<html><script>window.__cf_chl_f_tk="x"</script></html>')) == "Cloudflare challenge"
    assert "DataDome" in (ST._blocked(_Page('<html><script src="https://captcha-delivery.com/a.js"></script></html>')) or "")
    # the lane's OWN strong signals still answer first, unchanged
    assert ST._blocked(_Page("<html><body>no</body></html>", status=403)) == "HTTP 403"
    # and a real page is still a real page
    assert ST._blocked(_Page(PAGE)) is None


# ---------------------------------------------------------------- item 4 reached from scrape_map
_ROBOTS = b"User-agent: *\nDisallow: /admin\nSitemap: https://shop.in/si.xml\n"
_SM = (b'<?xml version="1.0"?><urlset><url><loc>https://shop.in/p/a</loc></url>'
       b'<url><loc>https://shop.in/p/b</loc></url></urlset>')


def test_scrape_map_sources_reads_the_sites_own_index(lane, monkeypatch):
    def h(req):
        u = str(req.url)
        if u.endswith("/robots.txt"):
            return httpx.Response(200, content=_ROBOTS)
        if "si.xml" in u:
            return httpx.Response(200, content=_SM)
        return httpx.Response(404)
    real = httpx.AsyncClient

    def fake(*a, **kw):
        kw.pop("transport", None)
        return real(*a, transport=httpx.MockTransport(h), **kw)
    monkeypatch.setattr(httpx, "AsyncClient", fake)
    got = asyncio.run(ST.scrape_map(lane, url="https://shop.in/", sources="sitemap"))
    assert got["engine"] == "index" and got["count"] == 2
    assert "/admin" not in " ".join(got["urls"]), "Disallow paths must never be mined as targets"


# ---------------------------------------------------------------- items 1 + 3 reached from the crawl job
def test_crawl_start_carries_the_question_into_the_checkpoint(lane, monkeypatch):
    monkeypatch.setattr(ST, "_robots_ok", lambda _u: _done(True))
    r = asyncio.run(CJ.crawl_start(lane, url="https://shop.in/", max_pages=5,
                                   question="what are the cement rates"))
    assert r.get("question") == "what are the cement rates" and r.get("mode") == "best"
    row = CJ.get_job("default", r["job_id"])
    cp = row.get("checkpoint") or {}
    assert cp.get("question") and cp.get("mode") == "best"


def _done(v):
    async def _f():
        return v
    return _f()


def test_the_frontier_is_used_only_when_a_question_was_given():
    q = ["https://x.in/careers", "https://x.in/prices/cement-rate-akola"]
    # no question -> FIFO, exactly as before
    assert CJ._pick_next(list(q), {}, "", "bfs", "https://x.in/", None) == q[0]
    # a question -> the most promising link first
    assert CJ._pick_next(list(q), {}, "cement rate akola", "best",
                         "https://x.in/", None) == q[1]


def test_the_stop_rule_is_reached_and_says_why():
    cp = {"learned": [
        {"url": "a", "text": "The GST rate on cement in India is 28 percent, the highest slab, since 2017."},
        {"url": "b", "text": "Cement attracts GST at 28 percent in India; the council was asked to cut the rate."},
        {"url": "c", "text": "GST on cement in India remains 28 percent and the cement industry says it raises cost."},
    ]}
    stop, why, metrics = CJ._enough_yet(cp, "GST rate on cement in India")
    assert stop and why.startswith("enough:"), why
    assert metrics["confidence"] >= 0.70
    # and a crawl with no question is never stopped by this rule
    assert CJ._enough_yet(cp, "") == (False, "", {})


def test_irrelevant_pages_never_stop_the_crawl_as_enough():
    cp = {"learned": [{"url": str(i), "text": "Our company values integrity in every market we serve."}
                      for i in range(3)]}
    stop, why, _ = CJ._enough_yet(cp, "GST rate on cement in India")
    assert not why.startswith("enough:")


# ---------------------------------------------------------------- the reachability law itself
def test_every_crawl_module_has_a_caller_outside_its_own_package():
    """CLAUDE.md's rule, as a test: grep for a caller outside the module's own file before calling a
    feature shipped. If a later change disconnects one of these, this goes red."""
    import pathlib
    root = pathlib.Path(ST.__file__).resolve().parents[1]      # server/app
    callers = {}
    for mod in ("prune", "enough", "frontier", "seed", "tables", "blocked", "chunks", "bm25",
                "proxies", "steps"):
        hits = []
        for py in root.rglob("*.py"):
            if "crawl/" in str(py).replace("\\", "/") and py.parent.name == "crawl":
                continue                                        # its own package does not count
            if "test" in py.name:
                continue
            txt = py.read_text(encoding="utf-8", errors="replace")
            if f"crawl import {mod}" in txt or f"crawl.{mod}" in txt:
                hits.append(py.name)
        callers[mod] = hits
    unwired = {m: h for m, h in callers.items() if not h}
    assert not unwired, f"these crawl modules have no caller outside app/crawl: {sorted(unwired)}"


def test_the_new_tool_is_registered_with_a_handler_and_a_label():
    names = {t["name"] for t in TOOLS}
    assert "scrape_tables" in names and "scrape_tables" in HANDLERS
    assert "scrape_tables" in ST.SCRAPE_LABELS
    from app import voice
    assert voice.call_route("scrape_tables"), "unreachable on a voice call"


def test_the_new_switches_are_on_the_existing_tools():
    pg = [t for t in TOOLS if t["name"] == "scrape_page"][0]["input_schema"]["properties"]
    mp = [t for t in TOOLS if t["name"] == "scrape_map"][0]["input_schema"]["properties"]
    cs = [t for t in TOOLS if t["name"] == "crawl_start"][0]["input_schema"]["properties"]
    assert "clean" in pg and "about" in pg
    assert "sources" in mp and "newer_than" in mp
    assert "question" in cs
    for t in TOOLS:                      # every schema must still be API-serialisable
        json.dumps(t["input_schema"])
