"""v0.655 KAAM DIKHE: the Web Studio shows the job's real steps with their times (her screenshot: '3 looks bana raha
hoon 0%' and nothing else for minutes)."""
import time

from fastapi.testclient import TestClient

from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


def test_activity_steps_counts_and_new_run(tmp_path, monkeypatch):
    from app.site import activity as A
    from app.site import build as B
    monkeypatch.setattr(B, "site_dir", lambda t, s: tmp_path)
    A.step(T, "x", "3 looks soch raha hoon", "3 design")
    A.step(T, "x", "Tasveeren bana raha hoon", "", key="photos", done=1, total=4, alongside=True)
    a = A.read(T, "x")
    assert [s["label"] for s in a["steps"]] == ["Planning three designs", "Making photos for your business"]
    assert all(s["state"] == "run" for s in a["steps"])          # the photos run beside the designs
    A.step(T, "x", "Tasveeren bana raha hoon", "", key="photos", done=3, total=4, alongside=True)
    A.step(T, "x", "3 looks ban rahe hain", "", key="tops", done=0, total=6)
    A.step(T, "x", "3 looks ban rahe hain", "Look 1: Hero written", key="tops", done=1, total=6)
    a = A.read(T, "x")
    assert len(a["steps"]) == 3 and a["steps"][1]["done"] == 3
    assert [s["state"] for s in a["steps"]] == ["done", "done", "run"] and a["steps"][0]["end"] >= a["steps"][0]["at"]
    assert a["steps"][2]["done"] == 1 and a["steps"][2]["note"] == "Look 1: Hero written" and abs(a["now"] - time.time()) < 5
    A.end(T, "x", "Look chuniye", "3 looks taiyaar")
    a = A.read(T, "x")
    assert a["ended"] and all(s["state"] == "done" for s in a["steps"]) and a["steps"][-1]["final"]
    A.step(T, "x", "Design kit bana raha hoon")                 # the next job (the build) starts its own log
    a = A.read(T, "x")
    assert [s["label"] for s in a["steps"]] == ["Making the design kit"] and not a.get("ended")


