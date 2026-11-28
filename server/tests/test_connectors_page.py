"""v0.999.183 CONNECTORS PAGE: her connected apps as their own page (/console/connectors) - activity, her Pause switch,
the old console view sending her there, and a browser walk through every section at computer and phone width."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from tests.test_google_connections import CORE_SCOPES
from tests.test_signup_email import _google_on
from tests.test_v121_site import site_env  # noqa: F401  (fixture)
from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)


def test_classify_and_record(site_env):
    from app import connhub as C
    assert C.classify("email_draft", {}) == "mail" and C.classify("calendar_add_event", {}) == "calendar"
    assert C.classify("drive_create_doc", {}) == "docs" and C.classify("drive_find", {}) == "drive"
    assert C.classify("drivers", {}) == "" and C.classify("youtube_search", {}) == "" and C.classify("youtube_upload", {}) == "youtube"
    assert C.classify("bazar_run", {"pack_id": "cmp-slack", "tool": "SLACK_SEND_MESSAGE"}) == "slack"
    assert C.classify("bazar_run", {"pack_id": "upi-gpay"}) == "" and C.classify("web_search", {}) == ""
    C.record("tA", "c1", "bazar_run", {"pack_id": "cmp-slack", "tool": "SLACK_SEND_MESSAGE", "args": {"text": "secret words"}},
             {"card": {"id": "x"}}, True)
    C.record("tA", "c1", "email_read", {"id": "m1"}, {"subject": "Private"}, True)
    C.record("tA", "c1", "calendar_add_event", {}, None, False)
    C.record("tB", "c9", "email_read", {}, {}, True)
    rows = C.activity("tA")["rows"]
    assert [r["app"] for r in rows] == ["calendar", "mail", "slack"]
    assert [r["outcome"] for r in rows] == ["failed", "done", "asked"]
    assert rows[2]["what"] == "Send message" and rows[2]["source"] == "chat"
    assert "secret" not in str(rows) and "Private" not in str(rows)          # no content is ever kept
    assert C.activity("tA", app="slack")["rows"][0]["app"] == "slack"
    s = C.summary("tA")
    assert s["month"] == {"total": 3, "done": 1, "asked": 1, "failed": 1, "paused": 0} and s["week"]["slack"]["asked"] == 1
    assert C.activity("tB")["rows"][0]["app"] == "mail" and len(C.activity("tB")["rows"]) == 1   # tenants never mix


def test_pause_stops_every_app_in_the_tool_funnel(site_env):
    import asyncio
    from app import connhub as C
    from app.agent import santosh
    from app.agent.tools import ToolError
    from app.config import get_settings
    C.set_paused("tA", True)
    assert C.gate("tA", "email_draft", {}) and not C.gate("tA", "web_search", {}) and not C.gate("tB", "email_draft", {})

    class Ctx:
        tenant_id, conversation_id = "tA", "c1"
    ran = []

    async def disp(name, args, ctx):
        ran.append(name)
        return {"ok": True}
    with pytest.raises(ToolError) as e:
        asyncio.run(santosh._run_tool("email_draft", {}, Ctx(), get_settings(), dispatch_fn=disp))
    assert "paused" in str(e.value) and not ran
    assert C.activity("tA")["rows"][0]["outcome"] == "paused"
    asyncio.run(santosh._run_tool("web_search", {"q": "x"}, Ctx(), get_settings(), dispatch_fn=disp))
    assert ran == ["web_search"]
    assert C.set_paused("tA", False)["paused"] is False
    asyncio.run(santosh._run_tool("email_read", {}, Ctx(), get_settings(), dispatch_fn=disp))
    assert ran[-1] == "email_read" and C.activity("tA")["rows"][0]["outcome"] == "done"


def test_routes_page_and_old_door(site_env, monkeypatch):
    from app.main import app
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    c = TestClient(app)
    h = {"Authorization": f"Bearer {KEY}"}
    assert c.get("/api/connectors/summary").status_code == 401
    assert c.get("/api/connectors/summary", headers=h).json()["paused"] is False
    assert c.put("/api/connectors/safety", json={"paused": True}, headers=h).json()["paused"] is True
    assert c.get("/api/connectors/safety", headers=h).json()["always"]
    assert c.get("/api/connectors/activity", headers=h).json()["rows"] == []
    r = c.get("/console/connectors")
    assert r.status_code == 200 and "connectorsapp.js" in r.text and "script-src 'self'" in r.headers["content-security-policy"]
    from pathlib import Path
    v2 = (Path(__file__).resolve().parents[1] / "app/static/console/v2.js").read_text()
    assert "location.assign('/console/connectors'" in v2 and "'route', 'connectors'" in v2


def test_browser_walk_every_section(arena_server, monkeypatch):
    base, browser, key = arena_server
    _google_on(monkeypatch)
    from app import accounts, connhub
    from app.config import get_settings
    from app.db import CalendarAccount, OAuthConnection, session
    tenant = get_settings().tenant_id
    with session() as s:
        s.add(OAuthConnection(user_id=tenant, provider="google", account_email="asha@gmail.com", scopes=CORE_SCOPES,
                              refresh_token_enc=accounts.encrypt("rt")))
        s.add(CalendarAccount(tenant_id=tenant, address="office@biz.com", status="error", last_error="invalid_grant",
                              refresh_token_enc=accounts.encrypt("rt2")))
    for name, args, out, ok in (("email_triage", {}, {}, True), ("email_draft", {}, {"card": 1}, True),
                                ("sheet_append", {}, {}, True), ("calendar_add_event", {}, None, False)):
        connhub.record(tenant, "c1", name, args, out, ok)
    shots = os.environ.get("HOOLA_SHOTS")
    for w, h, scheme in ((1440, 900, "light"), (390, 844, "light"), (1440, 900, "dark")):
        ctx = browser.new_context(viewport={"width": w, "height": h}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        p = ctx.new_page()
        errs: list[str] = []
        p.on("pageerror", lambda e: errs.append(str(e)))
        p.goto(base + "/console/connectors")
        p.wait_for_selector(".k-stats")
        body = p.text_content("#kmain")
        assert "Connectors" in body and "Needs you" in body and "office@biz.com needs you" in body and "Your apps" in body
        assert "Gmail" in body and "Hoola did 4 things" in body
        for hash_, want in (("", "Your apps"), ("google", "Everyday apps"), ("google/gmail", "What Hoola does in Gmail"),
                            ("apps", "All apps"), ("activity", "Steps this month"), ("limits", "Pause every app"),
                            ("mcp", "MCP servers"), ("connected", "Connected")):
            p.evaluate(f"location.hash = '#/{hash_}'")
            for _ in range(100):
                if want in (p.text_content("#kmain") or ""):
                    break
                p.wait_for_timeout(100)
            assert want in p.text_content("#kmain"), (w, hash_)
            if hash_ == "activity":
                p.wait_for_selector(".k-tr:not(.h)")
                t = p.text_content("#kalist")
                assert "Asked you" in t and "Failed" in t and "Done" in t
            if hash_ == "google/gmail":
                p.wait_for_selector("#kact .k-table")
            wide = p.evaluate("[...document.querySelectorAll('body *')].filter(e => !e.closest('.k-navs') && e.getBoundingClientRect().right > innerWidth + 1)"
                              ".slice(0, 6).map(e => e.tagName + '.' + e.className + ' ' + Math.round(e.getBoundingClientRect().right))")
            assert p.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), (w, hash_, wide)
            if shots:
                p.screenshot(path=f"{shots}/cx_{scheme}_{w}_{hash_.replace('/', '-') or 'overview'}.png", full_page=True)
        p.evaluate("location.hash = '#/limits'")
        p.wait_for_selector("#kpause")
        p.click("label.k-sw:has(#kpause)")
        p.wait_for_selector(".k-nav .k-cnt.warn")
        assert connhub.paused(tenant)
        p.click("label.k-sw:has(#kpause)")
        p.wait_for_selector(".k-nav .k-cnt.warn", state="detached")
        assert not connhub.paused(tenant)
        assert not errs, errs
        ctx.close()
