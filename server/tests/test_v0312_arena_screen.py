"""v0.312 ARENA SCREEN: the Design Arena gets an owner-only page in the web console. Server side: the console's /me says
whether this user may see it, run cards carry the business name, screenshots are served only for Arena sites and only to
the owner, recent duels name the builder, a run orphaned by a restart reads 'interrupted'. Then the page itself in a real
browser (Playwright + Chromium, skipped without one): the sidebar item, the score row, the runs table, a run's website
cards, comparing two runs, the start form, and a phone width with no sideways scroll. Screenshots: CONSOLE_SHOTS=<folder>."""
import json
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v121_site import site_env  # noqa: F401  (fixture)

CONSOLE = Path(__file__).resolve().parents[1] / "app" / "static" / "console"


def _seed():
    """Two finished runs (the newer one better), a website card that failed, and two duels."""
    from app.db import session
    from app.site import arena as A
    A.ensure_tables()
    briefs = A.pick(3, 1)
    crit = lambda v: {c: v for c in A.CRITERIA}
    ids = []
    for i, (ver, j, lcp) in enumerate((("0.309.0", 6.8, 2600), ("0.317.0", 7.9, 1900))):
        with session() as s:
            run = A.ArenaRun(version=ver, seed=1, n=3, budget_inr=1500, spent_inr=420 + i, status="done", note=f"run {i}")
            s.add(run)
            s.flush()
            ids.append(run.id)
            cards = []
            for k, b in enumerate(briefs[:2]):
                c = {"site": f"site_{i}_{k}", "status": "ready", "blocking": k, "performance": 88, "accessibility": 95, "seo": 92,
                     "lcp_ms": lcp, "inr": 140.0, "minutes": 9.5, "sections": 7, "photos": 6, "ai_photos": 2, "sameness": 1.5,
                     "judge": {"scores": crit(j), "overall": j, "best": "Warm hero photo of the <b>shop</b>", "worst": "Footer is thin"}}
                cards.append(c)
                s.add(A.ArenaItem(run_id=run.id, brief_id=b["id"], site_id=c["site"], card=json.dumps(c)))
            s.add(A.ArenaItem(run_id=run.id, brief_id=briefs[2]["id"], card=json.dumps({"status": "failed", "error": "Build timed out"})))
            run.summary = json.dumps(A.summarize(cards))
        time.sleep(0.01)
    with session() as s:
        for w in ("a", "b"):
            res = {"winner": "hoola" if w == "a" else "rival", "hoola": {"overall": 8}, "rival": {"overall": 6.5}, "why": "A is clearer", "hoola_was": w}
            s.add(A.ArenaDuel(brief_id=briefs[0]["id"], rival="lovable", rival_url="https://example.com", hoola_site="site_1_0", result=json.dumps(res)))
    return ids, briefs


def test_server_side_for_the_screen(site_env, monkeypatch):
    from app.main import app, current_tenant
    from app.site import arena as A
    c = TestClient(app)
    assert c.get("/api/console/me").json()["arena"] is True                          # the owner sees the Arena
    ids, briefs = _seed()
    d = c.get("/api/arena/runs").json()
    assert d["max_inr"] > 0 and d["duels"]["lovable"]["duels"] == 2
    assert {x["builder"] for x in d["recent_duels"]} == {"lovable"} and d["recent_duels"][0]["rival"]["overall"] == 6.5
    run = c.get(f"/api/arena/runs/{ids[1]}").json()
    assert run["items"][0]["name"] == briefs[0]["name"] and run["items"][0]["industry"] == briefs[0]["industry"]
    assert run["budget_inr"] == 1500 and "dna" not in run["items"][0]
    # screenshots: only Arena sites, only the owner
    assert c.get("/api/arena/shot/no-such-site").status_code == 404
    from app.db import session
    from app.site.models import Site
    with session() as s:
        s.add(Site(id="site_hers", tenant_id="default", name="Meri bakery", status="ready"))
    assert c.get("/api/arena/shot/site_hers").status_code == 404                        # her own site is never served here
    app.dependency_overrides[current_tenant] = lambda: "someone-else"
    try:
        assert c.get("/api/console/me").status_code in (200, 404) and c.get("/api/arena/shot/x").status_code == 403
    finally:
        app.dependency_overrides.pop(current_tenant, None)
    # a 'running' run with no live thread (the server restarted) reads interrupted
    with session() as s:
        r = A.ArenaRun(version="t", seed=1, n=2, budget_inr=100, status="running")
        s.add(r)
        s.flush()
        rid = r.id
    assert next(x for x in A.runs() if x["run"] == rid)["status"] == "interrupted"


