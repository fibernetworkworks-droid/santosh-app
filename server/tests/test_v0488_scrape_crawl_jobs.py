"""v0.492.0 CRAWL JOBS - the background crawl lane (the Firecrawl /crawl idea, house-sized).

Owner: "PHASE 2 END TO END".

The lane: crawl_start queues a per-tenant crawl job (data/scraping/<tenant>/crawl.db), the worker tick
(worker.scrape_crawl_jobs -> crawl_jobs.tick, ~20 s) claims it and runs a checkpointed polite same-site
BFS - HTTP only, robots honoured per url, SSRF guarded per url, one heartbeat per page, stop between
pages, stalled jobs resumed from their checkpoint, tries then failed - and every successful page lands
in the v0.481 per-tenant PAGE cache as write-through (the crawl warms the scrape door's cache).

Everything runs OFFLINE: fetches monkeypatched to local scrapling Responses, robots via the monkeypatched
gate, politeness shrunk to 0. SSRF, robots, budget caps, checkpoint/resume, stop, tries and the tools'
pagination are tested for real.
"""
import asyncio
import json
import shutil
import sqlite3
import time
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401  (the env fixture: fresh DB, dry-run WhatsApp)

from app.agent import crawl_jobs as cj
from app.agent import scrape_tools as st
from app.agent.tools import Ctx, TOOLS, HANDLERS, TOOL_LABELS

CTX = Ctx(tenant_id="cj-test-tenant", conversation_id="c1")
CTX2 = Ctx(tenant_id="cj-other-tenant", conversation_id="c2")

BASE = "https://93.184.216.34"

CARD_HTML = """
<html><head><title>All products | Books to Scrape</title></head><body>
<div id="main">
  <a href="/products/a">A</a><a href="/products/b">B</a><a href="/about">About</a>
  <a href="https://external.com/x">Ext</a><a href="mailto:x@y.z">M</a><a href="#top">Frag</a>
  <a href="javascript:void(0)">Js</a>
</div></body></html>
"""

PRODUCTS_HTML = """
<html><head><title>Products</title></head><body>
<a href="/products/a">A</a><a href="/products/b">B</a><a href="/about">nope</a>
</body></html>
"""

CHALLENGE_HTML = """
<html><head><title>Just a moment...</title></head><body>
<div>Checking your browser. challenge-platform/H/b</div>
</body></html>
"""


def _resp(html=CARD_HTML, url=f"{BASE}/", status=200):
    from scrapling.engines.toolbelt.custom import Response
    return Response(url=url, content=html, status=status, reason="OK" if status < 400 else "Forbidden",
                    cookies={}, headers={}, request_headers={}, _log=False)


def _run(coro):
    return asyncio.run(coro)


def _wipe(tenant):
    shutil.rmtree(Path("data") / "scraping" / tenant, ignore_errors=True)


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    """Every test: empty robots cache, empty tenant dirs, no in-process jobs, no politeness sleeps."""
    monkeypatch.setattr(cj, "_polite_s", 0)
    st._ROBOTS_CACHE.clear()
    cj._RUNNING.clear()
    for t in (CTX.tenant_id, CTX2.tenant_id):
        _wipe(t)
    yield
    st._ROBOTS_CACHE.clear()
    cj._RUNNING.clear()
    for t in (CTX.tenant_id, CTX2.tenant_id):
        _wipe(t)


def _allow_robots(monkeypatch):
    monkeypatch.setattr(st, "_robots_allowed", lambda *a, **k: True)


def _page_map(monkeypatch, pages: dict, calls: list | None = None):
    """pages: url -> Response. Redirects: the Response carries its own final url."""

    def _fetch(url, tenant, timeout=25, adaptive=False):
        if calls is not None:
            calls.append(url)
        r = pages.get(url)
        if r is None:
            raise RuntimeError(f"offline: {url}")
        return r
    monkeypatch.setattr(st, "_fetch", _fetch)


# ---------------------------------------------------------------- registry

