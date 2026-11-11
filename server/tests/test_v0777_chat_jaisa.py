"""v0.777 CHAT JAISA (L1 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L1"): the Web Studio chat like Lovable - the live
event stream instead of 1.5 s polling, soft word fade, a Thinking shimmer, present -> past tool verbs, a Details view
(Timeline + Changes), the turn's own rupees, queued follow-ups, attachments + long-paste chips."""
import asyncio
import json
import pathlib
import re
import subprocess

from fastapi.testclient import TestClient

from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

CON = pathlib.Path(__file__).resolve().parents[1] / "app" / "static" / "console"
JS = (CON / "webstudio.js").read_text(encoding="utf-8")


def test_turn_meter_counts_its_calls_and_nests_with_a_run_meter():
    from app import usage
    with usage.turn_meter() as t:
        usage.record("claude-haiku-5-5", 1000, 200, tenant="t1")
        with usage.run_meter() as r:                       # a research run inside the turn keeps its own meter
            usage.record("claude-haiku-5-5", 500, 100, tenant="t1")
    assert t["calls"] == 2 and r["calls"] == 1 and t["usd"] > r["usd"] > 0
    usage.record("claude-haiku-5-5", 10, 10, tenant="t1")  # outside: counted nowhere here
    assert t["calls"] == 2


def test_costs_row_route_and_run_turn_writes_one(site_env, monkeypatch):
    from app import turncost, usage
    from app.agent import santosh
    from app.db import now
    from app.main import app
    turncost.record(T, "c-none", now(), {"usd": 0.0, "calls": 0})          # no model call = no row
    assert turncost.recent("c-none") == []

    async def fake(conv, text, tenant, *a, **k):
        usage.record("claude-sonnet-5-5", 20000, 1000, tenant=tenant)
        return "ok"
    monkeypatch.setattr(santosh, "_run_turn", fake)
    c = TestClient(app)
    conv = c.post("/api/conversations", json={"title": "Website · test"}).json()
    cid = conv.get("id") or conv.get("conversation_id")
    assert asyncio.run(santosh.run_turn(cid, "hello", T)) == "ok"
    rows = c.get(f"/api/conversations/{cid}/costs").json()["costs"]
    assert len(rows) == 1 and rows[0]["calls"] == 1 and rows[0]["inr"] > 0 and rows[0]["start"] and rows[0]["end"]


def test_every_english_step_verb_has_its_past_tense():
    """Every tool label's first -ing word (agent/labels_en.py) turns past tense when the step is done."""
    from app.agent.labels_en import LABELS_EN
    past = dict(re.findall(r"(\w+ing): '(\w+)'", JS[JS.index("const PAST"):JS.index("const pastLabel")]))
    firsts = {v.split()[0] for v in LABELS_EN.values() if re.match(r"^[A-Z][a-z]+ing$", v.split()[0])}
    missing = sorted(firsts - set(past))
    assert not missing, missing
    out = subprocess.run(["node", "-e", JS[JS.index("const PAST"):JS.index("const LONG_PASTE")].replace("const ", "var ")
                          + "\nconst S=v=>v==null?'':String(v);console.log(JSON.stringify([pastLabel('Reading the site','done'),"
                          "pastLabel('Reading the site','run'),pastLabel('Writing Home hero','done'),pastLabel('Sandarbh: x','done')]))"],
                         capture_output=True, text=True, timeout=30)
    assert json.loads(out.stdout) == ["Read the site", "Reading the site", "Wrote Home hero", "Sandarbh: x"], out.stderr


def test_studio_source_wiring():
    html = (CON / "webstudio.html").read_text(encoding="utf-8")
    css = (CON / "webstudio.css").read_text(encoding="utf-8")
    assert "/static/console/stream.js" in html and html.index("md.js") < html.index("stream.js") < html.index("webstudio.js")
    for needle in ("HoolaStream.open", "/events", "new window.HoolaMD.Live(el, {soft: true})", "'reply_start'", "'delta'",
                   "'think'", "class=\"thinking\"", "data-act=\"details\"", "data-act=\"stop-turn\"", "/costs?limit=",
                   "data-act=\"attach\"", "LONG_PASTE", "THREAD.queue", "detailsView", "data-dtab", "jump-latest"):
        assert needle in JS, needle
    for needle in ("@keyframes ws-word", "@keyframes ws-think", ".me.queued", ".fchip", ".tline"):
        assert needle in css, needle
    rm = css[css.rindex("@media (prefers-reduced-motion:reduce)"):]
    assert ".ho .w" in rm and ".thinking" in rm                # every new motion stops under reduced motion


from tests.test_v0312_arena_screen import arena_server  # noqa: E402,F401  (fixture: uvicorn + Chromium)
from tests.test_v0407_ek_dimaag import arch_env  # noqa: E402,F401


