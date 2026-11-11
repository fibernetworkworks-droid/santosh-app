"""v0.782 TEEN MODE (L2 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L2"): Build / Plan / Chat in the Web Studio, with
Plan / Chat enforced on the SERVER (every changing tool refused), plans kept as numbered versions she opens / edits /
approves / skips, a Start building card from Chat, and her standing instructions per website."""
import asyncio
import pathlib

import pytest
from fastapi.testclient import TestClient

from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

CON = pathlib.Path(__file__).resolve().parents[1] / "app" / "static" / "console"
JS = (CON / "webstudio.js").read_text(encoding="utf-8")


def test_mode_line_and_the_server_guard():
    from app.agent import turnmode as TM
    msg = 'Make it blue\n\n[Web console Web Studio: ... (site id site_ab12cd)]\n\n[Web console mode: plan]'
    assert TM.parse(msg) == ("plan", "site_ab12cd")
    assert TM.begin(msg) == "plan"
    assert not TM.allowed("website") and not TM.allowed("email_send")       # changing tools: refused
    assert TM.allowed("website_dekho") and TM.allowed("web_fetch") and TM.allowed("yaad_khojo")   # looking: fine
    assert "Plan mode" in TM.refusal("website") and "PLAN MODE" in TM.rules()
    TM.begin("[Web console mode: chat]")
    assert not TM.allowed("website") and "start-building" in TM.refusal("website") and "CHAT MODE" in TM.rules()
    TM.begin("[Web console mode: build]")
    assert TM.MODE.get() == "" and TM.allowed("website") and TM.rules() == ""
    TM.begin("no studio line at all")
    assert TM.allowed("email_send")


def test_run_tool_refuses_a_change_in_plan_mode(monkeypatch):
    from app.agent import santosh, turnmode as TM
    from app.agent.tools import Ctx, ToolError
    from app.config import get_settings
    ran = []
    monkeypatch.setattr(santosh, "dispatch", lambda n, a, c: ran.append(n) or asyncio.sleep(0, result="done"))

    async def go():
        TM.begin("[Web console mode: plan]")
        with pytest.raises(ToolError) as e:
            await santosh._run_tool("website", {"action": "change"}, Ctx(tenant_id="t1", conversation_id="c1"), get_settings())
        out = await santosh._run_tool("website_dekho", {}, Ctx(tenant_id="t1", conversation_id="c1"), get_settings())
        return str(e.value), out
    err, out = asyncio.run(go())
    assert "did not run" in err and ran == ["website_dekho"] and out == "done"     # the change never reached dispatch


def test_plans_versions_status_and_instructions(site_env):
    from app.site import plans as P
    a = P.add_plan(T, "s1", "## Goal\nBlue hero")
    assert a["version"] == 1 and a["status"] == "draft" and a["source"] == "hoola"
    assert P.add_plan(T, "s1", "## Goal\nBlue hero  ")["version"] == 1      # the same text again = the same version
    b = P.add_plan(T, "s1", "## Goal\nBlue hero, bigger logo", source="her")
    assert b["version"] == 2 and b["source"] == "her"
    P.set_status(T, "s1", 1, "approved")
    P.set_status(T, "s1", 2, "approved")                                    # one approved plan at a time
    st = {p["version"]: p["status"] for p in P.plans(T, "s1")}
    assert st == {2: "approved", 1: "superseded"} and [p["version"] for p in P.plans(T, "s1")] == [2, 1]
    assert P.plans("other-tenant", "s1") == []
    with pytest.raises(P.PlanError):
        P.set_instructions(T, "s1", "x" * 10001)
    P.set_instructions(T, "s1", "Never change the phone number.")
    assert "Never change the phone number." in P.prompt_block(T, "s1")
    assert P.instructions(T, "s2")["text"] == "" and P.prompt_block(T, "s2") == ""


def test_routes_are_hers_only(site_env):
    from app.main import app
    from app.site import service as S
    v = S.new(T, "pet clinic Nagpur", "", name="PawCare")
    c = TestClient(app)
    r = c.post(f"/api/sites/{v['id']}/plans", json={"text": "## Goal\nCalmer hero"}).json()
    assert r["version"] == 1
    assert c.post(f"/api/sites/{v['id']}/plans/1/approve").json()["status"] == "approved"
    assert c.get(f"/api/sites/{v['id']}/plans").json()["plans"][0]["status"] == "approved"
    assert c.post(f"/api/sites/{v['id']}/plans/1/delete").status_code == 400
    assert c.get("/api/sites/site_nope/plans").status_code == 404
    assert c.put(f"/api/sites/{v['id']}/instructions", json={"text": "Warm tone"}).json()["text"] == "Warm tone"
    assert c.get(f"/api/sites/{v['id']}/instructions").json()["max"] == 10000


def test_turn_hint_carries_rules_and_her_instructions(site_env):
    from app.agent import turnmode as TM
    from app.site import plans as P
    P.set_instructions(T, "site_xy99", "Use simple English for parents.")
    TM.begin("hi\n\n[Web console Web Studio: (site id site_xy99)]\n\n[Web console mode: chat]")
    blk = TM.rules() + TM.site_block(T)
    assert "CHAT MODE" in blk and "Use simple English for parents." in blk
    santosh_src = (pathlib.Path(__file__).resolve().parents[1] / "app" / "agent" / "santosh.py").read_text(encoding="utf-8")
    assert "_tmode.begin(user_text)" in santosh_src and "_tmode.allowed(name)" in santosh_src and "_tmode.site_block" in santosh_src


