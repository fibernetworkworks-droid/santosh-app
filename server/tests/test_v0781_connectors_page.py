"""v0.781 CONNECTORS PAGE (owner: "LETS WORK ON CONNECTOR IN WEB CONSOLE --- CURRENTLY IT IS ONLY AT APP SIDE" ->
"GO BUILD FULL CONNECTORS PAGE -- MAKE IT MORE PREMIUM, PROFESSIONAL AND ADVANCE AND A SHORT 1 LINER BELOW EVERY
CONNECTOR -- AS WE USE COMPOSIO FOR THIS").

Held here:
- the one-liner (bazar/oneline.py) and that every connector list carries it as `line`;
- the sign-in done page works for the web console (BroadcastChannel + localStorage, closes itself) AND the phone
  (deep link unchanged), in English, with every value escaped - before, both callbacks jumped to santosh://bazar,
  a dead page on a computer;
- the console page is wired (sidebar row, view, stamp) and calls ONLY routes the server really has;
- no inline handlers (console CSP), keys never echoed back;
- a real-browser walk: cards with their line, tabs, key modal, sign-in window -> done page -> the console updates.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tests.test_v0276_composio import cz  # noqa: F401  (fixture: a fake Composio with 6 apps)

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server" / "app" / "static" / "console"
JS = (CON / "connectors.js").read_text()


# ---------------------------------------------------------------- the one-liner
def test_oneline_keeps_one_calm_sentence():
    from app.bazar.oneline import oneline
    assert oneline("Team chat") == "Team chat"
    assert oneline("Slack is a channel-based messaging platform. It connects teams.", "Slack") == "Channel-based messaging platform"
    assert oneline("Notion (notes) is an all-in-one workspace for notes and docs.", "Notion") == "All-in-one workspace for notes and docs"
    long = "Manage contacts, deals, pipelines, quotes, invoices, email sequences, meetings, tasks and reports across every team you have"
    out = oneline(long)
    assert len(out) <= 90 and out.endswith("…") and not out[:-1].endswith(" ")
    assert " " in out and long.startswith(out[:-1])             # cut at a word boundary, never mid-word
    assert oneline("**Fast** [docs](https://x.y/z) for https://a.b invoices") == "Fast docs for invoices"
    assert oneline("", category="CRM") == "CRM app"
    assert oneline("its tools") == "Connect your account and Hoola works inside it"


def test_every_composio_app_carries_its_line(cz):  # noqa: F811
    out = cz["svc"].composio_apps("default", "", "", 0, 40)
    assert out["apps"] and all(a["line"] and len(a["line"]) <= 90 for a in out["apps"])
    slack = next(a for a in out["apps"] if a["toolkit"] == "slack")
    assert slack["line"] == "Team chat" and slack["does"] == "Team chat"


def test_featured_servers_and_catalog_carry_a_line(env):
    from app.bazar import service
    feat = service.mcp_featured("default")
    assert feat and all(f["line"] and len(f["line"]) <= 90 for f in feat)
    cat = service.catalog("default")
    assert all("line" in p for p in cat["packs"])
    conns = service.connections("default")
    assert conns and all(c.get("line") for c in conns if not c.get("custom"))


# ---------------------------------------------------------------- the sign-in done page
def test_done_page_serves_web_and_phone_and_escapes():
    from app.bazar import donepage
    html = donepage.render(True, "<b>X</b> is connected", "ok", "santosh://bazar?linked=1", name="</script><img src=x onerror=alert(1)>")
    assert "<b>X</b>" not in html and "&lt;b&gt;X&lt;/b&gt;" in html
    assert "</script><img" not in html                                  # the name inside the script block is escaped
    assert "BroadcastChannel('hoola-connect')" in html and "hoola.connect.pending" in html and "hoola.connect.done" in html
    assert "window.close()" in html and "santosh://bazar?linked=1" in html   # web closes itself; the phone keeps its deep link


def test_link_callback_page_is_english_and_works_for_the_web(env):
    from fastapi.testclient import TestClient
    from app import main
    with TestClient(main.app) as c:
        r = c.get("/bazar/link/callback", params={"error": "access_denied"})
    assert r.status_code == 200 and "Sign-in cancelled" in r.text and "Back to Hoola" in r.text
    assert "BroadcastChannel" in r.text and "://bazar?linked=0" in r.text
    assert "Santosh" not in r.text


def test_composio_callback_page_is_english(cz):  # noqa: F811
    from fastapi.testclient import TestClient
    from app import main
    with TestClient(main.app) as c:
        r = c.get("/bazar/composio/callback", params={"st": "not-a-real-state"})
    assert r.status_code == 200 and "Not connected" in r.text and "jud gaya" not in r.text
    assert "BroadcastChannel" in r.text and "://bazar?linked=0" in r.text


def test_a_key_is_never_echoed_back(cz):  # noqa: F811
    from fastapi.testclient import TestClient
    from app import main
    with TestClient(main.app) as c:
        r = c.post("/api/composio/apps/zendesk/key", json={"values": {"generic_api_key": "zd-SECRET-123456", "subdomain": "shop"}})
    assert r.status_code == 200 and r.json()["status"] == "ready"
    assert "zd-SECRET-123456" not in r.text


# ---------------------------------------------------------------- the console page is wired, and only to real routes
def test_console_wiring():
    from app.main import APP_VERSION
    html = (CON / "v2.html").read_text()
    js = (CON / "v2.js").read_text()
    assert f'<script src="/static/console/connectors.js?v={APP_VERSION}"></script>' in html
    assert 'id="v-connectors"' in html and 'id="connectors"' in html
    assert "['connectors','Connectors']" in js and "HoolaConnectors(" in js and "CX?.open($('#connectors')" in js
    assert html.index("connectors.js") < html.index("/v2.js")          # the module is there before v2.js builds it


def test_page_calls_only_routes_the_server_has():
    from app import main
    have = []

    def walk(routes, prefix=""):
        for r in routes:
            sub = getattr(r, "original_router", None)            # FastAPI 0.14x keeps include_router() lazy
            if sub is not None:
                ctx = getattr(r, "include_context", None)
                walk(sub.routes, prefix + (getattr(ctx, "prefix", "") or ""))
                continue
            for m in getattr(r, "methods", None) or ():
                have.append((m, re.compile("^" + re.sub(r"\{[^}]+\}", "[^/]+", prefix + r.path) + "$")))
    walk(main.app.routes)
    calls = re.findall(r"api\('(GET|POST|PUT|PATCH|DELETE)',\s*[`'\"]([^`'\"?]+)", JS)
    assert len(calls) >= 18, calls
    missing = []
    for meth, path in calls:
        p = re.sub(r"\$\{[^}]+\}", "x", path)
        if not any(m == meth and rx.match(p) for m, rx in have):
            missing.append((meth, path))
    assert not missing, missing


def test_page_rules_no_inline_handlers_and_keys_only_typed_here():
    assert not re.search(r"""\son[a-z]+=["']""", JS)                   # the console CSP is script-src 'self'
    for word in ("Sealed on the server and never shown again", "never asks for a key in chat"):
        assert word in JS
    # every card shows the server's one-liner under the name
    assert JS.count('<p class="cx-line">') >= 3 and "x.line || x.does" in JS
    assert "Composio" in JS                                             # the apps say how they connect


