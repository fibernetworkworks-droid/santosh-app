"""v0.478.0 SCRAPLING - Hoola can scrape any website smoothly.

Owner: "NOW DEPLOY THIS SCRAPER FOR HOOLA --- THUS HOOLA CAN SCRAP ANY WEBSITE SMOOTHLY".

New tool module agent/scrape_tools.py (Scrapling, PyPI v0.5, BSD-3-Clause) - the structured/bulk
scraping lane open_website/browse_web never had: scrape_page (fast TLS-impersonated HTTP read),
scrape_extract (css/xpath -> JSON rows, ADAPTIVE per-tenant element memory that survives site
redesigns), scrape_many (same selector on up to 15 pages), scrape_site (polite same-host crawl,
max 25 pages), scrape_stealth (real-browser last resort, OFF unless scrape_stealth_enabled).

Everything here runs OFFLINE: fetches are monkeypatched to local scrapling Responses, robots via
a prefilled cache. The SSRF guard, robots gate, caps and stealth gate are tested for real.
"""
import asyncio
import time

import pytest

from tests.test_bazar import bz  # noqa: F401  (the env fixture: fresh DB, dry-run WhatsApp)

from app.agent import scrape_tools as st
from app.agent.tools import Ctx, TOOLS, HANDLERS, TOOL_LABELS

CTX = Ctx(tenant_id="tenant a/b@d", conversation_id="c1")

CARD_HTML = """
<html><head><title>All products | Books to Scrape</title></head><body>
<div id="main">
  <article class="product_pod"><h3><a href="p1.html" title="A Light in the Attic">A Light in the Attic</a></h3>
    <p class="price_color">£51.77</p></article>
  <article class="product_pod"><h3><a href="p2.html" title="Tipping the Velvet">Tipping the Velvet</a></h3>
    <p class="price_color">£53.74</p></article>
  <article class="product_pod"><h3><a href="p3.html" title="Soumission">Soumission</a></h3>
    <p class="price_color">£50.10</p></article>
  <a href="/about.html">About us</a><a href="javascript:void(0)">bad</a>
</div></body></html>
"""


def _resp(html=CARD_HTML, url="https://93.184.216.34/", status=200):
    from scrapling.engines.toolbelt.custom import Response
    return Response(url=url, content=html, status=status, reason="OK" if status < 400 else "Not Found",
                    cookies={}, headers={}, request_headers={}, _log=False)


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------- registry

def test_registry_wired():
    names = {t["name"] for t in st.SCRAPE_TOOLS}
    # v0.481 grew the lane: scrape (auto-waterfall door), scrape_map, scrape_extract_json joined
    # v0.537 grew it again: scrape_tables (a page's DATA tables as aligned rows, not flattened text)
    assert names == {"scrape_page", "scrape_extract", "scrape_many", "scrape_site", "scrape_stealth",
                     "scrape", "scrape_map", "scrape_extract_json", "scrape_tables"}
    assert set(st.SCRAPE_LABELS) == set(st.SCRAPE_HANDLERS) == names
    global_names = {t["name"] for t in TOOLS}
    assert names <= global_names, "scrape tools must be registered in the global registry"
    for n in names:
        assert n in HANDLERS and n in TOOL_LABELS, n


def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.616.0"
    from pathlib import Path
    pub = Path(__file__).resolve().parents[2] / "pubspec.yaml"
    assert "0.616.0+622" in pub.read_text()


# ---------------------------------------------------------------- SSRF guard

@pytest.mark.parametrize("bad", [
    "http://127.0.0.1/x", "http://10.1.2.3/x", "http://172.16.0.9/x", "http://192.168.1.1/x",
    "http://169.254.169.254/latest/meta-data/", "http://[::1]/x", "http://0.0.0.0/x",
    "ftp://books.example.in/x", "file:///etc/passwd", "", "   ",
])
def test_ssrf_guard_blocks_private_and_junk(bad):
    with pytest.raises(Exception) as e:
        st._guard_url(bad)
    assert "scraping" in str(e.value).lower() or "http" in str(e.value).lower() or "resolve" in str(e.value).lower() or "link" in str(e.value).lower() or "website" in str(e.value).lower()


def test_ssrf_guard_passes_public():
    assert st._guard_url("93.184.216.34/x") == "https://93.184.216.34/x"
    assert st._guard_url("http://93.184.216.34:8080/a?b=1") == "http://93.184.216.34:8080/a?b=1"


# ---------------------------------------------------------------- robots gate