def test_console_wiring():
    html = (CONSOLE / "v2.html").read_text()
    js = (CONSOLE / "v2.js").read_text()
    ar = (CONSOLE / "arena.js").read_text()
    assert 'id="v-arena"' in html and "arena.js?v=" in html
    assert "ME.arena && window.HoolaArena" in js and "AR?.draw($('#arena'))" in js
    assert "onclick=" not in ar and "innerHTML" in ar
    for k in ("/api/arena/start", "/api/arena/compare", "/api/arena/duel", "/api/arena/shot/"):
        assert k in ar
    css = (CONSOLE / "v2.css").read_text()
    blk = css[css.index("v0.312 DESIGN ARENA"):css.index("v0.288 SIDEBAR FULLY VISIBLE")]   # sits before the sidebar's last word
    assert "#" not in blk.split("*/", 1)[1].replace("#arena", "").replace("/* =====", "")                       # theme tokens only, no raw colours


@pytest.fixture
def arena_server(site_env, monkeypatch):
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    import uvicorn
    from app import main
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(1200):
        if srv.started:
            break
        time.sleep(0.05)
    assert srv.started
    try:
        pw = sync_api.sync_playwright().start()
        try:
            import os
            browser = pw.chromium.launch(**({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
        except Exception as e:
            pw.stop()
            pytest.skip(f"no Chromium for Playwright here: {str(e)[:80]}")
        yield f"http://127.0.0.1:{port}", browser, KEY
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_arena_screen_in_a_real_browser(arena_server):
    import os
    base, browser, key = arena_server
    ids, briefs = _seed()
    shots = os.environ.get("CONSOLE_SHOTS")
    errors = []
    for scheme in ("light", "dark"):
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base + "/console/")
        page.wait_for_selector('#snav [data-v="arena"]', timeout=20000)
        page.click('#snav [data-v="arena"]')
        page.wait_for_selector("#arena .ar-runs table", timeout=20000)
        kpi = page.inner_text("#arena .kpis")
        assert "7.9" in kpi and "1.9 s" in kpi and "50%" in kpi                          # judge, LCP, duels won 1 of 2
        assert page.locator("#arena .ar-runs tbody tr").count() == 2
        assert page.locator("#arStart").count() == 1
        assert "₹" in page.inner_text("#arEst")
        # compare the two runs: the newer is better on the judge
        page.click("#arCmpF button[type=submit]")
        page.wait_for_selector("#arCmp table")
        row = page.locator("#arCmp tr", has_text="Judge (of 10)").inner_text()
        assert "Better" in row
        # the duel picker lists businesses the runs built; the duel table shows Lovable
        page.wait_for_function("document.querySelector('#arBrief').options.length > 1", timeout=10000)
        assert "Lovable" in page.inner_text("#arena")
        if shots:
            page.screenshot(path=f"{shots}/arena-compare-{scheme}.png")
            page.evaluate("document.querySelector('#arena').closest('.view').scrollTop = 0; document.querySelector('#arena').scrollTop = 0")
            page.screenshot(path=f"{shots}/arena-{scheme}.png")
        # open the newer run: criteria bars, two website cards + one failed, judge lines as TEXT
        page.locator(f'[data-ar-open="{ids[1]}"]').click()
        page.wait_for_selector("#arena .ar-grid .ar-card")
        assert page.locator("#arena .ar-card").count() == 3 and page.locator("#arena .ar-failed").count() == 1
        assert "Build timed out" in page.inner_text("#arena .ar-failed")
        assert "<b>shop</b>" in page.inner_text("#arena .ar-card >> nth=0")                 # model text is never HTML
        assert page.locator("#arena .ar-crit .ar-bar").count() == 6
        page.locator("#arena [data-ar-more] >> nth=0").click()
        assert page.locator("#arena .ar-card.more .ar-extra .ar-bar").count() == 6
        if shots:
            page.screenshot(path=f"{shots}/arena-run-{scheme}.png", full_page=True)
        page.click("#arBack")
        page.wait_for_selector("#arena .ar-runs table")
        ctx.close()
    # phone width: no sideways scroll
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    page = ctx.new_page()
    page.goto(base + "/console/")
    page.wait_for_function("window.HoolaArena && document.querySelector('#app') && !document.querySelector('#app').hidden", timeout=20000)
    page.evaluate("document.querySelector('[data-v=\"arena\"]').click()")
    page.wait_for_selector("#arena .ar-runs table")
    assert page.evaluate("document.querySelector('#arena').scrollWidth <= document.querySelector('#arena').clientWidth + 1")
    if shots:
        page.screenshot(path=f"{shots}/arena-phone.png", full_page=True)
    ctx.close()
    assert not errors, errors


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.318.0"
    assert "0.318.0+358" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
