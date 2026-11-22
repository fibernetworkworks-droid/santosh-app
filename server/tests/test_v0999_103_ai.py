"""v0.999.103 D8 wave 10: her own AI assistant inside her React website. She builds and publishes an AI App in Hoola AI
Apps (its answers, notice, limits and monthly cost ceiling); when its website channel is on, the writer puts it on her
React website's home page. On her own address the visitor reads the notice and taps I agree (nothing is asked before
that), then asks; Hoola's server answers with the same rules as the app's own chat page. Only an app of the site's own
owner answers on her address. Under Hoola's address (the sealed Studio preview) it is not called, so no visitor's
words spend her credits there."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.appengine import rules as RL
from app.appengine import service as AE
from app.appengine import writer as W
from tests.test_v0814_app_engine import _box, ae_env  # noqa: F401  (fixture)
from tests.test_v0999_82_own_address import _on  # noqa: F401  (autouse fixture)
from tests.test_v0999_82_signin import _portal
from tests.test_v0999_91_live import _server, live_clinic  # noqa: F401  (fixture)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

TPL = Path(AE.__file__).resolve().parent / "template"
LOCAL = "sunrise-bakery.hoolasites.localhost"
AI = {"code": "AbC123xyz", "name": "Sunrise helper", "kind": "chat", "opening": "Ask me about our breads.",
      "notice": "You are chatting with an AI assistant.", "suggested": ["When are you open?", "Do you deliver?"]}


@pytest.fixture(autouse=True)
def _local(_on, monkeypatch):  # noqa: F811
    monkeypatch.setenv("SITES_BASE_DOMAIN", "hoolasites.localhost")
    from app.config import get_settings
    get_settings.cache_clear()
    yield


# ---------------------------------------------------------------- 1. by code
def test_the_writer_puts_her_assistant_on_the_home_page_only():
    ctx = W.Ctx("Sunrise Bakery", _portal(), {"_site": {"id": "site_abc123", "ai": AI}}, "s", None)
    home, rows = W.page_file(_portal()[0], ctx, {})
    assert 'import AiChat from "@/islands/AiChat";' in home and 'code="AbC123xyz"' in home
    assert 'name="Sunrise helper"' in home and 'kind="chat"' in home and "When are you open?" in home
    assert home.index('data-sec="home:0"') < home.index("<AiChat ")                       # never above the hero
    assert any(r.get("island") == "AiChat" for r in rows)
    assert "src/islands/AiChat.tsx" in W.kit_files(rows, False)
    for pg in _portal()[1:]:
        assert "AiChat" not in W.page_file(pg, ctx, {})[0]
    # no live app of hers: no assistant; a code that is not a code: none either
    for sx in ({"id": "site_abc123"}, {"id": "site_abc123", "ai": {**AI, "code": "bad code!"}}):
        c = W.Ctx("x", _portal(), {"_site": sx}, "s", None)
        assert "AiChat" not in W.page_file(_portal()[0], c, {})[0]
    assert "src/islands/AiChat.tsx" not in W.kit_files([], False)


def test_the_island_keeps_the_rules_asks_only_after_her_tap_and_never_holds_the_token():
    from app.appengine import image as IMG
    deps = set(IMG.project_package("x").get("dependencies") or {})
    t = (TPL / "src" / "islands" / "AiChat.tsx").read_text()
    assert RL.check_file("src/islands/AiChat.tsx", t, deps) == []
    assert "localStorage" not in t and "X-Visitor-Token" not in t and "fetch(" not in t   # only member.ts does
    assert t.count("aiAgree(") == 1 and "await aiAgree(code)" in t.split("async function agree")[1][:200]
    assert "if (aiSealed())" in t.split("React.useEffect")[1][:200]                       # the preview is never called
    member = (TPL / "src" / "lib" / "member.ts").read_text()
    assert "src/lib/member.ts" in RL.LOCKED
    seal = member.split("export function aiSealed")[1][:400]
    assert '"null"' in seal and '"/api/"' in seal and '"/apps/"' in seal
    agree = member.split("export async function aiAgree")[1][:300]
    assert "consent: true" in agree and '"session"' in agree
    assert "?embed=1" in member.split("export async function aiApp")[1][:600]          # the website channel


def test_only_her_own_app_answers_on_her_address(ae_env):
    from app.aiapps import store as AST
    from app.site import rxhost as RH
    mine = AST.create(T, "Sunrise helper", "chat")
    theirs = AST.create("someone-else", "Other shop", "chat")
    for p in ("", "/session", "/chat", "/history", "/feedback"):
        assert RH.allowed("site_x", f"/api/aiapp-pub/{mine['code']}{p}", T)
        assert not RH.allowed("site_x", f"/api/aiapp-pub/{theirs['code']}{p}", T)
    assert not RH.allowed("site_x", f"/api/aiapp-pub/{mine['code']}/admin", T)
    assert not RH.allowed("site_x", f"/api/aiapp-pub/{mine['code']}", "")              # no owner known: closed
    assert not RH.allowed("site_x", "/api/aiapp-pub/nosuchcode", T)
    assert RH.allowed("site_x", "/api/site-app/site_x/me", T)                          # wave 7 unchanged


def test_the_site_reads_her_live_app_with_its_website_channel_on(ae_env):
    from app.aiapps import store as AST
    from app.site import prototype as PT
    assert PT.her_ai_app(T) == {}
    a = AST.create(T, "Sunrise helper", "chat", soul={"name": "Sunrise helper", "about": "Bakery",
                                                       "opening": "Ask me about our breads.",
                                                       "suggested": ["When are you open?"]})
    assert PT.her_ai_app(T) == {}                                                       # a draft never shows
    AST.publish(T, a["id"], a["draft_hash"])
    got = PT.her_ai_app(T)
    assert got["code"] == a["code"] and got["name"] == "Sunrise helper" and got["suggested"] == ["When are you open?"]
    assert "AI assistant" in got["notice"] and "key" not in got
    AST.set_channels(T, a["id"], embed=False)
    assert PT.her_ai_app(T) == {}                                                       # she turned the website off
    assert PT.her_ai_app("someone-else") == {}


def test_the_checklist_names_what_is_left():
    from app.appengine import parity
    st = {x["key"]: x for x in parity.check()["rows"]}
    assert st["ai"]["state"] == "partial", st["ai"]
    assert "picture maker" in st["ai"]["missing"][0]
    assert not [k for k, x in st.items() if x["state"] in ("not yet", "blocked")]


# ---------------------------------------------------------------- 2. a real website, live on its own address
@pytest.fixture
def her_ai(ae_env, monkeypatch):
    from app.aiapps import runtime as RT
    from app.aiapps import store as AST
    old = RT.ASK[0]
    RT.ASK[0] = lambda s, p, n: "We are open 8 am to 8 pm, every day."
    a = AST.create(T, "Sunrise helper", "chat", soul={"name": "Sunrise helper", "about": "Bakery in Pune",
                                                       "facts": ["Open 8 am to 8 pm, every day"],
                                                       "opening": "Ask me about our breads.",
                                                       "suggested": ["When are you open?"]})
    AST.publish(T, a["id"], a["draft_hash"])
    yield a["code"]
    RT.ASK[0] = old


def test_a_visitor_agrees_then_asks_her_assistant_on_her_own_address(her_ai, live_clinic):  # noqa: F811
    from playwright.sync_api import sync_playwright
    from app.aiapps import store as AST
    from app.main import app
    sid, code = live_clinic, her_ai
    c = TestClient(app)
    card = c.post(f"/api/sites/{sid}/launch-request", json={}).json()
    assert not card["blockers"], card["blockers"]
    assert c.post(f"/api/sites/{sid}/launch", json={"hash": card["hash"]}).status_code == 200
    other = AST.create("someone-else", "Other shop", "chat")
    AST.publish("someone-else", other["id"], other["draft_hash"])
    r = c.get(f"/api/aiapp-pub/{other['code']}?embed=1", headers={"host": LOCAL})
    assert other["code"] not in r.text                                                  # their assistant never here
    assert c.post(f"/api/aiapp-pub/{other['code']}/session?embed=1", json={"consent": True},
                  headers={"host": LOCAL}).status_code == 404
    seen: list[str] = []
    srv, port = _server()
    base = f"http://{LOCAL}:{port}"
    errors: list[str] = []
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch(args=[f"--host-resolver-rules=MAP {LOCAL} 127.0.0.1"],
                                   **({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
            ctx = b.new_context(viewport={"width": 1280, "height": 900})
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.on("console", lambda m: errors.append(m.text) if m.type == "error" and "Error" in m.text else None)
            pg.on("request", lambda rq: seen.append(rq.method + " " + rq.url) if "/api/aiapp-pub/" in rq.url else None)
            pg.goto(base + "/", wait_until="load")
            box = pg.locator('[data-hoola-ai="notice"]')
            box.wait_for(timeout=30000)
            assert "You are chatting with an AI assistant" in box.inner_text()
            assert not [x for x in seen if x.startswith("POST")]                         # nothing asked before her tap
            box.get_by_role("button", name="I agree").click()
            chat = pg.locator('[data-hoola-ai="chat"]')
            chat.wait_for(timeout=15000)
            chat.get_by_role("button", name="When are you open?").click()                 # a suggested question
            chat.get_by_text("We are open 8 am to 8 pm, every day.").wait_for(timeout=15000)
            chat.get_by_label("Your question").fill("Do you bake on Sunday?")
            chat.get_by_role("button", name="Send").click()
            chat.get_by_text("Do you bake on Sunday?").wait_for(timeout=15000)
            pg.reload(wait_until="load")                                                  # her talk is still there
            again = pg.locator('[data-hoola-ai="chat"]')
            again.wait_for(timeout=30000)
            again.get_by_text("Do you bake on Sunday?").wait_for(timeout=15000)
            b.close()
    finally:
        srv.should_exit = True
    assert not errors, errors
    assert all(code in x for x in seen), seen                                           # only her own app was called
    assert [x for x in seen if "/session" in x] and all("embed=1" in x for x in seen)
