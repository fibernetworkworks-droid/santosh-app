"""v0.808 WAPAS (L7 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L7"): every version keeps its source, so ANY version
can come back before launch (as a new, undoable version; data never touched); bookmarks; what changed between versions;
Undo this change on each reply; Revert and resend from an edited message; and (E7) the live build view survives a
restart."""
import asyncio
import json
import os

import pytest
from fastapi.testclient import TestClient

from tests.test_life import conv_ctx
from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v0407_ek_dimaag import arch_env  # noqa: F401  (fixture: the architect + the site fake AI)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


def _site(S):
    v = S.new(T, "mithai dukaan ki website", conv_ctx().conversation_id, name="Sharma Sweets",
              answers={"phone": "9876543210", "address": "Main Road, Akot"})
    S.approve_plan(T, v["id"], pages=["contact"])
    S.choose_look(T, v["id"], 0)
    return v["id"]


def _fast_checks(monkeypatch):
    from app.site import checks as C
    monkeypatch.setattr(C, "run", lambda *a, **k: (_ for _ in ()).throw(C.CheckError("no browser checks in this test")))


def _hero_line(S, sid):
    return S.code_read(T, sid, "pages/home/hero.html")["code"].splitlines()[0]


def test_any_version_comes_back_as_a_new_version(site_env, monkeypatch):
    _fast_checks(monkeypatch)
    from app.site import build as B
    from app.site import service as S
    from app.site import wapas as WP
    sid = _site(S)
    v1 = S.get(T, sid)["version"]
    assert WP.has(T, sid, v1)                                                         # every version keeps its source
    first = _hero_line(S, sid)
    S.code_write(T, sid, "pages/home/hero.html", S.code_read(T, sid, "pages/home/hero.html")["code"].replace(
        first, first.replace("<section", '<section data-tone="v2"', 1), 1))
    v2 = S.get(T, sid)["version"]
    assert v2 == v1 + 1 and "data-tone" in _hero_line(S, sid)
    look = json.loads(S._load(sid).look)
    look["tokens"]["primary"] = "#123456"
    S._save(sid, look=look)
    S.save_version(sid, "colour")
    v3 = S.get(T, sid)["version"]
    out = WP.restore(T, sid, v1)
    assert out["restored"] and "not touched" in out["say"]
    g = S.get(T, sid)
    assert g["version"] == v3 + 1 and g["versions"][0]["note"] == f"Restored v{v1}"           # History stays a line
    assert "data-tone" not in _hero_line(S, sid)                                            # the code is v1's
    assert json.loads(S._load(sid).look)["tokens"]["primary"] != "#123456"                  # the design is v1's
    assert "data-tone" not in (B.out_dir(T, sid, g["version"]) / "index.html").read_text()
    WP.restore(T, sid, v2)                                                                  # and the restore can be undone
    assert "data-tone" in _hero_line(S, sid)
    with pytest.raises(WP.WapasError):
        WP.restore(T, sid, 999)
    import shutil
    shutil.rmtree(WP.snap_dir(T, sid, v1))
    with pytest.raises(WP.WapasError, match="before versions kept their source"):
        WP.restore(T, sid, v1)
    S._save(sid, status="building")
    with pytest.raises(WP.WapasError, match="working on something"):
        WP.restore(T, sid, v2)


def test_data_is_never_touched(site_env, monkeypatch):
    _fast_checks(monkeypatch)
    from app.db import session
    from app.site import service as S
    from app.site import wapas as WP
    from app.site.models import SiteLead
    sid = _site(S)
    v1 = S.get(T, sid)["version"]
    S.save_version(sid, "second")
    with session() as s:
        s.add(SiteLead(site_id=sid, tenant_id=T, name="Ramesh", phone="9000000000", message="Kaju katli price?"))
    WP.restore(T, sid, v1)
    with session() as s:
        assert s.query(SiteLead).filter(SiteLead.site_id == sid).count() == 1


