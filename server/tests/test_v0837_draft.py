"""v0.837 DRAFT (L13 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L13", E6): a draft is a named copy of the site with its own
preview; Accept merges BY SECTION against the version it started from; a section both changed is a NAMED conflict (never
merged silently); nothing visitors sent moves. The proof the plan asks for: the conflict-named merge test."""
import asyncio
import json
import os

import pytest
from fastapi.testclient import TestClient

from tests.test_life import conv_ctx
from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v0407_ek_dimaag import arch_env  # noqa: F401  (fixture)
from tests.test_v0808_wapas import _fast_checks, _site
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


def _code(S, sid, rel):
    return S.code_read(T, sid, rel)["code"]


def _mark(S, sid, rel, tag):
    c = _code(S, sid, rel)
    first = c.splitlines()[0]
    S.code_write(T, sid, rel, c.replace(first, first.replace("<section", f'<section data-tag="{tag}"', 1), 1))


def _files(S, sid):
    return [f["path"] for f in S.code_files(T, sid)["files"]] if hasattr(S, "code_files") else []


def test_a_draft_is_a_copy_and_the_site_is_untouched(site_env, monkeypatch):
    _fast_checks(monkeypatch)
    from app.site import drafts as DF
    from app.site import service as S
    sid = _site(S)
    v0 = S.get(T, sid)["version"]
    d = DF.create(T, sid, "New look")
    assert d["draft_of"] == sid and d["draft_name"] == "New look" and d["preview"] and d["preview"] != S.get(T, sid)["preview"]
    assert d["id"] not in [x["id"] for x in S.sites(T)]                              # a draft is not a site of its own
    _mark(S, d["id"], "pages/home/hero.html", "draft")
    assert 'data-tag="draft"' in _code(S, d["id"], "pages/home/hero.html")
    assert 'data-tag' not in _code(S, sid, "pages/home/hero.html") and S.get(T, sid)["version"] == v0   # the site did not move
    ls = DF.listing(T, sid)
    assert [x["name"] for x in ls["drafts"]] == ["New look"] and ls["drafts"][0]["changed"][0]["say"] == "Home page · hero"
    with pytest.raises(DF.DraftError, match="already exists"):
        DF.create(T, sid, "new look")
    for n in ("b", "c"):
        DF.create(T, sid, n)
    with pytest.raises(DF.DraftError, match="3 drafts"):
        DF.create(T, sid, "d")
    from app.site import hosting as H
    assert any("this is a draft" in b for b in H.blockers(S._load(d["id"])))          # never put live
    out = DF.discard(T, sid, d["id"])
    assert "not touched" in out["say"] and len(DF.listing(T, sid)["drafts"]) == 2
    with pytest.raises(DF.DraftError) as e:
        DF.accept(T, sid, "nope")
    assert e.value.code == 403                                                          # her tap (confirm) first


def test_accept_merges_by_section_and_names_conflicts(site_env, monkeypatch):
    _fast_checks(monkeypatch)
    from app.site import drafts as DF
    from app.site import service as S
    sid = _site(S)
    pages = [f for f in os.listdir(os.path.dirname(__file__)) if False]
    d = DF.create(T, sid, "Try")["id"]
    secs = sorted(k for k in DF._read_sections(T, sid))
    assert len(secs) >= 2
    hero, other = "pages/home/hero.html", None
    # the draft changes the hero; the SITE changes a different file (its own change must survive the merge)
    files = S.code_read(T, sid, hero)
    _mark(S, d, hero, "draft-hero")
    _mark(S, sid, hero, "site-hero")                                                    # BOTH changed the hero: a conflict
    plan = DF.merge_plan(T, S._load(sid), S._load(d))
    names = [c["say"] for c in plan["conflicts"]]
    assert names == ["Home page · hero"], plan
    with pytest.raises(DF.DraftError) as e:                                              # named, never silent
        DF.accept(T, sid, d, confirm=True)
    assert e.value.code == 409 and "Home page · hero" in str(e.value) and "both the website and the draft changed" in str(e.value)
    assert "site-hero" in _code(S, sid, hero) and "draft-hero" not in _code(S, sid, hero)   # nothing was applied
    v_before = S.get(T, sid)["version"]
    out = DF.accept(T, sid, d, {"pages/home/hero.html".replace("pages/home/", "home__").replace(".html", ""): "draft"}, confirm=True)
    assert out["merged"] and "draft-hero" in _code(S, sid, hero) and "site-hero" not in _code(S, sid, hero)
    g = S.get(T, sid)
    assert g["version"] == v_before + 1 and g["versions"][0]["note"] == "Merged draft 'Try'"
    assert DF.listing(T, sid)["drafts"] == []                                            # the draft is gone after accept