# ---------------------------------------------------------------- a real-browser walk
from tests.test_v0312_arena_screen import arena_server  # noqa: E402,F401
from tests.test_v121_site import site_env  # noqa: E402,F401

APPS = {"configured": True, "total": 3, "all": 1612, "offset": 0, "live": True, "calls_this_month": 42, "monthly_cap": 300,
        "categories": [["Communication", 120], ["CRM", 80]],
        "apps": [{"toolkit": "slack", "pack_id": "cmp-slack", "name": "Slack", "does": "Team chat", "line": "Team chat for every channel",
                  "logo": "/api/logo/cmp/slack?v=2", "category": "Communication", "tools": 150, "status": "ready"},
                 {"toolkit": "zendesk", "pack_id": "cmp-zendesk", "name": "Zendesk", "does": "Support tickets", "line": "Support tickets and help centre",
                  "logo": "/api/logo/cmp/zendesk?v=2", "category": "Customer Support", "tools": 40, "status": "needs_key"},
                 {"toolkit": "notion", "pack_id": "cmp-notion", "name": "Notion", "does": "Notes", "line": "Notes, docs and wikis in one place",
                  "logo": "", "category": "Productivity", "tools": 30, "status": "needs_link"}]}


def test_connectors_page_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    for w in (1280, 390):
        errors = []
        ctx = browser.new_context(viewport={"width": w, "height": 900})
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.route("**/api/composio/apps?*", lambda r: r.fulfill(json=APPS))
        pg.route("**/api/composio/apps/zendesk/connect", lambda r: r.fulfill(json={"status": "needs_key", "fields": [
            {"name": "generic_api_key", "label": "API Key", "required": True, "secret": True, "hint": "From Admin > API"}]}))
        pg.route("**/api/composio/apps/zendesk/key", lambda r: r.fulfill(json={"status": "ready", "name": "Zendesk"}))
        # the sign-in "page" is Hoola's own done page for a cancelled sign-in: it must reach this tab by itself
        pg.route("**/api/composio/apps/notion/connect", lambda r: r.fulfill(json={"status": "open_link", "url": base + "/bazar/link/callback?error=access_denied"}))
        pg.goto(base + "/console/")
        pg.wait_for_selector('#snav [data-v="connectors"]')
        pg.click('#snav [data-v="connectors"]') if w > 700 else pg.evaluate("()=>document.querySelector('#snav [data-v=\"connectors\"]').click()")
        pg.wait_for_selector(".cx-card[data-app='slack']")
        assert "Team chat for every channel" in pg.inner_text(".cx-card[data-app='slack'] .cx-line")
        assert pg.locator(".cx-card[data-app='notion'] .cx-logo.mono").count() == 1      # no logo = the initial on a tile
        m = pg.evaluate("()=>({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth})")
        assert m["sw"] <= m["cw"] + 1, (w, m)                                             # no sideways scroll
        if w > 700:
            # the key modal from the server's own fields, then saved
            pg.click(".cx-card[data-app='zendesk'] [data-app-go]")
            pg.wait_for_selector(".cx-dialog input[name='generic_api_key']")
            assert pg.get_attribute(".cx-dialog input[name='generic_api_key']", "type") == "password"
            pg.fill(".cx-dialog input[name='generic_api_key']", "zd-123456")
            pg.click(".cx-dialog [data-cx='ok']")
            pg.wait_for_selector(".cx-dialog", state="detached")
            # the sign-in window lands on the done page, which tells this tab
            with pg.expect_popup() as pop:
                pg.click(".cx-card[data-app='notion'] [data-app-go]")
            pop.value.wait_for_load_state()
            pg.wait_for_function("()=>/Notion was not connected/.test(document.getElementById('toast').textContent)")
            # the drawer of a connected app, and its try lines go into the composer (never sent by themselves)
            pg.click(".cx-card[data-app='slack'] .cx-line")
            pg.wait_for_selector(".cx-panel .cx-trybtn")
            pg.click(".cx-panel .cx-trybtn")
            assert "Slack" in pg.input_value("#msg")
            pg.evaluate("()=>document.querySelector('#snav [data-v=\"connectors\"]').click()")
            for tab in ("connected", "mcp", "builtin", "apis", "limits"):
                pg.click(f".cx-tab[data-tab='{tab}']")
                pg.wait_for_selector(".cx-body > :not(.cx-grid) , .cx-body .cx-sec, .cx-body .cx-empty, .cx-body .cx-two, .cx-body .cx-bar")
                pg.wait_for_timeout(250)
                assert pg.get_attribute(f".cx-tab[data-tab='{tab}']", "aria-selected") == "true"
            assert pg.locator(".cx-two #cxlim").count() == 1
        assert not errors, errors
        ctx.close()


# ---------------------------------------------------------------- the version
def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.880.0"
    assert "0.880.0+879" in (ROOT / "pubspec.yaml").read_text()
