"""v0.802 GALTI PAKDO (L6 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L6"): the Studio's preview reports its errors
(page / data / build), each becomes one card per fingerprint, and Try to fix follows the debugging ladder: two fixes,
then a root-cause plan - with the ledger of attempts in the turn. The planted-error walk fixes it within 2 tries."""
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


def _bump(S, sid):
    S._save(sid, version=int(S._load(sid).version or 0) + 1)


def test_one_card_per_fingerprint_masked_and_capped(site_env, monkeypatch):
    _fast_checks(monkeypatch)
    from app.site import galti as G
    from app.site import service as S
    sid = _site(S)
    out = G.record(T, sid, [{"kind": "page", "m": "x is undefined at row 12 for ram@example.com 9876543210", "f": "pages/home/hero.js",
                             "l": 3, "p": "/"},
                            {"kind": "page", "m": "x is undefined at row 13 for ram@example.com 9876543210", "f": "pages/home/hero.js",
                             "l": 3, "p": "/"},
                            {"kind": "data", "m": "Data call failed: 502 /api/site-app/x", "p": "/contact/"},
                            "junk", {"kind": "evil", "m": "odd kind becomes a page error"}])
    es = {e["kind"] + e["message"][:6]: e for e in out["errors"]}
    assert out["recorded"] == 4 and len(out["errors"]) == 3                                 # rows 12 / 13 = one card
    pe = next(e for e in out["errors"] if e["file"] == "pages/home/hero.js")
    assert pe["count"] == 2 and "[email]" in pe["message"] and "9876543210" not in pe["message"]
    assert pe["title"] == "Page error" and pe["next"] == "fix" and pe["state"] == "open"
    assert any(e["title"] == "Data error" for e in out["errors"]) and es
    with pytest.raises(G.GaltiError):
        G.record(T, sid, "x" * (G.MAX_BODY + 1))
    assert G.record(T, sid, [{"m": f"err {i}"} for i in range(40)])["recorded"] == G.MAX_ITEMS
    with pytest.raises(S.SiteError):
        G.errors("other-tenant", sid)                                                         # her own sites only


def test_the_ladder_two_fixes_then_a_plan(site_env, monkeypatch):
    _fast_checks(monkeypatch)
    from app.agent import turnmode as TM
    from app.site import galti as G
    from app.site import service as S
    sid = _site(S)
    boom = [{"kind": "page", "m": "boom", "f": "pages/home/hero.js", "p": "/"}]
    eid = G.record(T, sid, boom)["errors"][0]["id"]
    f1 = G.try_fix(T, sid, eid)
    assert f1["mode"] == "build" and f1["attempt"] == 1 and "Fix this page error" in f1["text"]
    msg = f"{f1['text']}\n\n[Web console Web Studio: x (site id {sid})]\n\n[Web console mode: build]"
    TM.begin(msg)
    blk = TM.site_block(T)
    assert "<error_to_fix>" in blk and '"message": "boom"' in blk and "Do not claim it is fixed" in blk
    assert "<error_to_fix>" not in TM.site_block(T)                                       # read ONCE
    TM.begin("")
    _bump(S, sid)
    e = G.record(T, sid, boom)["errors"][0]                                               # seen again on a newer version
    assert e["attempts"][0]["result"] == "did not fix" and e["next"] == "fix"
    G.try_fix(T, sid, eid)
    _bump(S, sid)
    e = G.record(T, sid, boom)["errors"][0]
    assert e["failed_fixes"] == 2 and e["next"] == "plan" and "root cause" in e["note"]
    f3 = G.try_fix(T, sid, eid)
    assert f3["mode"] == "plan" and "Plan for the root cause" in f3["text"] and "2 fixes did not hold" in f3["text"]
    TM.begin(f"x\n\n[Web console Web Studio: x (site id {sid})]\n\n[Web console mode: plan]")
    blk = TM.site_block(T)
    assert "do NOT patch again" in blk and '"result": "did not fix"' in blk                # the ledger rides the turn
    TM.begin("")


def test_fixed_means_not_seen_on_a_newer_version(site_env, monkeypatch):
    _fast_checks(monkeypatch)
    from app.site import galti as G
    from app.site import service as S
    sid = _site(S)
    eid = G.record(T, sid, [{"m": "oops"}])["errors"][0]["id"]
    G.try_fix(T, sid, eid)
    assert G.errors(T, sid)["errors"][0]["state"] == "open"
    _bump(S, sid)
    e = G.errors(T, sid)["errors"][0]
    assert e["state"] == "not_seen" and e["note"].startswith("Not seen since v")
    assert G.errors(T, sid)["open"] == 0
    assert G.set_state(T, sid, eid, "ignored")["state"] == "ignored"
    assert G.errors(T, sid)["errors"] == []
    G.record(T, sid, [{"m": "oops"}])                                                     # it came back
    assert G.errors(T, sid)["errors"][0]["state"] in ("open", "not_seen")


