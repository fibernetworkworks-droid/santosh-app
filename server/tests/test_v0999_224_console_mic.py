"""v0.999.224 THE CHAT BOX MICROPHONE (owner: "THE CONSOLE MICROPHONE NOT FUNCTIONING PROPERLY - FIND THE BUG, DESIGN -
MAKE IT ADVANCED, PREMIUM AND PROFESSIONAL - MATCHING THIS CHAT PANEL DESIGN"). The old mic always listened for Hindi,
wrote the sent message back into the box, went off silently after a pause and overwrote her typing; dictate.js fixes
each and draws one recording bar in the page's ink. Driven here with a stand-in for the browser's speech service."""
from __future__ import annotations

import json
import os
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

CON = Path(__file__).resolve().parents[2] / "server/app/static/console"
JS = (CON / "dictate.js").read_text(encoding="utf-8")
V2 = (CON / "v2.js").read_text(encoding="utf-8")

FAKE = """
window.__sr = [];
class FakeSR {
  constructor(){ this.lang=''; window.__sr.push(this); this.res=[]; }
  start(){ this.started=true; }
  stop(){ this.stopped=true; setTimeout(()=>this.onend&&this.onend(),0); }
  abort(){ this.aborted=true; setTimeout(()=>this.onend&&this.onend(),0); }
  say(t, fin){ const r=[{transcript:t}]; r.isFinal=!!fin; const i=this.res.findIndex(x=>!x.isFinal); if(i>=0) this.res[i]=r; else this.res.push(r);
    const idx=this.res.indexOf(r); this.onresult&&this.onresult({resultIndex:idx, results:this.res}); }
  fail(e){ this.onerror&&this.onerror({error:e}); this.onend&&this.onend(); }
  endByItself(){ this.onend&&this.onend(); }
}
window.SpeechRecognition = FakeSR; window.webkitSpeechRecognition = FakeSR;
Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
"""


def test_shape():
    assert "hi-IN'; r.interimResults" not in V2 and "go('baat'); return; }" not in V2      # no forced Hindi, no jump to the call
    assert "window.HoolaDictate" in JS and "composer.addEventListener('submit'" in JS
    assert "#micBtn.on{animation:none" in (CON / "v2.css").read_text(encoding="utf-8")


def last(pg):
    return "window.__sr[window.__sr.length-1]"


def test_mic_walk(arena_server):  # noqa: F811
    base, browser, key = arena_server
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    ctx.add_init_script(FAKE)
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))

    def config(route):
        r = route.fetch(); d = r.json(); d["app_design"] = True; d["human"] = True
        route.fulfill(response=r, body=json.dumps(d))
    pg.route("**/api/console/config", config)
    pg.goto(base + "/console/")
    pg.wait_for_selector("html.appd #snav .sn"); pg.wait_for_timeout(4000)   # the first chat opens and sets the box
    L = last(pg)
    pg.locator("#micBtn").click(); pg.wait_for_selector("#composer.dicting .dictbar:not([hidden])")
    assert pg.evaluate(f"{L}.lang") == "en-US"                                            # her language, not Hindi
    assert pg.evaluate("document.querySelector('#micBtn').getAttribute('aria-pressed')") == "true"
    pg.evaluate(f"{L}.say('hello there', false)")
    assert pg.input_value("#msg") == "hello there"
    pg.evaluate(f"{L}.say('hello there team', true)")
    pg.wait_for_timeout(300)
    shots = os.environ.get("HOOLA_SHOTS")
    if shots:
        pg.screenshot(path=f"{shots}/mic-home.png")
    bar = pg.evaluate("""()=>{const b=document.querySelector('.dictbar').getBoundingClientRect(), k=document.querySelector('.dictbar .dok'),
        s=getComputedStyle(k); return {w:b.width, okbg:s.backgroundColor, ink:getComputedStyle(document.documentElement).getPropertyValue('--ink').trim(),
        others:[...document.querySelectorAll('#composer .row>*:not(.dictbar)')].filter(e=>e.offsetParent).length}}""")
    assert bar["w"] > 400 and bar["others"] == 0, bar                                       # one bar takes the row
    assert bar["okbg"] == "rgb(27, 26, 23)", bar                                            # Done in ink, not violet / red
    # Chrome closes the session after a pause: it carries on in a new one
    n = pg.evaluate("window.__sr.length"); pg.evaluate(f"{L}.endByItself()"); pg.wait_for_timeout(100)
    assert pg.evaluate("window.__sr.length") == n + 1 and pg.is_visible(".dictbar")
    pg.evaluate(f"{L}.say('and more', true)")
    assert pg.input_value("#msg") == "hello there team and more"
    # her typing is kept and dictation goes on after it
    pg.locator("#msg").press("End"); pg.keyboard.type(" typed")
    pg.wait_for_timeout(900)
    pg.evaluate(f"{L}.say('spoken', true)")
    assert pg.input_value("#msg") == "hello there team and more typed spoken"
    # the language menu restarts listening in the new language and is remembered
    pg.locator(".dictbar .dlang").click(); pg.wait_for_selector(".hmenu.dlangm.on")
    pg.locator(".hmenu.dlangm .mi", has_text="Hindi").click(); pg.wait_for_timeout(100)
    assert pg.evaluate(f"{L}.lang") == "hi-IN" and pg.evaluate("localStorage.getItem('hoola.dictate.lang')") == "hi-IN"
    # Esc cancels: the words from before dictation come back (here: an empty box)
    pg.keyboard.press("Escape"); pg.wait_for_timeout(100)
    assert not pg.is_visible(".dictbar") and pg.input_value("#msg") == ""
    # Done keeps the words; no more writing after it
    pg.locator("#micBtn").click(); pg.wait_for_selector(".dictbar:not([hidden])")
    pg.evaluate(f"{L}.say('keep this', true)"); pg.locator(".dictbar .dok").click(); pg.wait_for_timeout(100)
    assert pg.input_value("#msg") == "keep this" and not pg.is_visible(".dictbar")
    # the bug: sending while it listens - the sent words never come back into the box
    pg.fill("#msg", ""); pg.locator("#micBtn").click(); pg.wait_for_selector(".dictbar:not([hidden])")
    pg.evaluate(f"window.__keep = {L}; {L}.say('send me', true)")
    pg.evaluate("document.querySelector('#composer').requestSubmit()"); pg.wait_for_timeout(400)
    assert not pg.is_visible(".dictbar")
    pg.evaluate("window.__keep.say('send me again', false)"); pg.wait_for_timeout(100)
    assert "send me" not in pg.input_value("#msg")
    # a broken microphone says why
    pg.locator("#micBtn").click(); pg.wait_for_selector(".dictbar:not([hidden])")
    pg.evaluate(f"{L}.fail('audio-capture')"); pg.wait_for_timeout(150)
    assert not pg.is_visible(".dictbar") and "No microphone" in pg.inner_text("#toast")
    # inside a chat the bar sits on the row under the box
    pg.evaluate("document.querySelector('#composer').classList.remove('home')")
    pg.locator("#micBtn").click(); pg.wait_for_selector(".dictbar:not([hidden])")
    pg.evaluate(f"{L}.say('in a chat', false)"); pg.wait_for_timeout(300)
    if shots:
        pg.screenshot(path=f"{shots}/mic-chat.png")
    pg.locator(".dictbar .dx").click()
    assert not errors, errors
    ctx.close()
