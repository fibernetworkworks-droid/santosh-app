"""v0.484.0 FIRECRAWL CORE - our own Firecrawl, house-sized, on the v0.474 Scrapling lane.

Owner: "CAN WE BUILD OUR OWN FIRECRAWL FOR HOOLA" -> "BUILD".

Four ideas taken from the Firecrawl engine read (design only, ZERO Firecrawl code - engine is AGPL):
- scrape: ONE door with the auto-waterfall - fast HTTP first, on a block signature (401/403/429 or a
  Cloudflare-style challenge) it escalates ITSELF to the stealth browser (when enabled on the server).
- scrape_map: links-only discovery (their /map) - a few pages fetched, same-site urls harvested, no content.
- per-tenant page cache with max_age (their index engine): repeat reads served with zero outbound,
  write-through on every successful page read, LRU-capped, css/include_links bypass (they need the DOM).
- scrape_extract_json: schema -> JSON rows through ONE capped brain call (their /extract idea on the house
  brain, the coder-observer cheap-brain-first pattern).

Everything runs OFFLINE: fetches monkeypatched to local scrapling Responses, robots via a prefilled
cache, the brain via a stub. SSRF guard, robots gate, caps, cache semantics and the stealth gate are
tested for real.
"""
import asyncio
import shutil
import sqlite3
import time
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401  (the env fixture: fresh DB, dry-run WhatsApp)

from app.agent import scrape_tools as st
from app.agent.tools import Ctx, TOOLS, HANDLERS, TOOL_LABELS

CTX = Ctx(tenant_id="fc-test-tenant", conversation_id="c1")
CTX2 = Ctx(tenant_id="fc-other-tenant", conversation_id="c2")

BASE = "https://93.184.216.34"

CARD_HTML = """
<html><head><title>All products | Books to Scrape</title></head><body>
<div id="main">
  <article class="product_pod"><h3><a href="p1.html" title="A Light in the Attic">A Light in the Attic</a></h3>
    <p class="price_color">£51.77</p></article>
  <article class="product_pod"><h3><a href="p2.html" title="Tipping the Velvet">Tipping the Velvet</a></h3>
    <p class="price_color">£53.74</p></article>
</div></body></html>
"""

CHALLENGE_HTML = """
<html><head><title>Just a moment...</title></head><body>
<div class="main-wrapper">Checking your browser before accessing. challenge-platform/H/b</div>
</body></html>
"""

LONG_ARTICLE = ("<html><head><title>How CAPTCHAs work</title></head><body><p>" + ("lorem ipsum dolor sit amet " * 400)
                + " sometimes a captcha appears </p></body></html>")

MAP_HTML = """
<html><head><title>Site</title></head><body>
<a href="/products/a">A</a><a href="/products/b">B</a><a href="/about">About</a>
<a href="https://external.com/x">Ext</a><a href="mailto:x@y.z">M</a><a href="#top">Frag</a>
<a href="javascript:void(0)">Js</a>
</body></html>
"""


def _resp(html=CARD_HTML, url=f"{BASE}/", status=200):
    from scrapling.engines.toolbelt.custom import Response
    return Response(url=url, content=html, status=status, reason="OK" if status < 400 else "Forbidden",
                    cookies={}, headers={}, request_headers={}, _log=False)


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _clean_state():
    """Every test starts with empty robots cache + empty tenant caches (the cache is shared state)."""
    st._ROBOTS_CACHE.clear()
    for t in (CTX.tenant_id, CTX2.tenant_id):
        _wipe_cache(t)
    yield
    st._ROBOTS_CACHE.clear()
    for t in (CTX.tenant_id, CTX2.tenant_id):
        _wipe_cache(t)


def _wipe_cache(tenant):
    shutil.rmtree(Path("data") / "scraping" / tenant, ignore_errors=True)


def _allow_robots(monkeypatch):
    monkeypatch.setattr(st, "_robots_allowed", lambda *a, **k: True)