def test_registry_3_crawl_tools():
    names = {t["name"] for t in cj.CRAWL_TOOLS}
    assert names == {"crawl_start", "crawl_status", "crawl_results"}
    assert set(cj.CRAWL_LABELS) == set(cj.CRAWL_HANDLERS) == names
    global_names = {t["name"] for t in TOOLS}
    assert names <= global_names
    for n in names:
        assert n in HANDLERS and n in TOOL_LABELS, n
    assert len(TOOLS) == 554, "526 (v0.487, dev BYOX included) + 3 crawl tools + 1 uiux_design + 2 officehours + 3 code-graph + 1 docs7 + 5 dhara (v0.502) + 1 magic21 (v0.512) + 1 dhara_dsl (their v0.514) + 10 construction (v0.522) + 1 crew_run (v0.523)"


# ---------------------------------------------------------------- crawl_start / the queue

def test_crawl_start_queues_a_job_and_clamps_budget(monkeypatch):
    _allow_robots(monkeypatch)
    out = _run(cj.crawl_start(CTX, f"{BASE}/", max_pages=55))
    assert out["status"] == "queued" and out["job_id"].startswith("cj_")
    assert out["max_pages"] == 50, "the hard page budget cap is 50"
    row = cj.get_job(CTX.tenant_id, out["job_id"])
    assert row["seed"] == f"{BASE}/" and row["tries"] == 0
    cp = row["checkpoint"]
    assert cp["queue"] == [f"{BASE}/"], "the frontier starts with the seed"


def test_crawl_start_dedupes_same_seed(monkeypatch):
    _allow_robots(monkeypatch)
    a = _run(cj.crawl_start(CTX, f"{BASE}/"))
    b = _run(cj.crawl_start(CTX, f"{BASE}/"))
    assert a["job_id"] == b["job_id"], "one seed, one queued job"
    assert b["already_running"] is True
    c = _run(cj.crawl_start(CTX, f"{BASE}/other"))
    assert c["job_id"] != a["job_id"]


def test_crawl_start_ssrf_refused():
    with pytest.raises(Exception):
        _run(cj.crawl_start(CTX, "http://127.0.0.1/"))
    with pytest.raises(Exception):
        _run(cj.crawl_start(CTX, "http://169.254.169.254/meta"))


def test_crawl_start_robots_refused(monkeypatch):
    from protego import Protego
    st._ROBOTS_CACHE.clear()
    st._ROBOTS_CACHE["93.184.216.34"] = (time.time() + 999, Protego.parse("User-agent: *\nDisallow: /\n"))
    try:
        with pytest.raises(Exception) as e:
            _run(cj.crawl_start(CTX, f"{BASE}/"))
        assert "robots.txt" in str(e.value)
    finally:
        st._ROBOTS_CACHE.clear()