def test_studio_source_wiring():
    for needle in ("const MODES = ['build', 'plan', 'chat']", "`mode: ${mode}`", "/^\\/(plan|chat|build)\\b", "planView",
                   "data-act=\"plan-approve\"", "data-act=\"plan-comment\"", "Save as a new version", "[[start-building",
                   "data-act=\"sb-build\"", "e.altKey", "/instructions", "data-form=\"instr\""):
        assert needle in JS, needle


from tests.test_v0312_arena_screen import arena_server  # noqa: E402,F401  (fixture: uvicorn + Chromium)
from tests.test_v0407_ek_dimaag import arch_env  # noqa: E402,F401


def test_plan_and_chat_modes_in_a_browser(arena_server, arch_env, monkeypatch):
    """A real browser: Plan mode -> the plan card (v1) -> Open plan -> Edit -> v2 -> Approve sends ONE Build message
    with the approved text; Chat mode -> a Start building card -> Build sends that line in Build mode; Alt+P cycles;
    her instructions save from Settings."""
    import os
    import re
    base, browser, key = arena_server
    from app import turn_inbox
    from app.db import Message, session
    from app.events import bus
    got = []
    PLAN = "## Goal\nA calmer hero.\n\n## Steps\n1. Softer colour\n2. Shorter headline"

    async def fake(inbox_id, conv, text, tenant, voice, *a, **k):
        got.append(text)
        with session() as s:
            s.add(Message(conversation_id=conv, role="user", content=text, display=text, in_history=True))
        m = re.search(r"\[Web console mode: (\w+)\]", text)
        mode = m.group(1) if m else ""
        reply = PLAN if mode == "plan" else ("A calmer hero would suit a clinic.\n[[start-building: Make the hero calmer]]"
                                             if mode == "chat" else "Done: the hero is calmer.")
        await asyncio.sleep(0.4)
        with session() as s:
            s.add(Message(conversation_id=conv, role="assistant", content=reply, display=reply, in_history=True))
        bus.publish(conv, "message", {"role": "assistant", "text": reply, "source": "agent"})
        return reply
    monkeypatch.setattr(turn_inbox, "run_owned", fake)
    from app.site import service as S
    a = S.new(T, "pet clinic Nagpur", "", name="PawCare")
    shots = os.environ.get("CONSOLE_SHOTS")
    errors = []
    ctx = browser.new_context(viewport={"width": 1366, "height": 820})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(base + f"/console/web#/site/{a['id']}")
    page.wait_for_selector("#wsTh")
    assert page.locator("[data-cmode]").all_inner_texts() == ["Build", "Plan", "Chat"]
    page.click("[data-cmode='plan']")
    assert "plan first" in page.get_attribute("#wsTh", "placeholder")
    page.fill("#wsTh", "Make the hero calmer")
    page.keyboard.press("Enter")
    page.wait_for_selector("#wsMsgs .plancard[data-ver='1']", timeout=15000)
    assert "[Web console mode: plan]" in got[-1]
    if shots:
        page.screenshot(path=f"{shots}/studio-l2-plancard.png")
    page.click("#wsMsgs .plancard [data-act='plan-open']")
    page.wait_for_selector("#wsPane .plandoc", timeout=4000)
    assert "Shorter headline" in page.inner_text("#wsPane .plandoc")
    page.click("#wsPane [data-act='plan-edit']")
    page.fill("#wsPlanEd", PLAN + "\n3. Keep the Book now button")
    page.click("#wsPane button[type='submit']")
    page.wait_for_selector("#wsPane .dtop:has-text('Plan v2')", timeout=4000)
    if shots:
        page.screenshot(path=f"{shots}/studio-l2-planview.png")
    page.click("#wsPane [data-act='plan-approve']")
    page.wait_for_function("() => [...document.querySelectorAll('#wsMsgs .me')].some(e => e.textContent.includes('Build the approved plan (v2)'))", timeout=6000)
    for _ in range(40):
        if any("approved plan v2" in t for t in got):
            break
        import time
        time.sleep(0.2)
    sent = next(t for t in got if "approved plan v2" in t)
    assert "[Web console mode: build]" in sent and "Keep the Book now button" in sent
    assert page.get_attribute("[data-cmode='build']", "aria-pressed") == "true"
    page.wait_for_selector("#wsMsgs .ho:has-text('Done: the hero is calmer.')", timeout=10000)
    # Chat mode -> Start building
    page.click("[data-cmode='chat']")
    page.fill("#wsTh", "What would make it calmer?")
    page.keyboard.press("Enter")
    page.wait_for_selector("#wsMsgs .sbcard", timeout=15000)
    assert "[[start-building" not in page.inner_text("#wsMsgs")
    page.click("#wsMsgs [data-act='sb-build']")
    page.wait_for_function("() => [...document.querySelectorAll('#wsMsgs .me')].some(e => e.textContent.trim() === 'Make the hero calmer')", timeout=6000)
    # Alt+P cycles Build -> Plan -> Chat
    page.focus("#wsTh")
    page.keyboard.press("Alt+KeyP")
    assert page.get_attribute("[data-cmode='plan']", "aria-pressed") == "true"
    # instructions from Settings
    page.click("[data-view='settings']")
    page.wait_for_selector("#wsInstr")
    page.fill("#wsInstr", "Never change the phone number.")
    page.click("form[data-form='instr'] button[type='submit']")
    page.wait_for_function("() => document.querySelector('#toast') && document.querySelector('#toast').textContent.includes('Instructions saved')", timeout=5000)
    from app.site import plans as P
    assert P.instructions(T, a["id"])["text"] == "Never change the phone number."
    ctx.close()
    errors = [e for e in errors if "The document is sandboxed" not in e]
    assert not errors, errors