def _stealth_on(monkeypatch):
    monkeypatch.setenv("SCRAPE_STEALTH_ENABLED", "true")
    from app.config import get_settings
    get_settings.cache_clear()


def _stealth_off(monkeypatch):
    monkeypatch.setenv("SCRAPE_STEALTH_ENABLED", "false")
    from app.config import get_settings
    get_settings.cache_clear()


# ---------------------------------------------------------------- registry

def test_registry_8_tools():
    names = {t["name"] for t in st.SCRAPE_TOOLS}
    assert names == {"scrape_page", "scrape_extract", "scrape_many", "scrape_site", "scrape_stealth",
                     "scrape", "scrape_map", "scrape_extract_json"}
    assert set(st.SCRAPE_LABELS) == set(st.SCRAPE_HANDLERS) == names
    global_names = {t["name"] for t in TOOLS}
    assert names <= global_names
    for n in names:
        assert n in HANDLERS and n in TOOL_LABELS, n


# ---------------------------------------------------------------- block detection

def test_blocked_by_status():
    assert st._blocked(_resp(status=403)) == "HTTP 403"
    assert st._blocked(_resp(status=401)) == "HTTP 401"
    assert st._blocked(_resp(status=429)) == "HTTP 429"


def test_blocked_by_challenge_title_and_script():
    assert "challenge title" in st._blocked(_resp(CHALLENGE_HTML))
    small = "<html><body>enable javascript and cookies to continue</body></html>"
    assert "challenge script" in st._blocked(_resp(small))


def test_blocked_clean_pages_pass():
    assert st._blocked(_resp()) is None
    # the false-positive guard: a LONG article that merely mentions captcha never counts as a block
    assert st._blocked(_resp(LONG_ARTICLE)) is None


# ---------------------------------------------------------------- the waterfall door (scrape)

def test_scrape_clean_page_no_escalation(monkeypatch):
    _allow_robots(monkeypatch)
    _stealth_on(monkeypatch)

    def _boom(*a, **k):
        raise AssertionError("stealth must NOT be tried on a clean page")
    monkeypatch.setattr(st, "_stealth_fetch", _boom)
    monkeypatch.setattr(st, "_fetch", lambda *a, **k: _resp())
    out = _run(st.scrape(CTX, f"{BASE}/"))
    assert out["engine"] == "http" and out["escalated"] is False and out["status"] == 200
    assert "Books to Scrape" in out["content"]


def test_scrape_escalates_on_block_when_enabled(monkeypatch):
    _allow_robots(monkeypatch)
    _stealth_on(monkeypatch)
    calls = {"http": 0, "stealth": 0}

    def _http(url, tenant, timeout=25, adaptive=False):
        calls["http"] += 1
        return _resp(CHALLENGE_HTML, status=403)

    def _stealth(url, timeout=90, wait_selector="", solve_cloudflare=False):
        calls["stealth"] += 1
        return _resp(CARD_HTML)

    monkeypatch.setattr(st, "_fetch", _http)
    monkeypatch.setattr(st, "_stealth_fetch", _stealth)
    out = _run(st.scrape(CTX, f"{BASE}/"))
    assert out["engine"] == "stealth" and out["escalated"] is True
    assert calls == {"http": 1, "stealth": 1}
    assert "Books to Scrape" in out["content"]


def test_scrape_honest_refusal_when_stealth_disabled(monkeypatch):
    _allow_robots(monkeypatch)
    _stealth_off(monkeypatch)
    monkeypatch.setattr(st, "_fetch", lambda *a, **k: _resp(CHALLENGE_HTML, status=403))
    with pytest.raises(Exception) as e:
        _run(st.scrape(CTX, f"{BASE}/"))
    msg = str(e.value)
    assert "block kiya" in msg and "scrape_stealth_enabled" in msg