def test_robots_gate_on_off_and_fail_open(monkeypatch):
    from protego import Protego
    monkeypatch.setattr("scrapling.fetchers.Fetcher.get",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")))   # no real network anywhere
    u = "https://93.184.216.34/private/list"
    st._ROBOTS_CACHE.clear()
    st._ROBOTS_CACHE["93.184.216.34"] = (
        time.time() + 999,
        Protego.parse("User-agent: *\nDisallow: /private/\nAllow: /public/\n"))
    assert st._robots_allowed(u) is False                       # disallowed path refused
    assert st._robots_allowed("https://93.184.216.34/public/list") is True
    st._ROBOTS_CACHE.clear()                                     # no robots cached -> fetch fails -> fail open
    assert st._robots_allowed(u) is True
    monkeypatch.setenv("SCRAPE_RESPECT_ROBOTS", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    try:
        assert st._robots_allowed(u) is True                     # setting off = gate off
    finally:
        get_settings.cache_clear()


# ---------------------------------------------------------------- extraction core

def test_field_value_syntax():
    page = _resp()
    el = page.css("article.product_pod")[0]
    assert st._field_value(el, "h3 a@title") == "A Light in the Attic"
    assert st._field_value(el, "p.price_color") == "£51.77"
    assert st._field_value(el, "@href") is None                   # el itself has no href; None, not a crash
    a = page.css("article.product_pod h3 a")[0]
    assert st._field_value(a, "@href") == "p1.html"
    assert st._field_value(el, "") is None


def test_scrape_extract_rows_offline(monkeypatch):
    monkeypatch.setattr(st, "_fetch", lambda *a, **k: _resp())
    monkeypatch.setattr(st, "_robots_allowed", lambda *a, **k: True)
    out = _run(st.scrape_extract(CTX, "https://93.184.216.34/", "article.product_pod",
                                 fields={"title": "h3 a@title", "price": "p.price_color", "link": "h3 a@href"},
                                 identifier="product_cards"))
    assert out["count"] == 3 and out["status"] == 200 and out["adaptive"] is True
    assert out["rows"][0] == {"title": "A Light in the Attic", "price": "£51.77", "link": "p1.html"}
    assert " Adaptive" in out["note"] or "Adaptive" in out["note"]


def test_scrape_extract_similar_expands(monkeypatch):
    monkeypatch.setattr(st, "_fetch", lambda *a, **k: _resp())
    monkeypatch.setattr(st, "_robots_allowed", lambda *a, **k: True)
    out = _run(st.scrape_extract(CTX, "https://93.184.216.34/", "article.product_pod:first-child",
                                 similar=True, adaptive=False))
    assert out["count"] == 3, "one matched card must expand to all its siblings"


def test_scrape_extract_xpath(monkeypatch):
    monkeypatch.setattr(st, "_fetch", lambda *a, **k: _resp())
    monkeypatch.setattr(st, "_robots_allowed", lambda *a, **k: True)
    out = _run(st.scrape_extract(CTX, "https://93.184.216.34/", "xpath://article[@class='product_pod']/h3/a", attr="title"))
    assert out["count"] == 3 and out["rows"][0] == {"title": "A Light in the Attic"}


def test_scrape_extract_404_refused(monkeypatch):
    monkeypatch.setattr(st, "_fetch", lambda *a, **k: _resp(status=404))
    monkeypatch.setattr(st, "_robots_allowed", lambda *a, **k: True)
    with pytest.raises(Exception) as e:
        _run(st.scrape_extract(CTX, "https://93.184.216.34/", "article"))
    assert "404" in str(e.value)


# ---------------------------------------------------------------- page flow

def test_scrape_page_markdown_links_css(monkeypatch):
    monkeypatch.setattr(st, "_fetch", lambda *a, **k: _resp())
    monkeypatch.setattr(st, "_robots_allowed", lambda *a, **k: True)
    out = _run(st.scrape_page(CTX, "93.184.216.34", include_links=True, max_chars=5000))
    assert out["status"] == 200 and "Books to Scrape" in out["title"]
    assert "A Light in the Attic" in out["content"]
    hrefs = [l["href"] for l in out["links"]]
    assert "https://93.184.216.34/about.html" in hrefs and all("javascript:" not in h for h in hrefs)
    focussed = _run(st.scrape_page(CTX, "https://93.184.216.34/", css="p.price_color", format="text"))
    assert "£53.74" in focussed["content"] and "Tipping" not in focussed["content"]


def test_cap_truncates():
    assert st._cap("short", 100) == "short"
    long = "x" * 300
    assert st._cap(long, 100).startswith("x" * 100) and "truncated" in st._cap(long, 100)


def test_storage_path_tenant_safe(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    p = st._storage_path(CTX.tenant_id)
    assert p.startswith("data/scraping/") and p.endswith("elements.db")
    assert "/" not in p.split("scraping/")[1][:-len("/elements.db")], "tenant part must be sanitised"
    from pathlib import Path
    assert Path(p).parent.exists()


# ---------------------------------------------------------------- many + site

def test_scrape_many_isolates_errors_and_caps(monkeypatch):
    monkeypatch.setattr(st, "_robots_allowed", lambda *a, **k: True)
    state = {"n": 0}

    def fake_fetch(url, tenant, timeout, adaptive=False):
        state["n"] += 1
        if "dead" in url:
            raise RuntimeError("connection refused")
        return _resp(url=url)

    monkeypatch.setattr(st, "_fetch", fake_fetch)
    urls = [f"https://93.184.216.34/p?i={i}" for i in range(14)] + ["https://93.184.216.34/dead"] + ["https://93.184.216.34/p?i=15"]
    out = _run(st.scrape_many(CTX, urls, "article.product_pod", fields={"t": "h3 a@title"}))
    assert out["pages"] == 15, "16 urls given, cap 15"
    assert out["pages_ok"] == 14
    dead = [r for r in out["results"] if "dead" in r["url"]][0]
    assert dead.get("error") and "rows" not in dead
    assert all(len(r.get("rows", [])) == 3 for r in out["results"] if "rows" in r)


def test_scrape_site_crawls_same_host_only(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    pages = {
        "https://93.184.216.34/": _resp("<html><head><title>Home</title></head><body>welcome "
                                        "<a href='/list.html'>list</a> <a href='https://198.51.100.7/x'>ext</a> "
                                        "<a href='#frag'>f</a></body></html>", url="https://93.184.216.34/"),
        "https://93.184.216.34/list.html": _resp("<html><head><title>List</title></head><body>items here "
                                                 "<a href='https://93.184.216.34/deep.html'>deep</a></body></html>",
                                                 url="https://93.184.216.34/list.html"),
        "https://93.184.216.34/deep.html": _resp("<html><head><title>Deep</title></head><body>deep page</body></html>",
                                                 url="https://93.184.216.34/deep.html"),
    }
    monkeypatch.setattr(st, "_fetch", lambda u, *a, **k: pages[u])
    monkeypatch.setattr(st, "_robots_allowed", lambda *a, **k: True)
    out = _run(st.scrape_site(CTX, "https://93.184.216.34/", max_pages=10))
    got = [p["url"] for p in out["pages"]]
    assert "https://93.184.216.34/list.html" in got and "https://93.184.216.34/deep.html" in got
    assert all("198.51.100.7" not in g for g in got), "same-host only"
    inc = _run(st.scrape_site(CTX, "https://93.184.216.34/", max_pages=10, include="deep"))
    assert [p["url"] for p in inc["pages"]] == ["https://93.184.216.34/"], "include filters the frontier"


# ---------------------------------------------------------------- stealth gate

def test_stealth_gate_off_by_default(monkeypatch):
    monkeypatch.setenv("SCRAPE_STEALTH_ENABLED", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    try:
        with pytest.raises(Exception) as e:
            _run(st.scrape_stealth(CTX, "https://93.184.216.34/"))
        assert "scrape_stealth_enabled" in str(e.value) and "scrapling install" in str(e.value)
    finally:
        get_settings.cache_clear()


def test_stealth_gate_on_runs_offline_browser(monkeypatch):
    """Setting on: the handler must reach StealthyFetcher with our caps (semaphore released afterwards)."""
    monkeypatch.setenv("SCRAPE_STEALTH_ENABLED", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    try:
        seen = {}

        class _FakeSF:
            @staticmethod
            def fetch(url, **kw):
                seen.update(url=url, kw=kw)
                assert kw["headless"] is True and kw["timeout"] <= 180 * 1000, "stealth timeout is milliseconds (scrapling 0.5), capped at 180 s"
                return _resp()

        monkeypatch.setattr(st, "_STEALTH_SEM", __import__("threading").BoundedSemaphore(1))
        import scrapling.fetchers as F
        monkeypatch.setattr(F, "StealthyFetcher", _FakeSF)
        monkeypatch.setattr(st, "_robots_allowed", lambda *a, **k: True)
        out = _run(st.scrape_stealth(CTX, "https://93.184.216.34/", solve_cloudflare=True))
        assert out["engine"] == "scrapling-stealth" and "Books to Scrape" in out["title"]
        assert seen["kw"]["solve_cloudflare"] is True
        assert st._STEALTH_SEM._value == 1, "semaphore must be released after the run"
    finally:
        get_settings.cache_clear()