def test_live_chat_in_a_browser(arena_server, arch_env, monkeypatch):
    """A real browser on the Studio: the reply streams in word by word (soft-fade spans), Thinking shimmers first, the
    steps run present tense and end past tense, the answer keeps Worked for · steps · Rs, Details opens the Timeline,
    a second message sent while working waits greyed, and a long paste becomes a chip."""
    import os
    import time
    base, browser, key = arena_server
    from app import turn_inbox, turncost
    from app.db import Message, now, session
    from app.events import bus
    gate = {"go": False}

    async def fake(inbox_id, conv, text, tenant, voice, *a, **k):
        t0 = now()
        with session() as s:
            s.add(Message(conversation_id=conv, role="user", content=text, display=text, in_history=True))
        if "second" in text:
            return ""
        await asyncio.sleep(0.6)
        bus.publish_live(conv, "think", {"turn": "tr1", "seg": 0, "seq": 1, "text": "hmm"})
        await asyncio.sleep(1.4)
        bus.publish(conv, "step", {"tool": "website", "label": "Reading the site", "state": "running", "id": "s1"})
        await asyncio.sleep(1.2)
        bus.publish(conv, "step", {"tool": "website", "label": "Reading the site", "state": "done", "id": "s1"})
        for _ in range(40):
            if gate["go"]:
                break
            await asyncio.sleep(0.25)
        bus.publish_live(conv, "reply_start", {"turn": "tr1"})
        words = "The hero now has a deeper colour and a calmer headline for your clinic."
        for i, w in enumerate(words.split(" ")):
            bus.publish_live(conv, "delta", {"turn": "tr1", "seg": 0, "seq": i + 1, "text": w + " "})
            await asyncio.sleep(0.12)
        bus.publish_live(conv, "reply_end", {"turn": "tr1"})
        await asyncio.sleep(0.8)
        with session() as s:
            s.add(Message(conversation_id=conv, role="assistant", content=words, display=words, in_history=True))
        turncost.record(tenant, conv, t0, {"usd": 0.035, "calls": 3})
        bus.publish(conv, "message", {"role": "assistant", "text": words, "source": "agent", "turn": "tr1"})
        return words
    monkeypatch.setattr(turn_inbox, "run_owned", fake)
    from app.site import service as S
    a = S.new(T, "pet clinic Nagpur", "", name="PawCare")
    shots = os.environ.get("CONSOLE_SHOTS")
    errors = []
    ctx = browser.new_context(viewport={"width": 1366, "height": 820})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base + f"/console/web#/site/{a['id']}")
    page.wait_for_selector("#wsTh")
    page.fill("#wsTh", "Make the hero more premium")
    page.keyboard.press("Enter")
    page.wait_for_selector("#wsMsgs .thinking", timeout=8000)          # the shimmer while the model reasons
    page.wait_for_selector("#wsMsgs .working .acts li", timeout=8000)
    page.fill("#wsTh", "and a second change")                          # sent while Hoola works: waits greyed
    page.keyboard.press("Enter")
    page.wait_for_selector("#wsQ .me.queued", timeout=4000)                 # at the BOTTOM, under the work
    big = "line of pasted notes\n" * 120
    page.focus("#wsTh")
    page.evaluate("t => { const dt = new DataTransfer(); dt.setData('text/plain', t); document.querySelector('#wsTh').dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true})); }", big)
    page.wait_for_selector("#wsTray .fchip:has-text('Pasted')", timeout=6000)
    assert page.input_value("#wsTh") == ""                             # the long paste did not land in the box
    gate["go"] = True
    page.wait_for_selector("#wsLiveBox:not([hidden]) .ho", timeout=8000)
    time.sleep(0.5)
    soft = page.locator("#wsLiveBox .ho .w").count()
    assert soft > 0                                                   # the newest words fade in (soft spans)
    if shots:
        page.screenshot(path=f"{shots}/studio-l1-streaming.png")
    page.wait_for_selector("#wsMsgs details.turnw", timeout=15000)
    summary = page.inner_text("#wsMsgs details.turnw summary")
    assert summary.startswith("Thought for ") and "Worked for " in summary and "1 step" in summary and "Rs " in summary, summary
    page.click("#wsMsgs details.turnw summary")
    assert "Read the site" in page.inner_text("#wsMsgs details.turnw")  # past tense once done
    assert "1 steps" not in summary
    page.click("#wsMsgs [data-act='details']")
    page.wait_for_selector("#wsPane .tline li", timeout=4000)
    assert "Read the site" in page.inner_text("#wsPane .tline")
    page.click("#wsPane [data-dtab='changes']")
    page.wait_for_selector("#wsPane .main", timeout=3000)
    if shots:
        page.screenshot(path=f"{shots}/studio-l1-details.png")
    page.click("#wsPane [data-view='preview']")
    ctx.close()
    errors = [e for e in errors if "The document is sandboxed" not in e]
    assert not errors, errors