def test_scrape_stealth_still_blocked_reports(monkeypatch):
    _allow_robots(monkeypatch)
    _stealth_on(monkeypatch)
    monkeypatch.setattr(st, "_fetch", lambda *a, **k: _resp(CHALLENGE_HTML, status=403))
    monkeypatch.setattr(st, "_stealth_fetch", lambda *a, **k: _resp(CHALLENGE_HTML, status=403))
    with pytest.raises(Exception) as e:
        _run(st.scrape(CTX, f"{BASE}/"))
    assert "advance mode" in str(e.value)


def test_scrape_never_mode_is_http_only(monkeypatch):
    _allow_robots(monkeypatch)
    _stealth_on(monkeypatch)
    monkeypatch.setattr(st, "_stealth_fetch",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("never means never")))
    monkeypatch.setattr(st, "_fetch", lambda *a, **k: _resp(status=403))
    with pytest.raises(Exception) as e:
        _run(st.scrape(CTX, f"{BASE}/", stealth="never"))
    assert "403" in str(e.value)


def test_scrape_always_mode_needs_the_setting(monkeypatch):
    _allow_robots(monkeypatch)
    _stealth_off(monkeypatch)
    with pytest.raises(Exception) as e:
        _run(st.scrape(CTX, f"{BASE}/", stealth="always"))
    assert "scrape_stealth_enabled" in str(e.value)


def test_scrape_stealth_is_semaphored(monkeypatch):
    _allow_robots(monkeypatch)
    _stealth_on(monkeypatch)
    monkeypatch.setattr(st, "_fetch", lambda *a, **k: _resp(CHALLENGE_HTML, status=403))
    assert st._STEALTH_SEM.acquire(blocking=False) is True
    try:
        with pytest.raises(Exception) as e:
            _run(st.scrape(CTX, f"{BASE}/"))
        assert "already chal raha hai" in str(e.value)
    finally:
        st._STEALTH_SEM.release()


def test_scrape_ssrf_guard(monkeypatch):
    for bad in ("http://127.0.0.1/x", "http://169.254.169.254/meta", "http://192.168.1.5/x"):
        with pytest.raises(Exception):
            _run(st.scrape(CTX, bad))


# ---------------------------------------------------------------- the page cache

def _wipe_cache(tenant):
    shutil.rmtree(Path("data") / "scraping" / tenant, ignore_errors=True)


def test_cache_roundtrip_and_isolation():
    _wipe_cache(CTX.tenant_id)
    _wipe_cache(CTX2.tenant_id)
    st._cache_put(CTX.tenant_id, f"{BASE}/a", 200, "T", "# md", "plain text")
    hit = st._cache_get(CTX.tenant_id, f"{BASE}/a", 600)
    assert hit and hit["title"] == "T" and hit["markdown"] == "# md" and hit["text"] == "plain text"
    assert 0 <= hit["age"] <= 5
    assert st._cache_get(CTX2.tenant_id, f"{BASE}/a", 600) is None      # per-tenant isolation
    assert st._cache_get(CTX.tenant_id, f"{BASE}/b", 600) is None       # unknown url
    _wipe_cache(CTX.tenant_id)
    _wipe_cache(CTX2.tenant_id)


def test_cache_expiry_and_max_age_gate():
    _wipe_cache(CTX.tenant_id)
    st._cache_put(CTX.tenant_id, f"{BASE}/old", 200, "T", "md", "txt")
    db = Path("data") / "scraping" / CTX.tenant_id / "cache.db"
    con = sqlite3.connect(str(db))
    con.execute("UPDATE page_cache SET fetched_at = ?", (time.time() - 9999,))
    con.commit()
    con.close()
    assert st._cache_get(CTX.tenant_id, f"{BASE}/old", 600) is None      # expired
    assert st._cache_get(CTX.tenant_id, f"{BASE}/old", 99999) is not None  # still inside a bigger window
    assert st._cache_get(CTX.tenant_id, f"{BASE}/old", None) is None     # None = never read
    assert st._cache_get(CTX.tenant_id, f"{BASE}/old", 0) is None        # 0 = always fresh
    _wipe_cache(CTX.tenant_id)


