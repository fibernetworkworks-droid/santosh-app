"""v0.999.119 D9: "Upgrade this site" - her HTML website moved to the new engine on her tap. The new design is built
BESIDE the old website from its own pages and her own words (read back out of her pages, her edits included) with her
colour pinned; nothing of the old website changes meanwhile. She compares the two side by side; only her tap on the
fingerprint of what she saw keeps it; she can go back to the old design any time, or throw the new one away."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.site import upgrade as UP
from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v0814_app_engine import _box, ae_env  # noqa: F401  (fixture)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

HERO = ('<section class="hs" id="s-home-hero"><div class="wrap"><h1 data-e="1" data-m="split">Sunrise Bakery</h1>'
        '<p class="lead" data-e="2">Fresh bread in Pune since morning.</p><p class="eyebrow">Since <em class="blank">[year]</em></p>'
        '<div class="btns"><a class="btn btn-primary" href="tel:+919876543210">Call us</a></div>'
        '<svg aria-hidden="true"><path d="M0 10"></path></svg><script>bad()</script></div></section>')
GRID = ('<section class="hs"><div class="wrap"><h2>Today\'s bakes</h2><p class="lead">Out of the oven at 7 am.</p>'
        '<div class="grid g3"><article class="card"><h3>Pav</h3><p class="muted">Pack of 6.</p></article>'
        '<article class="card"><h3>Nankhatai</h3><p>250 g box.</p></article></div></div></section>')


# ---------------------------------------------------------------- 1. her words, read back out of her pages
def test_her_words_come_out_of_her_built_sections():
    assert UP.words_of(HERO) == {"heading": "Sunrise Bakery", "line": "Fresh bread in Pune since morning.", "cta": "Call us"}
    assert UP.words_of(GRID) == {"heading": "Today's bakes", "line": "Out of the oven at 7 am.",
                                 "items": ["Pav - Pack of 6.", "Nankhatai - 250 g box."]}
    assert UP.words_of("") == {} and UP.words_of("<div><script>x()</script></div>") == {}
    assert "[year]" not in json.dumps(UP.words_of(HERO))                   # a blank she never filled is not her words


def _html_site():
    from app.site import service as S
    v = S.new(T, "A website for Sunrise Bakery in Pune: breads, cakes, order online.", name="Sunrise Bakery",
              answers={"phone": "9876543210", "address": "12, Shanti Complex, Pune", "email": "hello@sunrise.example"})
    S.approve_plan(T, v["id"], pages=["contact"])
    S.choose_look(T, v["id"], 0)
    r = S._load(v["id"])
    assert r.status == "ready" and r.version == 1
    return r


def test_the_pages_carry_her_own_words_and_her_edits(site_env):
    from app.site import service as S
    r = _html_site()
    sec = json.loads(S._sec_path(r, "home__hero").read_text())
    sec["html"] = sec["html"].replace(UP.words_of(sec["html"])["heading"], "Warm bread, every morning")   # her edit
    S._put_sec(r, "home__hero", sec)
    pages, counts = UP.pages_from_site(S._load(r.id))
    home = next(p for p in pages if p["slug"] == "home")
    assert [p["slug"] for p in pages][:2] == ["home", "contact"]
    assert home["sections"][0]["type"] == "hero" and home["sections"][0]["heading"] == "Warm bread, every morning"
    assert counts["sections"] >= 8 and counts["with_her_words"] == counts["sections"]
    assert all(s["type"] for p in pages for s in p["sections"])


def test_upgrade_waits_for_a_built_website_and_only_for_her(site_env):
    from app.main import app
    from app.site import service as S
    c = TestClient(app)
    v = S.new(T, "A website for Sunrise Bakery in Pune.", name="Sunrise Bakery", answers={"phone": "9876543210"})
    r = S._load(v["id"])
    assert "not built yet" in UP.why_not(r)
    assert c.post(f"/api/sites/{r.id}/upgrade", json={}).status_code == 409
    assert c.get("/api/sites/nosuchsite/upgrade").status_code in (400, 404)
    r = _html_site()
    assert UP.why_not(r) == "" and c.get(f"/api/sites/{r.id}/upgrade").json()["can"] is True
    assert c.post(f"/api/sites/{r.id}/upgrade/keep", json={"hash": "x"}).status_code == 409   # nothing to keep yet
    assert c.post(f"/api/sites/{r.id}/upgrade/back", json={}).status_code == 409
    assert c.delete(f"/api/sites/{r.id}/upgrade").status_code == 404
    assert S.view(r)["upgrade"]["can"] is True


# ---------------------------------------------------------------- 2. the whole move, built in the box
@pytest.fixture
def inline(monkeypatch):
    monkeypatch.setattr(UP, "_spawn", lambda fn, site_id: fn(site_id))     # the new design is made in the test's thread
    yield


def test_the_new_design_is_built_beside_compared_kept_and_undone(ae_env, inline, monkeypatch):  # noqa: F811
    _box()
    from app.appengine import service as AE
    from app.main import app
    from app.site import ai as AI
    from app.site import service as S
    monkeypatch.setattr(AI, "ask", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no model here")))
    c = TestClient(app)
    r = _html_site()
    before = S.view(r)
    old_preview, old_files = before["preview"], sorted(p.name for p in (S.B.src_dir(T, r.id) / "sections").iterdir())
    out = c.post(f"/api/sites/{r.id}/upgrade", json={})
    assert out.status_code == 200, out.text
    r = S._load(r.id)
    u = UP.view(r)
    assert u["status"] == "ready", u.get("error")
    assert u["before"] in old_preview and u["after"].startswith("/api/app-preview/") and u["hash"]
    assert u["counts"]["with_her_words"] >= 8
    # the old website did not change at all while the new design was made
    assert r.version == 1 and r.status == "ready" and S.view(r)["preview"] == old_preview and "react" not in S.view(r)
    assert sorted(p.name for p in (S.B.src_dir(T, r.id) / "sections").iterdir()) == old_files
    assert c.post(f"/api/sites/{r.id}/upgrade", json={}).status_code == 409        # one at a time
    # the new design has her words and her colour
    app_ = AE._load(T, UP.state(r)["id"])
    home = (AE.src_dir(app_) / "src" / "pages" / "HomePage.tsx").read_text()
    assert "Fresh" in home or "Sunrise Bakery" in home
    # only her tap on what she saw keeps it
    assert c.post(f"/api/sites/{r.id}/upgrade/keep", json={"hash": "stale"}).status_code == 409
    kept = c.post(f"/api/sites/{r.id}/upgrade/keep", json={"hash": u["hash"]}).json()
    r = S._load(r.id)
    assert kept["react"]["id"] == app_.id and S.view(r)["preview"].startswith("/api/app-preview/")
    assert UP.kept(r)["version"] == 1 and "react_upgrade" not in json.loads(r.facts)
    assert S.view(r)["upgrade"]["kept"]["can_go_back"] is True
    assert c.delete(f"/api/sites/{r.id}/upgrade").status_code == 404                # nothing waiting to throw away
    # back to the old design: the HTML website, untouched; the new one waits beside it again
    back = c.post(f"/api/sites/{r.id}/upgrade/back", json={}).json()
    r = S._load(r.id)
    assert "react" not in back and S.view(r)["preview"] == old_preview and r.version == 1
    assert UP.view(r)["status"] == "ready" and UP.view(r)["hash"] == u["hash"]
    # throw it away: the new design's app is removed, the website is as it was
    gone = c.delete(f"/api/sites/{r.id}/upgrade")
    assert gone.status_code == 200
    r = S._load(r.id)
    assert "react_upgrade" not in json.loads(r.facts) and UP.view(r)["can"] is True
    with pytest.raises(Exception):
        AE._load(T, app_.id)


def test_the_studio_offers_it_and_compares_side_by_side():
    from pathlib import Path
    js = (Path(UP.__file__).resolve().parents[1] / "static" / "console" / "webstudio.js").read_text()
    bar = js.split("function upgBar")[1].split("function upgradeView")[0]
    assert "Upgrade this site" in bar and "data-act=\"upg-start\"" in bar and "Go back to the old design" in bar
    assert "Your website stays exactly as it is meanwhile" in bar and "It uses some credits" in bar
    cmp = js.split("function upgradeView")[1].split("async function upgAct")[0]
    assert 'data-act="upg-keep" data-hash=' in cmp and "Your website now" in cmp and "The new design" in cmp
    act = js.split("async function upgAct")[1].split("const studioBtn")[0]
    assert "/upgrade/keep`, {hash: S(d.hash)}" in act and "confirm(" in act        # throwing away asks first
    assert "M(CUR.upgrade).status === 'building') startPoll()" in js


def test_the_chat_can_say_where_it_stands_but_never_starts_it(site_env):
    import asyncio
    from app.agent.site_tools import website
    from app.agent.tools import Ctx
    r = _html_site()
    out = asyncio.run(website(Ctx(tenant_id=T, conversation_id="", actor="owner"), "upgrade", site=r.id))
    assert out["upgrade"]["can"] is True and "her tap in the Web Studio" in out["say"]
    assert UP.state(UP.site_of(T, r.id)) == {}                                   # nothing was started
    from pathlib import Path
    tool = (Path(UP.__file__).resolve().parents[1] / "agent" / "site_tools.py").read_text()
    for her_tap in ("UP.start(", "UP.accept(", "UP.back(", "UP.discard("):
        assert her_tap not in tool


def test_upgrade_compare_keep_and_go_back_in_a_real_browser(arena_server, monkeypatch):  # noqa: F811
    """The Studio on a real server: the bar offers Upgrade on her HTML website, her tap starts it (the box build is
    stood in here), Compare shows her website and the new design side by side, Keep uses it, Go back returns."""
    from tests.test_chatkit_webstudio import _open
    from app.site import service as S
    base, browser, key = arena_server
    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(1) as ex:                             # the build's own checks run Playwright too
        r = ex.submit(_html_site).result()
    after = S.view(r)["preview"]                                    # a page to show on the right (no box here)

    def made(fn, site_id):                                           # the new design, made instantly
        UP._set(site_id, id="app_stand_in", version=1, preview=after, status="ready", built=True,
                counts={"pages": 2, "sections": 11, "with_her_words": 11}, blanks=[])
    monkeypatch.setattr(UP, "_spawn", made)
    errors: list[str] = []
    ctx, pg = _open(browser, key, base + f"/console/web#/site/{r.id}", errors)
    try:
        pg.locator('[data-upgrade="can"]').wait_for(timeout=30000)
        pg.get_by_role("button", name="Upgrade this site").click()
        pg.locator('[data-upgrade="ready"]').wait_for(timeout=30000)
        assert "11 of 11 sections carry your own words" in pg.locator('[data-upgrade="ready"]').inner_text()
        pg.get_by_role("button", name="Compare").click()
        cmp = pg.locator('[data-upgrade="compare"]')
        cmp.wait_for(timeout=15000)
        assert pg.locator(".cmp iframe").count() == 2
        assert pg.get_by_text("Your website now", exact=True).count() >= 1
        pg.get_by_role("button", name="Keep the new design").click()
        pg.locator('[data-upgrade="kept"]').wait_for(timeout=30000)
        f = json.loads(S._load(r.id).facts)
        assert f["react_app"]["id"] == "app_stand_in" and f["html_kept"]["version"] == 1
        pg.get_by_role("button", name="Go back to the old design").click()
        pg.locator('[data-upgrade="ready"]').wait_for(timeout=30000)
        f = json.loads(S._load(r.id).facts)
        assert "react_app" not in f and f["react_upgrade"]["status"] == "ready"
    finally:
        ctx.close()
    assert not errors, errors