def test_looks_and_build_leave_a_timed_log(site_env, monkeypatch):
    monkeypatch.setenv("SITE_FULL_LOOKS", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.main import app
    from app.site import service as S
    c = TestClient(app)
    v = S.new(T, "pet clinic Nagpur: vaccination, grooming, shop. Phone 98765 43210", "", name="PawCare")
    assert c.post(f"/api/sites/{v['id']}/plan", json={}).status_code == 200
    a = S.get(T, v["id"])["activity"]
    labels = [s["label"] for s in a["steps"]]
    assert labels[0] == "Planning three designs" and "Writing the top of every look" in labels
    assert "Putting the 3 looks together and taking screenshots" in labels and "Writing every page for the looks" in labels
    tops = next(s for s in a["steps"] if s["label"] == "Writing the top of every look")
    assert tops["total"] >= 3 and tops["done"] == tops["total"]
    assert a["ended"] and a["steps"][-1]["label"] == "Three looks ready: pick one"
    assert all(s["state"] == "done" and s["end"] >= s["at"] for s in a["steps"])
    assert c.post(f"/api/sites/{v['id']}/look", json={"index": 1}).status_code == 200
    b = S.get(T, v["id"])["activity"]
    assert b["started"] > a["started"] and b["steps"][-1]["label"] == "Website ready"


def test_studio_draws_steps_and_timers():
    from pathlib import Path
    js = (Path(__file__).parents[1] / "app/static/console/webstudio.js").read_text()
    for marker in ("actPanel(", "stepList(", "data-t0", "Working for", "steps so far", "drawActivity()", "tickClocks"):
        assert marker in js, marker
    assert "}, 2000);" in js     # polls every 2 s while working


def test_rename_route(site_env):
    from app.main import app
    from app.site import service as S
    c = TestClient(app)
    v = S.new(T, "pet clinic Nagpur", "", name="PawCare")
    r = c.patch(f"/api/sites/{v['id']}", json={"name": "  PawCare   Pet Hospital "})
    assert r.status_code == 200 and r.json()["name"] == "PawCare Pet Hospital"
    assert S.get(T, v["id"])["name"] == "PawCare Pet Hospital"
    assert c.patch(f"/api/sites/{v['id']}", json={"name": ""}).status_code == 400
    assert c.patch(f"/api/sites/{v['id']}", json={"name": "x" * 81}).status_code == 400


from tests.test_v0312_arena_screen import arena_server  # noqa: E402,F401  (fixture: uvicorn + Chromium)
from tests.test_v0407_ek_dimaag import arch_env  # noqa: E402,F401


def test_projects_menu_and_chat_timer_in_a_browser(arena_server, arch_env):
    """v0.658 her screenshots: no menu on a project (rename / delete / star like Lovable) and no timer while the site
    chat answers. The sidebar + card menus rename, star and delete; search filters; a sent line shows a ticking timer."""
    import os
    base, browser, key = arena_server
    from app.site import service as S
    a = S.new(T, "pet clinic Nagpur", "", name="PawCare")
    S.new(T, "sweet shop Akola", "", name="Sharma Sweets")
    shots = os.environ.get("CONSOLE_SHOTS")
    errors = []
    ctx = browser.new_context(viewport={"width": 1366, "height": 860})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(base + "/console/web")
    page.wait_for_selector("#ws .side .rec .rm")
    side = page.inner_text("#ws .side")
    for word in ("Home", "Search", "All websites", "Starred", "Templates", "PawCare", "Sharma Sweets"):
        assert word in side, word
    # the sidebar menu: open, items, star
    page.hover("#ws .side .rec:has-text('PawCare')")
    page.click("#ws .side .rec:has-text('PawCare') .rm")
    page.wait_for_selector("#wsMenu")
    assert [t.strip() for t in page.locator("#wsMenu button").all_inner_texts()] == \
        ["Open", "Open in new tab", "Rename", "Add to starred", "Delete"]
    if shots:
        page.screenshot(path=f"{shots}/studio-menu.png")
    page.click("#wsMenu [data-mi='star']")
    page.wait_for_selector("#ws .side .lbl:has-text('Starred')")
    # rename through the dialog
    page.click("#ws .side .rec:has-text('PawCare') .rm")
    page.click("#wsMenu [data-mi='rename']")
    page.fill("#wsRename", "PawCare Pet Hospital")
    page.click("dialog [value='ok']")
    page.wait_for_selector("#ws .side .rec:has-text('PawCare Pet Hospital')")
    assert S.get(T, a["id"])["name"] == "PawCare Pet Hospital"
    # All websites: search + the card menu
    page.click("#ws .side a.nav:has-text('All websites')")
    page.wait_for_selector("#wsFind")
    page.fill("#wsFind", "sharma")
    assert page.locator("#wsAll .cw:visible").count() == 1
    page.fill("#wsFind", "")
    page.hover("#wsAll .cw:has-text('Sharma Sweets')")
    page.click("#wsAll .cw:has-text('Sharma Sweets') .cm")
    page.click("#wsMenu [data-mi='delete']")          # the confirm is accepted
    page.wait_for_selector("#wsAll .cw:has-text('Sharma Sweets')", state="detached")
    assert all(v["name"] != "Sharma Sweets" for v in S.sites(T))
    # Starred page
    page.click("#ws .side a.nav:has-text('Starred')")
    page.wait_for_selector("#ws .hmain .cw:has-text('PawCare Pet Hospital')")
    # the site chat: a sent line shows the work feed with a ticking timer
    page.goto(base + f"/console/web#/site/{a['id']}")
    page.wait_for_selector("#wsTh")
    page.fill("#wsTh", "Hero ko aur premium banao")
    page.keyboard.press("Enter")
    page.wait_for_selector("#wsMsgs .working .tm", timeout=5000)
    t = page.evaluate("(document.querySelector('#wsMsgs .working .tm') || {}).textContent || ''")
    assert t == "" or t.endswith("s"), t           # the row can be gone already when the test turn fails at once
    if shots:
        page.screenshot(path=f"{shots}/studio-chat-timer.png")
    ctx.close()
    errors = [e for e in errors if "The document is sandboxed" not in e]
    assert not errors, errors


def test_chat_shows_live_steps_timer_then_worked_for(arena_server, arch_env, monkeypatch):
    """v0.658 her screenshot: 'NEED MORE PREMIUMNESS' and only three dots. A turn's tool steps now show live with a
    ticking timer, and the answer keeps 'Worked for N · 3 steps' with each step's own time. Also caught here: a new
    site chat starts with a greeting, which the old answer check took for the answer and stopped waiting at once."""
    import asyncio
    import time
    base, browser, key = arena_server
    from app import turn_inbox
    from app.db import Message, session
    from app.events import bus

    async def fake(inbox_id, conv, text, tenant, voice, *a, **k):
        with session() as s:
            s.add(Message(conversation_id=conv, role="user", content=text, display=text, in_history=True))
        for i, lab in enumerate(["Website padh raha hoon", "Hero badal raha hoon", "Naya version jaanch raha hoon"]):
            bus.publish(conv, "step", {"tool": "website", "label": lab, "state": "running", "id": f"t{i}"})
            await asyncio.sleep(1.6)
            bus.publish(conv, "step", {"tool": "website", "label": lab, "state": "done", "id": f"t{i}"})
        with session() as s:
            s.add(Message(conversation_id=conv, role="assistant", content="Hero ab premium hai.", display="Hero ab premium hai.",
                          in_history=True))
        return ""
    monkeypatch.setattr(turn_inbox, "run_owned", fake)
    from app.site import service as S
    a = S.new(T, "pet clinic Nagpur", "", name="PawCare")
    ctx = browser.new_context(viewport={"width": 1366, "height": 760})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    page = ctx.new_page()
    page.goto(base + f"/console/web#/site/{a['id']}")
    page.wait_for_selector("#wsTh")
    page.fill("#wsTh", "NEED MORE PREMIUMNESS")
    page.keyboard.press("Enter")
    page.wait_for_selector("#wsMsgs .working .acts li", timeout=8000)
    t1 = page.inner_text("#wsMsgs .working .step .tm")
    time.sleep(2.2)
    assert page.locator("#wsMsgs .working").count() == 1
    t2 = page.inner_text("#wsMsgs .working .step .tm")
    assert t1 != t2 and t2.endswith("s"), (t1, t2)          # the timer ticks while Hoola works
    page.wait_for_selector("#wsMsgs details.turnw", timeout=20000)
    summary = page.inner_text("#wsMsgs details.turnw summary")
    assert summary.startswith("Worked for ") and summary.endswith("3 steps"), summary
    page.click("#wsMsgs details.turnw summary")
    times = page.locator("#wsMsgs details.turnw .tm").all_inner_texts()
    assert len(times) == 3 and all(x != "0s" for x in times), times     # each step's own time, not 0s
    assert "Hero ab premium hai." in page.inner_text("#wsMsgs")
    ctx.close()