def test_build_problem_routes_and_the_agent_read(site_env, monkeypatch):
    _fast_checks(monkeypatch)
    from app.agent import site_tools as ST
    from app.agent.tools import Ctx
    from app.main import app
    from app.site import service as S
    sid = _site(S)
    S._save(sid, status="failed", error="The hero section could not be written: the model stopped early")
    c = TestClient(app)
    got = c.get(f"/api/sites/{sid}/errors").json()
    assert any(e["kind"] == "build" and "stopped early" in e["message"] for e in got["errors"])
    r = c.post(f"/api/sites/{sid}/preview-errors", json={"items": [{"kind": "page", "m": "y is not a function", "p": "/"}]}).json()
    eid = next(e["id"] for e in r["errors"] if "y is not a function" in e["message"])
    fx = c.post(f"/api/sites/{sid}/errors/{eid}/fix").json()
    assert fx["mode"] == "build" and fx["attempt"] == 1
    assert c.post(f"/api/sites/{sid}/errors/{eid}/ignored").json()["state"] == "ignored"
    assert c.post(f"/api/sites/{sid}/errors/nope/fix").status_code == 404
    assert c.post(f"/api/sites/{sid}/preview-errors", content=b"[" + b" " * (70 * 1024) + b"]").status_code == 413
    ctx = Ctx(tenant_id=T, conversation_id=conv_ctx().conversation_id)
    out = asyncio.run(ST.website_dekho(ctx, "errors", site=sid))
    assert "open error" in out["say"] and out["errors"]
    assert "errors" in ST.SITE_TOOLS[1]["input_schema"]["properties"]["what"]["enum"]


def test_section_errors_reach_the_catcher_only_in_the_preview(site_env, monkeypatch):
    _fast_checks(monkeypatch)
    from pathlib import Path
    from app.site import build as B
    from app.site import service as S
    sid = _site(S)
    S.code_write(T, sid, "pages/home/hero.js", "document.getElementById('s-home-hero').classList.add('x');")
    site_js = (B.out_dir(T, sid, S.get(T, sid)["version"]) / "assets" / "site.js").read_text()
    assert 'window.__hoolaErr&&window.__hoolaErr(e,"pages/home/hero.js")' in site_js     # no-op unless the catcher is there
    js = (Path(__file__).resolve().parents[1] / "app" / "site" / "assets" / "hoola-site.js").read_text()
    tail = js[js.index("v0.802 GALTI PAKDO"):]
    assert "W.parent === W || !/\\/api\\/site-preview\\//.test(location.pathname)" in tail     # preview frame only
    assert "W.__hoolaErr = function" in tail and "hoola: 'perr'" in tail


def test_studio_source_wiring():
    from pathlib import Path
    D = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
    js, css = (D / "webstudio.js").read_text(), (D / "webstudio.css").read_text()
    for x in ("d.hoola !== 'perr'", "ev.source !== fr.contentWindow", "/preview-errors`", "Plan for root cause", "Try to fix",
              "This page hit a problem.", "Ctrl+Enter", "data-act=\"err-ign\""):
        assert x in js, x
    assert ".errcard" in css and ".perrbar" in css


def test_planted_error_fixed_in_at_most_two_tries(arena_server, arch_env, monkeypatch):
    _fast_checks(monkeypatch)
    base, browser, key = arena_server
    from app import turn_inbox
    from app.db import Message, session
    from app.events import bus
    from app.site import galti as G
    from app.site import service as S
    sid = _site(S)
    S.code_write(T, sid, "pages/home/hero.js", "throw new Error('planted boom');")
    v_planted = S.get(T, sid)["version"]
    seen = []

    async def fake(inbox_id, conv, text, tenant, voice, *a, **k):
        from app.agent import turnmode as TM
        TM.begin(text)
        seen.append({"text": text, "block": TM.site_block(tenant)})
        with session() as s:
            s.add(Message(conversation_id=conv, role="user", content=text, display=text, in_history=True))
        if "<error_to_fix>" in seen[-1]["block"]:                     # the fix: one exact edit, like the real model
            from app.site import lineedit as LE
            await asyncio.to_thread(LE.edit, tenant, sid, "pages/home/hero.js", "throw new Error('planted boom');",
                                    "document.getElementById('s-home-hero').classList.add('ok');")
        reply = "I removed the line that threw the error in pages/home/hero.js."
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
    page.goto(base + f"/console/web#/site/{sid}")
    page.wait_for_selector("#wsTh", timeout=20000)
    page.wait_for_selector("#wsErr .errcard", timeout=20000)                                # the preview told the Studio
    card = page.inner_text("#wsErr .errcard")
    assert "Page error" in card and "planted boom" in card and not page.locator("#wsPerr").is_hidden()
    page.click("#wsErr [data-act='err-more']")
    assert "pages/home/hero.js" in page.inner_text("#wsErr .errcard")
    if shots:
        page.screenshot(path=f"{shots}/l6-error-card.png")
    tries = 0
    for _ in range(2):                                                                     # at most two tries
        tries += 1
        page.click("#wsErr [data-act='err-fix']")
        for _ in range(100):
            if any("<error_to_fix>" in x["block"] for x in seen) and S.get(T, sid)["version"] > v_planted:
                break
            page.wait_for_timeout(150)
        page.wait_for_timeout(2500)                                                         # the new preview loads + reports
        if not page.locator("#wsErr .errcard").count():
            break
    assert tries <= 2 and page.locator("#wsErr .errcard").count() == 0, page.inner_text("#wsErr")
    assert "planted boom" in [x for x in seen if "<error_to_fix>" in x["block"]][0]["block"]
    st = G.errors(T, sid, True)["errors"]
    assert st and st[0]["state"] in ("not_seen", "open") and st[0]["count"] >= 1
    if shots:
        page.wait_for_timeout(400)
        page.screenshot(path=f"{shots}/l6-fixed.png")
    ctx.close()
    assert not [e for e in errors if "localStorage" not in e], errors


def test_the_preview_link_never_kept():
    from app.site import galti as G
    st = G._clean_stack("Error: x\n    at http://127.0.0.1:8000/api/site-preview/SECRETTOKEN/assets/site.js:3:74")
    assert "SECRETTOKEN" not in st and "/assets/site.js" in st