def test_bookmarks_and_what_changed(site_env, monkeypatch):
    _fast_checks(monkeypatch)
    from app.main import app
    from app.site import service as S
    sid = _site(S)
    v1 = S.get(T, sid)["version"]
    line = _hero_line(S, sid)
    code = S.code_read(T, sid, "pages/home/hero.html")["code"]
    S.code_write(T, sid, "pages/home/hero.html", code.replace(line, line + '\n<p class="lead">Naya din, nayi mithai.</p>', 1))
    v2 = S.get(T, sid)["version"]
    c = TestClient(app)
    d = c.get(f"/api/sites/{sid}/versions/{v2}/diff").json()
    f = next(x for x in d["files"] if x["path"] == "pages/home/hero.html")
    assert d["against"] == v1 and f["added"] >= 1 and "+<p class=\"lead\">Naya din, nayi mithai.</p>" in f["diff"]
    assert c.get(f"/api/sites/{sid}/versions/{v1}/diff?against={v1}").json()["files"] == []
    b = c.post(f"/api/sites/{sid}/versions/{v1}/bookmark", json={"name": "  Before the Diwali   changes "}).json()
    assert b["bookmark"] == "Before the Diwali changes"
    vs = {x["version"]: x for x in S.get(T, sid)["versions"]}
    assert vs[v1]["bookmark"] == "Before the Diwali changes" and vs[v1]["restorable"] and vs[v2]["restorable"]
    assert c.post(f"/api/sites/{sid}/versions/{v1}/bookmark", json={"name": ""}).json()["bookmark"] == ""
    assert c.post(f"/api/sites/{sid}/versions/77/bookmark", json={"name": "x"}).status_code == 404
    r = c.post(f"/api/sites/{sid}/versions/{v1}/restore").json()
    assert r["restored"] and S.get(T, sid)["version"] == v2 + 1


def test_agent_can_restore_a_version(site_env, monkeypatch):
    _fast_checks(monkeypatch)
    from app.agent import site_tools as ST
    from app.agent.tools import Ctx
    from app.site import service as S
    sid = _site(S)
    v1 = S.get(T, sid)["version"]
    S.save_version(sid, "x")
    ctx = Ctx(tenant_id=T, conversation_id=conv_ctx().conversation_id)
    out = asyncio.run(ST.website(ctx, "restore_version", site=sid, version=v1))
    assert out["restored"] and "restore_version" in ST.SITE_TOOLS[0]["input_schema"]["properties"]["action"]["enum"]
    assert "action=rollback is only for her LIVE address" in ST.SITE_TOOLS[0]["description"]


def test_live_view_survives_a_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("SITE_DIR", str(tmp_path))
    from app.site import stream as ST
    ST._SITES.clear()
    with ST.watch("site_live1", "home__hero", "Hero"):
        ST.feed('{"html": "<section>Hi', force=True)
    ST.finish("site_live1", "home__hero", True, "<section>Hi there</section>", "")
    ST.begin("site_live1", "home__about", "About")
    with ST._COND:
        ST._SITES["site_live1"]["slots"]["home__about"].update(state="write", html="<section>Ab")
        ST._bump(ST._SITES["site_live1"], ST._SITES["site_live1"]["slots"]["home__about"], force=True)
    before = ST.snapshot("site_live1")
    ST._SITES.clear()                                                                     # the server restarted
    after = ST.snapshot("site_live1")
    assert after["seq"] == before["seq"] and {s["key"] for s in after["slots"]} == {"home__hero", "home__about"}
    hero = next(s for s in after["slots"] if s["key"] == "home__hero")
    about = next(s for s in after["slots"] if s["key"] == "home__about")
    assert hero["state"] == "done" and hero["html"] == "<section>Hi there</section>" and about.get("stale")
    assert ST.done_count("site_live1") == 1
    assert ST.wait("site_live1", 0, 0.1)["seq"] == before["seq"]
    ST.begin("site_live1", "home__about", "About")                                         # the build picks it up again
    assert not ST._SITES["site_live1"]["slots"]["home__about"].get("stale")
    ST.clear("site_live1")
    ST._SITES.clear()
    assert ST.snapshot("site_live1")["slots"] == []


def test_studio_source_wiring():
    from pathlib import Path
    D = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
    js, css = (D / "webstudio.js").read_text(), (D / "webstudio.css").read_text()
    for x in ("data-act=\"ver-restore\"", "data-act=\"ver-diff\"", "data-act=\"ver-bm\"", "data-act=\"undo-turn\"", "Undo this change",
              "Revert and resend", "data-form=\"resend\"", "/versions/${n}/restore`", "Put live…"):
        assert x in js, x
    assert ".vfoot" in css and ".dpre" in css and ".meedit" in css