def test_site_only_and_draft_only_changes_both_survive(site_env, monkeypatch):
    _fast_checks(monkeypatch)
    from app.site import drafts as DF
    from app.site import service as S
    sid = _site(S)
    d = DF.create(T, sid, "Mix")["id"]
    keys = sorted(DF._read_sections(T, sid))
    # find two different section files to change, one on each side
    rels = [f"pages/{k.split('__')[0]}/{k.split('__')[1]}.html" for k in keys if "__" in k]
    a, b = rels[0], rels[1]
    _mark(S, d, a, "from-draft")
    _mark(S, sid, b, "from-site")
    plan = DF.merge_plan(T, S._load(sid), S._load(d))
    assert plan["conflicts"] == [] and [c["item"] for c in plan["changed"]] == [keys[0]]
    DF.accept(T, sid, d, confirm=True)
    assert "from-draft" in _code(S, sid, a) and "from-site" in _code(S, sid, b)         # both changes are in the site
    # the design: a draft-only colour change comes across; a both-changed one is a named conflict
    d2 = DF.create(T, sid, "Colour")["id"]
    for who, col in ((d2, "#112233"),):
        look = json.loads(S._load(who).look); look["tokens"]["primary"] = col; S._save(who, look=look); S.save_version(who, "colour")
    DF.accept(T, sid, d2, confirm=True)
    assert json.loads(S._load(sid).look)["tokens"]["primary"] == "#112233"
    d3 = DF.create(T, sid, "Clash")["id"]
    for who, col in ((d3, "#445566"), (sid, "#778899")):
        look = json.loads(S._load(who).look); look["tokens"]["primary"] = col; S._save(who, look=look); S.save_version(who, "colour")
    plan = DF.merge_plan(T, S._load(sid), S._load(d3))
    assert [c["say"] for c in plan["conflicts"]] == ["The colours, fonts and design kit"]
    DF.accept(T, sid, d3, {"meta:look": "site"}, confirm=True)
    assert json.loads(S._load(sid).look)["tokens"]["primary"] == "#778899"              # she kept the website's own


def test_tool_and_routes(site_env, monkeypatch):
    _fast_checks(monkeypatch)
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app import main
    from app.agent import site_tools as ST
    from app.agent.tools import Ctx
    from app.site import service as S
    sid = _site(S)
    ctx = Ctx(tenant_id=T, conversation_id=conv_ctx().conversation_id)
    out = asyncio.run(ST.website(ctx, "draft_new", site=sid, name="Via Hoola"))
    assert out["draft_name"] == "Via Hoola" and "draft_new" in ST.SITE_TOOLS[0]["input_schema"]["properties"]["action"]["enum"]
    assert asyncio.run(ST.website(ctx, "draft_list", site=sid))["drafts"][0]["name"] == "Via Hoola"
    assert "Accept) is HER tap" in ST.SITE_TOOLS[0]["description"]
    c = TestClient(main.app)
    h = {"Authorization": f"Bearer {KEY}"}
    assert c.get(f"/api/sites/{sid}/drafts", headers={}).status_code == 401
    did = out["id"]
    r = c.post(f"/api/sites/{sid}/drafts/{did}/accept", headers=h, json={})
    assert r.status_code == 403
    assert c.post(f"/api/sites/{sid}/drafts", headers=h, json={"name": "Second"}).json()["draft_name"] == "Second"
    assert len(c.get(f"/api/sites/{sid}/drafts", headers=h).json()["drafts"]) == 2
    assert c.post(f"/api/sites/{sid}/drafts/{did}/accept", headers=h, json={"confirm": True}).json()["merged"] is True
    assert c.delete(f"/api/sites/{sid}/drafts/nope", headers=h).status_code == 404


def test_drafts_tab_in_a_browser(arena_server, site_env, monkeypatch):
    base, browser, key = arena_server
    _fast_checks(monkeypatch)
    from app.site import drafts as DF
    from app.site import service as S
    sid = _site(S)
    errors = []
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}') }} catch (e) {{}}")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(f"{base}/console/web#/site/{sid}/drafts")
    page.locator("[data-form=dft-new] input").wait_for(timeout=20000)
    page.fill("[data-form=dft-new] input", "Diwali look")
    page.click("[data-form=dft-new] button")
    page.locator(".pill", has_text="Draft · Diwali look").wait_for(timeout=40000)       # now inside the draft
    assert page.locator("[data-view=publish]").count() == 0 and page.locator("a", has_text="Back to the website").count() == 1
    did = page.url.split("/site/")[1].split("/")[0].split("?")[0]
    # both sides change the hero -> the Drafts tab names the conflict and offers the choice
    _mark(S, did, "pages/home/hero.html", "draft-hero")
    _mark(S, sid, "pages/home/hero.html", "site-hero")
    page.goto(f"{base}/console/web#/site/{did}/drafts")
    page.locator(".dfc legend", has_text="Home page · hero").wait_for(timeout=20000)
    shots = os.environ.get("CONSOLE_SHOTS")
    if shots:
        page.screenshot(path=os.path.join(shots, "ae13-1-drafts.png"), full_page=True)
    page.check(".dfc input[value=draft]")
    page.click("[data-act=dft-accept]")
    page.locator("h2, .pname").first.wait_for()
    for _ in range(60):
        if not DF.listing(T, sid)["drafts"]:
            break
        page.wait_for_timeout(500)
    assert not DF.listing(T, sid)["drafts"] and "draft-hero" in _code(S, sid, "pages/home/hero.html")
    ctx.close()
    assert not errors, errors