def test_crawl_start_disabled_setting(monkeypatch):
    monkeypatch.setenv("SCRAPE_CRAWL_ENABLED", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    try:
        with pytest.raises(Exception) as e:
            _run(cj.crawl_start(CTX, f"{BASE}/"))
        assert "scrape_crawl_enabled" in str(e.value)
    finally:
        get_settings.cache_clear()


# ---------------------------------------------------------------- candidates + claim

def test_candidates_finds_queued_not_fresh_running():
    row = cj.create_job(CTX.tenant_id, f"{BASE}/")
    cands = cj.candidates(180)
    assert (CTX.tenant_id, row["id"]) in cands
    cj._save(CTX.tenant_id, row["id"], status="running", updated_at=time.time())   # fresh heartbeat
    assert (CTX.tenant_id, row["id"]) not in cj.candidates(180), "a live running job is nobody's business"
    cj._save(CTX.tenant_id, row["id"], updated_at=time.time() - 999)               # stalled
    assert (CTX.tenant_id, row["id"]) in cj.candidates(180), "a stalled running job is picked up"


def test_candidates_tenant_isolation():
    row = cj.create_job(CTX.tenant_id, f"{BASE}/")
    cj.create_job(CTX2.tenant_id, f"{BASE}/2")
    cands = dict((jid, tenant) for tenant, jid in cj.candidates(180))
    assert cands.get(row["id"]) == CTX.tenant_id, "the job belongs to ITS tenant"
    assert len(cands) == 2


def test_claim_counts_tries_and_fails_honestly():
    row = cj.create_job(CTX.tenant_id, f"{BASE}/")
    assert cj.claim(CTX.tenant_id, row["id"], 3) is True
    assert cj.get_job(CTX.tenant_id, row["id"])["tries"] == 1
    assert cj.claim(CTX.tenant_id, row["id"], 3) is True       # the stall-pickup claims a running job too
    assert cj.claim(CTX.tenant_id, row["id"], 3) is True
    j = cj.get_job(CTX.tenant_id, row["id"])
    assert j["tries"] == 3 and j["status"] == "running"
    assert cj.claim(CTX.tenant_id, row["id"], 3) is False      # tries exhausted
    j = cj.get_job(CTX.tenant_id, row["id"])
    assert j["status"] == "failed" and "tries" in j["error"]


# ---------------------------------------------------------------- the runner

def test_run_job_crawls_bfs_and_warms_the_page_cache(monkeypatch):
    _allow_robots(monkeypatch)
    calls: list[str] = []
    pages_map = {
        f"{BASE}/": _resp(CARD_HTML),
        f"{BASE}/products/a": _resp("<html><head><title>A</title></head><body>page a</body></html>",
                                    url=f"{BASE}/products/a"),
        f"{BASE}/products/b": _resp('<html><body><a href="/products/a">back</a></body></html>',
                                    url=f"{BASE}/products/b"),
        f"{BASE}/about": _resp("<html><body>about</body></html>", url=f"{BASE}/about"),
    }
    _page_map(monkeypatch, pages_map, calls)
    row = cj.create_job(CTX.tenant_id, f"{BASE}/")
    cj.claim(CTX.tenant_id, row["id"], 3)
    _run(cj.run_job(CTX.tenant_id, row["id"]))
    j = cj.get_job(CTX.tenant_id, row["id"])
    assert j["status"] == "done" and j["pages_done"] == 4, f"seed + a + b + about, got {j['pages_done']}"
    stored, total = cj.pages(CTX.tenant_id, row["id"], 0, 10)
    assert total == 4 and [r["seq"] for r in stored] == [1, 2, 3, 4]
    assert stored[0]["title"] == "All products | Books to Scrape"
    hit = st._cache_get(CTX.tenant_id, f"{BASE}/", 600)
    assert hit is not None, "the crawl write-through warms the v0.481 page cache"
    assert calls.count(f"{BASE}/") == 1, "no page is fetched twice"


def test_run_job_include_regex_and_same_host_only(monkeypatch):
    _allow_robots(monkeypatch)
    pages_map = {
        f"{BASE}/": _resp(PRODUCTS_HTML),
        f"{BASE}/products/a": _resp("<html><body>a</body></html>", url=f"{BASE}/products/a"),
        f"{BASE}/products/b": _resp("<html><body>b</body></html>", url=f"{BASE}/products/b"),
    }
    _page_map(monkeypatch, pages_map)
    row = cj.create_job(CTX.tenant_id, f"{BASE}/", include="product")
    cj.claim(CTX.tenant_id, row["id"], 3)
    _run(cj.run_job(CTX.tenant_id, row["id"]))
    stored, total = cj.pages(CTX.tenant_id, row["id"], 0, 50)
    urls = {r["url"] for r in stored}
    assert f"{BASE}/about" not in urls and total == 3, "include regex keeps only /product/ urls"
    assert all(u.startswith(BASE) for u in urls), "external links never enter the crawl"


def test_run_job_max_pages_budget(monkeypatch):
    _allow_robots(monkeypatch)
    deep = {f"{BASE}/": _resp('<html><body><a href="/p1">1</a></body></html>')}
    for i in range(1, 6):
        deep[f"{BASE}/p{i}"] = _resp(f'<html><body><a href="/p{i + 1}">next</a></body></html>',
                                     url=f"{BASE}/p{i}")
    _page_map(monkeypatch, deep)
    row = cj.create_job(CTX.tenant_id, f"{BASE}/", max_pages=2)
    cj.claim(CTX.tenant_id, row["id"], 3)
    _run(cj.run_job(CTX.tenant_id, row["id"]))
    j = cj.get_job(CTX.tenant_id, row["id"])
    assert j["status"] == "done" and j["fetched"] == 2 and j["pages_done"] == 2
    assert len(j["checkpoint"]["queue"]) > 0, "the frontier stops, it is not drained past the budget"


def test_run_job_robots_skips_counted(monkeypatch):
    from protego import Protego
    monkeypatch.setattr("scrapling.fetchers.Fetcher.get",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")))
    st._ROBOTS_CACHE.clear()
    st._ROBOTS_CACHE["93.184.216.34"] = (
        time.time() + 999, Protego.parse("User-agent: *\nDisallow: /private\n"))
    try:
        pages_map = {
            f"{BASE}/": _resp('<html><body><a href="/private/x">p</a><a href="/open">o</a></body></html>'),
            f"{BASE}/open": _resp("<html><body>open</body></html>", url=f"{BASE}/open"),
        }
        _page_map(monkeypatch, pages_map)
        row = cj.create_job(CTX.tenant_id, f"{BASE}/")
        cj.claim(CTX.tenant_id, row["id"], 3)
        _run(cj.run_job(CTX.tenant_id, row["id"]))
        j = cj.get_job(CTX.tenant_id, row["id"])
        assert j["status"] == "done" and j["checkpoint"].get("skipped_robots") == 1
        stored, total = cj.pages(CTX.tenant_id, row["id"], 0, 10)
        assert f"{BASE}/private/x" not in {r["url"] for r in stored}
    finally:
        st._ROBOTS_CACHE.clear()


def test_run_job_blocked_page_recorded_never_stealth(monkeypatch):
    _allow_robots(monkeypatch)

    def _boom(*a, **k):
        raise AssertionError("the background lane is HTTP-only - stealth must never be tried here")
    monkeypatch.setattr(st, "_stealth_fetch", _boom)
    pages_map = {f"{BASE}/": _resp(CHALLENGE_HTML, status=403)}
    _page_map(monkeypatch, pages_map)
    row = cj.create_job(CTX.tenant_id, f"{BASE}/")
    cj.claim(CTX.tenant_id, row["id"], 3)
    _run(cj.run_job(CTX.tenant_id, row["id"]))
    j = cj.get_job(CTX.tenant_id, row["id"])
    assert j["status"] == "done" and j["pages_done"] == 0
    assert j["checkpoint"]["errors"] == 1 and "403" in j["checkpoint"]["last_block"]
    stored, total = cj.pages(CTX.tenant_id, row["id"], 0, 10)
    assert total == 1 and stored[0]["status"] == 403 and "blocked" in stored[0]["note"]


def test_run_job_fetch_failures_never_kill_the_crawl(monkeypatch):
    _allow_robots(monkeypatch)
    pages_map = {
        f"{BASE}/": _resp('<html><body><a href="/dead">d</a><a href="/live">l</a></body></html>'),
        f"{BASE}/live": _resp("<html><body>live</body></html>", url=f"{BASE}/live"),
        # /dead is missing on purpose -> RuntimeError -> recorded, crawl moves on
    }
    _page_map(monkeypatch, pages_map)
    row = cj.create_job(CTX.tenant_id, f"{BASE}/")
    cj.claim(CTX.tenant_id, row["id"], 3)
    _run(cj.run_job(CTX.tenant_id, row["id"]))
    j = cj.get_job(CTX.tenant_id, row["id"])
    assert j["status"] == "done" and j["pages_done"] == 2 and j["checkpoint"]["errors"] == 1
    stored, _ = cj.pages(CTX.tenant_id, row["id"], 0, 10)
    dead = [r for r in stored if r["url"] == f"{BASE}/dead"][0]
    assert dead["status"] == 0 and "fetch failed" in dead["note"], "the dead page is recorded honestly"


def test_run_job_stop_between_pages(monkeypatch):
    _allow_robots(monkeypatch)
    pages_map = {
        f"{BASE}/": _resp('<html><body><a href="/p2">2</a></body></html>'),
        f"{BASE}/p2": _resp('<html><body>two <a href="/p3">3</a></body></html>', url=f"{BASE}/p2"),
    }

    def _fetch(url, tenant, timeout=25, adaptive=False):
        if url == f"{BASE}/p2":            # the owner's stop lands while page 2 is in the air
            cj.stop_job(tenant, row["id"])
        return pages_map[url]
    monkeypatch.setattr(st, "_fetch", _fetch)
    row = cj.create_job(CTX.tenant_id, f"{BASE}/")
    cj.claim(CTX.tenant_id, row["id"], 3)
    _run(cj.run_job(CTX.tenant_id, row["id"]))
    j = cj.get_job(CTX.tenant_id, row["id"])
    assert j["status"] == "stopped", "stop lands between pages, fetched pages stay usable"
    assert j["pages_done"] == 2, "the page in the air finishes; nothing after it starts"
    stored, total = cj.pages(CTX.tenant_id, row["id"], 0, 10)
    assert total == 2 and {r["url"] for r in stored} == {f"{BASE}/", f"{BASE}/p2"}
    assert f"{BASE}/p3" not in {r["url"] for r in stored}, "harvested-but-unfetched urls never run after a stop"


def test_stalled_job_resumes_from_checkpoint(monkeypatch):
    _allow_robots(monkeypatch)
    calls: list[str] = []
    pages_map = {
        f"{BASE}/": _resp(CARD_HTML),
        f"{BASE}/products/a": _resp("<html><body>a</body></html>", url=f"{BASE}/products/a"),
        f"{BASE}/products/b": _resp("<html><body>b</body></html>", url=f"{BASE}/products/b"),
        f"{BASE}/about": _resp("<html><body>about</body></html>", url=f"{BASE}/about"),
    }
    _page_map(monkeypatch, pages_map, calls)
    row = cj.create_job(CTX.tenant_id, f"{BASE}/")
    # simulate a crash after the seed page: checkpoint keeps the frontier, heartbeat went stale
    cj._save(CTX.tenant_id, row["id"], status="running", tries=1, fetched=1, pages_done=1,
             updated_at=time.time() - 999,
             checkpoint=json.dumps({"queue": [f"{BASE}/products/a", f"{BASE}/products/b", f"{BASE}/about"],
                                    "seen": [f"{BASE}/", f"{BASE}/products/a", f"{BASE}/products/b",
                                             f"{BASE}/about"]}))
    async def _flow():                       # one loop: the tick's task lives on the same run
        assert await cj.tick() == 1
        await cj.drain()
    _run(_flow())
    j = cj.get_job(CTX.tenant_id, row["id"])
    assert j["status"] == "done" and j["pages_done"] == 4
    assert calls.count(f"{BASE}/") == 0, "the finished page is NEVER fetched again"


def test_tick_spawns_and_finishes(monkeypatch):
    _allow_robots(monkeypatch)
    pages_map = {f"{BASE}/": _resp("<html><body>solo</body></html>")}
    _page_map(monkeypatch, pages_map)
    out = _run(cj.crawl_start(CTX, f"{BASE}/"))

    async def _flow():                       # one loop: the tick's task lives on the same run
        assert await cj.tick() == 1
        await cj.drain()
    _run(_flow())
    j = cj.get_job(CTX.tenant_id, out["job_id"])
    assert j["status"] == "done" and j["tries"] == 1 and j["pages_done"] == 1


def test_tick_respects_max_running(monkeypatch):
    _allow_robots(monkeypatch)
    row = cj.create_job(CTX.tenant_id, f"{BASE}/")
    cj._RUNNING.add(f"{CTX.tenant_id}:{row['id']}x")     # the one global slot is busy
    assert _run(cj.tick()) == 0
    assert cj.get_job(CTX.tenant_id, row["id"])["status"] == "queued", "nothing was claimed"


def test_tick_disabled_setting(monkeypatch):
    row = cj.create_job(CTX.tenant_id, f"{BASE}/")
    monkeypatch.setenv("SCRAPE_CRAWL_ENABLED", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    try:
        assert _run(cj.tick()) == 0
        assert cj.get_job(CTX.tenant_id, row["id"])["status"] == "queued"
    finally:
        get_settings.cache_clear()


def test_forget_old_keeps_recent_and_cap():
    for i in range(12):
        r = cj.create_job(CTX.tenant_id, f"{BASE}/j{i}")
        cj._save(CTX.tenant_id, r["id"], status="done", updated_at=time.time())
    assert cj.forget_old(CTX.tenant_id, keep_days=7) == 2, "the 10-job cap trims the two oldest"
    con = sqlite3.connect(str(Path("data") / "scraping" / CTX.tenant_id / "crawl.db"))
    n = con.execute("SELECT COUNT(*) FROM crawl_jobs").fetchone()[0]
    con.close()
    assert n == 10
    r = cj.create_job(CTX.tenant_id, f"{BASE}/oldone")
    cj._save(CTX.tenant_id, r["id"], status="done", updated_at=time.time() - 30 * 86400)
    assert cj.forget_old(CTX.tenant_id, keep_days=7) == 1, "a week-old finished job goes"
    assert cj.get_job(CTX.tenant_id, r["id"]) is None


# ---------------------------------------------------------------- the tools

def test_crawl_status_latest_and_fields(monkeypatch):
    _allow_robots(monkeypatch)
    with pytest.raises(Exception):
        _run(cj.crawl_status(CTX))                          # nothing queued yet = honest refusal
    out = _run(cj.crawl_start(CTX, f"{BASE}/", max_pages=7))
    row = cj.get_job(CTX.tenant_id, out["job_id"])
    cj._save(CTX.tenant_id, row["id"], status="running", fetched=3, pages_done=3,
             checkpoint=json.dumps({"queue": [f"{BASE}/x"], "seen": [f"{BASE}/"], "errors": 1,
                                    "skipped_robots": 2, "last_block": "HTTP 429"}))
    st_out = _run(cj.crawl_status(CTX))                     # no job_id = the latest job
    assert st_out["job_id"] == out["job_id"] and st_out["status"] == "running"
    assert st_out["fetched"] == 3 and st_out["queue_left"] == 1
    assert st_out["errors"] == 1 and st_out["skipped_by_robots"] == 2 and st_out["last_block"] == "HTTP 429"


def test_crawl_status_stop(monkeypatch):
    _allow_robots(monkeypatch)
    out = _run(cj.crawl_start(CTX, f"{BASE}/"))
    stopped = _run(cj.crawl_status(CTX, out["job_id"], action="stop"))
    assert stopped["status"] == "stopped" and "crawl_results" in stopped["note"]
    again = _run(cj.crawl_status(CTX, out["job_id"], action="stop"))
    assert again["status"] == "stopped"                     # idempotent, honest


def test_crawl_results_pagination_and_url_pick(monkeypatch):
    _allow_robots(monkeypatch)
    row = cj.create_job(CTX.tenant_id, f"{BASE}/")
    cj._save(CTX.tenant_id, row["id"], status="running")
    for i in range(7):
        cj.put_page(CTX.tenant_id, row["id"], f"{BASE}/p{i}", i + 1, 200, f"T{i}",
                    f"# page {i} " + "x" * (12_000 if i == 3 else 10), f"text {i}")
    out = _run(cj.crawl_results(CTX, row["id"], offset=0, limit=3))
    assert out["total_pages"] == 7 and out["count"] == 3
    assert [p["title"] for p in out["pages"]] == ["T0", "T1", "T2"]
    out2 = _run(cj.crawl_results(CTX, row["id"], offset=6, limit=3))
    assert out2["count"] == 1 and "offset aage badhayein" not in out2["note"]
    one = _run(cj.crawl_results(CTX, row["id"], url=f"{BASE}/p3"))
    assert one["count"] == 1 and len(one["pages"][0]["markdown"]) > 8_000, "url= mode serves the full page"
    listing = _run(cj.crawl_results(CTX, row["id"], offset=3, limit=1))
    assert len(listing["pages"][0]["markdown"]) <= cj._RESULT_CHARS + 100, "listings stay capped"
    with pytest.raises(Exception):                       # another tenant's job_id is not visible
        _run(cj.crawl_results(CTX2.tenant_id, row["id"]))


def test_crawl_results_masks_ids(monkeypatch):
    _allow_robots(monkeypatch)
    row = cj.create_job(CTX.tenant_id, f"{BASE}/")
    cj.put_page(CTX.tenant_id, row["id"], f"{BASE}/id", 1, 200, "T",
                "aadhaar 234123412346 hai", "")     # Verhoeff-valid, so the masker fires
    out = _run(cj.crawl_results(CTX, row["id"]))
    assert "234123412346" not in out["pages"][0]["markdown"], "ids are masked like every other tool"
    assert "XXXX" in out["pages"][0]["markdown"]


# ---------------------------------------------------------------- version pin

def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.530.0"
    from pathlib import Path
    pub = Path(__file__).resolve().parents[2] / "pubspec.yaml"
    assert "0.530.0+553" in pub.read_text()