def test_history_undo_and_revert_in_a_browser(arena_server, arch_env, monkeypatch):
    _fast_checks(monkeypatch)
    base, browser, key = arena_server
    from app import turn_inbox
    from app.db import Message, session
    from app.events import bus
    from app.site import service as S
    sid = _site(S)
    v1 = S.get(T, sid)["version"]
    sent = []

    async def fake(inbox_id, conv, text, tenant, voice, *a, **k):
        sent.append(text)
        with session() as s:
            s.add(Message(conversation_id=conv, role="user", content=text, display=text, in_history=True))
        line = (await asyncio.to_thread(S.code_read, tenant, sid, "pages/home/hero.html"))["code"].splitlines()[0]
        tag = "grey" if "grey" in text else "green"
        new = line.split(" data-tone=")[0].replace("<section", f'<section data-tone="{tag}"', 1) if "data-tone" not in line \
            else line.replace(line[line.index("data-tone="):].split()[0], f'data-tone="{tag}"')
        from app.site import lineedit as LE
        await asyncio.to_thread(LE.edit, tenant, sid, "pages/home/hero.html", line, new)
        reply = f"Done: the hero is {tag}."
        await asyncio.sleep(0.3)
        with session() as s:
            s.add(Message(conversation_id=conv, role="assistant", content=reply, display=reply, in_history=True))
        bus.publish(conv, "message", {"role": "assistant", "text": reply, "source": "agent"})
        return reply
    monkeypatch.setattr(turn_inbox, "run_owned", fake)
    shots = os.environ.get("CONSOLE_SHOTS")
    errors = []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}') }} catch (e) {{}}")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(base + f"/console/web#/site/{sid}")
    page.wait_for_selector("#wsTh", timeout=20000)
    page.wait_for_timeout(1500)                                                            # the message is after v1
    page.fill("#wsTh", "make the hero green")
    page.keyboard.press("Enter")
    page.wait_for_selector("#wsMsgs .vfoot [data-act='undo-turn']", timeout=20000)          # Version N · Undo this change
    assert "Version" in page.inner_text("#wsMsgs .vfoot")
    v_green = S.get(T, sid)["version"]
    assert 'data-tone="green"' in _hero_line(S, sid) and v_green > v1
    if shots:
        page.screenshot(path=f"{shots}/l7-undo.png")
    page.click("#wsMsgs .vfoot [data-act='undo-turn']")
    for _ in range(60):
        if "data-tone" not in _hero_line(S, sid) and S.get(T, sid)["version"] > v_green:
            break
        page.wait_for_timeout(150)
    assert "data-tone" not in _hero_line(S, sid)                                             # back to v1's code
    # Revert and resend: edit her message -> the site goes back to before it, then the new words go
    page.hover("#wsMsgs .mewrap")
    page.click("#wsMsgs [data-act='msg-edit']")
    page.wait_for_selector("#wsReEd")
    page.fill("#wsReEd", "make the hero grey")
    if shots:
        page.screenshot(path=f"{shots}/l7-resend.png")
    page.click("#wsMsgs form[data-form='resend'] button[type='submit']")
    for _ in range(80):
        if any("make the hero grey" in t for t in sent) and 'data-tone="grey"' in _hero_line(S, sid):
            break
        page.wait_for_timeout(150)
    assert any("make the hero grey" in t for t in sent) and 'data-tone="grey"' in _hero_line(S, sid)
    page.wait_for_function("() => document.querySelectorAll('#wsMsgs .vfoot').length === 2", timeout=15000)   # each reply its own
    assert "Restored" not in page.inner_text("#wsMsgs")
    # History: bookmark, what changed, restore
    page.click("[data-view='history']")
    page.wait_for_selector("#wsPane .verw", timeout=8000)
    top = S.get(T, sid)["version"]
    page.click(f"#wsPane [data-act='ver-diff'][data-ver='{top}']")
    page.wait_for_selector(f"#wsPane [data-diff='{top}'] .dfile", timeout=8000)
    assert "pages/home/hero.html" in page.inner_text(f"#wsPane [data-diff='{top}']")
    page.once("dialog", lambda d: d.accept())
    page.click(f"#wsPane [data-act='ver-bm'][data-ver='{v1}']")
    page.wait_for_selector("dialog.dlg input[name='name']", timeout=4000)
    page.fill("dialog.dlg input[name='name']", "First look")
    page.click("dialog.dlg button[value='ok']")
    page.wait_for_selector("#wsPane .vbm", timeout=8000)
    assert "First look" in page.inner_text("#wsPane") and "Bookmarks" in page.inner_text("#wsPane")
    if shots:
        page.screenshot(path=f"{shots}/l7-history.png")
    page.click(f"#wsPane [data-act='ver-restore'][data-ver='{v1}'] >> nth=0")
    for _ in range(60):
        if S.get(T, sid)["version"] > top and "data-tone" not in _hero_line(S, sid):
            break
        page.wait_for_timeout(150)
    assert "data-tone" not in _hero_line(S, sid)
    ctx.close()
    assert not [e for e in errors if "localStorage" not in e], errors