def test_cache_disabled_by_setting(monkeypatch):
    _wipe_cache(CTX.tenant_id)
    st._cache_put(CTX.tenant_id, f"{BASE}/x", 200, "T", "md", "txt")
    monkeypatch.setenv("SCRAPE_CACHE_ENABLED", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    try:
        assert st._cache_get(CTX.tenant_id, f"{BASE}/x", 600) is None
    finally:
        get_settings.cache_clear()


def test_cache_lru_cap():
    _wipe_cache(CTX.tenant_id)
    for i in range(st._CACHE_ROWS + 5):
        st._cache_put(CTX.tenant_id, f"{BASE}/p{i}", 200, "t", "md", "txt")
    con = sqlite3.connect(str(Path("data") / "scraping" / CTX.tenant_id / "cache.db"))
    n = con.execute("SELECT COUNT(*) FROM page_cache").fetchone()[0]
    con.close()
    assert n == st._CACHE_ROWS, "the LRU cap must hold"
    _wipe_cache(CTX.tenant_id)


def test_cache_write_through_and_cache_serve(monkeypatch):
    _wipe_cache(CTX.tenant_id)
    _allow_robots(monkeypatch)
    monkeypatch.setattr(st, "_fetch", lambda *a, **k: _resp())
    out = _run(st.scrape_page(CTX, f"{BASE}/"))                        # write-through on success
    assert out.get("engine") != "cache"
    monkeypatch.setattr(st, "_fetch",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")))
    out = _run(st.scrape_page(CTX, f"{BASE}/", max_age=600))            # served from cache
    assert out["engine"] == "cache" and out["cached"] is True and "Books to Scrape" in out["content"]
    with pytest.raises(Exception):                                      # css needs the live DOM
        _run(st.scrape_page(CTX, f"{BASE}/", css="h1", max_age=600))
    out = _run(st.scrape(CTX, f"{BASE}/"))                              # the new door reads the cache by default
    assert out["engine"] == "cache"
    monkeypatch.setattr(st, "_fetch", lambda *a, **k: _resp())          # back online for the fresh read
    out = _run(st.scrape(CTX, f"{BASE}/", max_age=0))                   # 0 = always fresh
    assert out["engine"] == "http"
    _wipe_cache(CTX.tenant_id)


# ---------------------------------------------------------------- scrape_map

def test_scrape_map_harvests_same_host_only(monkeypatch):
    _allow_robots(monkeypatch)
    monkeypatch.setattr(st, "_fetch", lambda *a, **k: _resp(MAP_HTML))
    out = _run(st.scrape_map(CTX, f"{BASE}/", max_pages=1))
    urls = out["urls"]
    assert f"{BASE}/" in urls and f"{BASE}/products/a" in urls and f"{BASE}/about" in urls
    assert all(u.startswith(BASE) for u in urls), "external/mailto/js urls never enter the map"
    assert out["pages_fetched"] == 1


def test_scrape_map_walks_the_queue(monkeypatch):
    _allow_robots(monkeypatch)
    pages = {
        f"{BASE}/": _resp('<html><body><a href="/p2">next</a></body></html>'),
        f"{BASE}/p2": _resp('<html><body><a href="/p3">deep</a></body></html>', url=f"{BASE}/p2"),
    }
    monkeypatch.setattr(st, "_fetch", lambda u, *a, **k: pages.get(u, _resp(url=u)))
    out = _run(st.scrape_map(CTX, f"{BASE}/", max_pages=2))
    assert f"{BASE}/p2" in out["urls"] and f"{BASE}/p3" in out["urls"], "the BFS must walk past page one"
    assert out["pages_fetched"] == 2


def test_scrape_map_include_regex_and_cap(monkeypatch):
    _allow_robots(monkeypatch)
    monkeypatch.setattr(st, "_fetch", lambda *a, **k: _resp(MAP_HTML))
    out = _run(st.scrape_map(CTX, f"{BASE}/", include="product"))
    assert f"{BASE}/products/a" in out["urls"] and f"{BASE}/about" not in out["urls"]
    out = _run(st.scrape_map(CTX, f"{BASE}/", max_urls=2))
    assert out["urls_found"] == 2


def test_scrape_map_respects_robots(monkeypatch):
    from protego import Protego
    monkeypatch.setattr("scrapling.fetchers.Fetcher.get",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")))
    st._ROBOTS_CACHE.clear()
    st._ROBOTS_CACHE["93.184.216.34"] = (
        time.time() + 999, Protego.parse("User-agent: *\nDisallow: /about\n"))
    try:
        monkeypatch.setattr(st, "_fetch", lambda *a, **k: _resp(MAP_HTML))
        out = _run(st.scrape_map(CTX, f"{BASE}/"))
        assert f"{BASE}/about" not in out["urls"]
        assert out["skipped_by_robots"] == 1
    finally:
        st._ROBOTS_CACHE.clear()


def test_scrape_map_ssrf(monkeypatch):
    with pytest.raises(Exception):
        _run(st.scrape_map(CTX, "http://10.0.0.1/"))


# ---------------------------------------------------------------- scrape_extract_json

def test_extract_json_parses_fenced_array(monkeypatch):
    _allow_robots(monkeypatch)
    monkeypatch.setattr(st, "_fetch", lambda *a, **k: _resp())

    async def _brain(system, user):
        return 'Here you go:\n```json\n[{"product": "A Light in the Attic", "price": "£51.77"}]\n```', "cheap:test"
    monkeypatch.setattr(st, "_extract_brain", _brain)
    out = _run(st.scrape_extract_json(CTX, f"{BASE}/", schema={"type": "array"}))
    assert out["count"] == 1 and out["data"][0]["product"] == "A Light in the Attic"
    assert out["brain"] == "cheap:test" and out["status"] == 200


def test_extract_json_balanced_slice_and_schema_prompt(monkeypatch):
    _allow_robots(monkeypatch)
    monkeypatch.setattr(st, "_fetch", lambda *a, **k: _resp())
    captured = {}

    async def _brain(system, user):
        captured["system"] = system
        captured["user"] = user
        return 'Sure! The data: {"total": 2, "items": [1, 2]} hope that helps', "cheap:test"
    monkeypatch.setattr(st, "_extract_brain", _brain)
    out = _run(st.scrape_extract_json(CTX, f"{BASE}/",
                                      schema={"type": "object", "properties": {"total": {"type": "integer"}}}))
    assert out["data"]["total"] == 2
    assert '"type": "object"' in captured["user"], "the schema must ride in the prompt"
    assert "Output ONLY valid JSON" in captured["system"] or "JSON" in captured["system"]


def test_extract_json_garbage_refused_honestly(monkeypatch):
    _allow_robots(monkeypatch)
    monkeypatch.setattr(st, "_fetch", lambda *a, **k: _resp())

    async def _brain(system, user):
        return "Sorry, I did not find anything.", "cheap:test"
    monkeypatch.setattr(st, "_extract_brain", _brain)
    with pytest.raises(Exception) as e:
        _run(st.scrape_extract_json(CTX, f"{BASE}/"))
    assert "JSON" in str(e.value)


def test_extract_json_limit_cap(monkeypatch):
    _allow_robots(monkeypatch)
    monkeypatch.setattr(st, "_fetch", lambda *a, **k: _resp())

    async def _brain(system, user):
        return "[" + ",".join('{"n": %d}' % i for i in range(80)) + "]", "cheap:test"
    monkeypatch.setattr(st, "_extract_brain", _brain)
    out = _run(st.scrape_extract_json(CTX, f"{BASE}/"))
    assert out["count"] == 50, "rows cap is 50 - the cost law"


def test_extract_json_ssrf(monkeypatch):
    with pytest.raises(Exception):
        _run(st.scrape_extract_json(CTX, "http://192.168.0.10/x"))


# ---------------------------------------------------------------- version pin

def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.707.0"
    from pathlib import Path
    pub = Path(__file__).resolve().parents[2] / "pubspec.yaml"
    assert "0.707.0+706" in pub.read_text()
