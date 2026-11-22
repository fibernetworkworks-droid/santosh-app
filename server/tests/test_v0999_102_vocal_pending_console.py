"""v0.999.125 HOOLA VOCAL - the console half of "GO BUILD ALL PENDING", walked in a real Chromium on mocked routes:
takes 1 / 2 / 4, the dialogue extras (small reactions, soft music) in the request, Dub it on a sound, own-voice dub lines
changed and made again together, Play while it is made only for a Premium voice, Keep my sounds, and For your own apps
(a key and a webhook secret shown once)."""
import json
from urllib.parse import urlparse

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v0999_96_vocal_redesign_console import CHECKS, CONFIG, FAKE_MIC, ISO, JS, install, open_vocal, overview, page_to
from tests.test_v121_site import site_env  # noqa: F401


def test_the_file_offers_every_pending_piece():
    assert "[[1, '1'], [2, '2'], [4, '4']]" in JS and "[[1, '1'], [2, '2'], [3, '3']]" not in JS
    for k in ("/take/", "/tts/stream", "/apps/keys", "/apps/hooks", "keep_days", "reactions: !!dd2.reactions", "ownredo", "Play while it is made"):
        assert k in JS, k


def extra(pg, st):
    def more(route):
        req = route.request
        path = urlparse(req.url).path[len("/api/vocal"):]
        body = req.post_data_json if req.method in ("POST", "PUT") and req.post_data else None
        j = lambda d, s=200: route.fulfill(status=s, content_type="application/json", body=json.dumps(d))  # noqa: E731
        if path == "/overview":
            o = overview()
            o["status"]["connected"]["stream"] = st["stream"]
            o["history"][0]["text"] = "Is Diwali, Mithas par 20% chhoot."
            o["settings"] = {"keep_days": st["keep"]}
            return j(o)
        if path == "/dialogue":
            st["dialogue"].append(body)
            return j({"id": "vo_dlg", "kind": "dialogue", "title": "Hello", "seconds": 3, "made": ISO(), "ext": "wav", "reactions": 1, "music": "soft"})
        if path.startswith("/take/") and path.endswith("/dub"):
            st["takedub"].append((path, body))
            return j({"items": [{"id": "vo_es", "kind": "tts", "title": "Diwali", "lang": "es", "seconds": 4, "made": ISO(), "ext": "mp3"}], "failed": [], "credits": 2})
        if path == "/tts/stream":
            st["stream_calls"].append(body)
            return j({"url": "/api/vocal/stream/tok_abc", "format": "mp3", "credits": 3, "voice_name": "Thandi"})
        if path == "/stream/tok_abc":
            return route.fulfill(body=b"ID3" + b"\x00" * 64, content_type="audio/mpeg")
        if path == "/settings" and req.method == "PUT":
            st["keep"] = body.get("keep_days", st["keep"])
            st["puts"].append(body)
            return j({"keep_days": st["keep"]})
        if path == "/apps" and req.method == "GET":
            return j({"keys": st["keys"], "hooks": st["hooks"], "events": ["sound.ready", "dub.ready", "dub.failed"], "max_keys": 5, "max_hooks": 3,
                      "rate_hour": 120, "doors": [{"method": "POST", "path": "/api/vocal/v1/speech", "does": "Words in, one take out"}],
                      "signature": "X-Hoola-Signature: t=<unix time>,v1=<hmac>"})
        if path == "/apps/keys":
            k = {"id": "vk_1", "name": body["name"], "last4": "9xYz", "made": ISO(), "used_at": "", "calls": 0}
            st["keys"].append(k)
            return j({**k, "key": "hv_live_SECRETVALUE9xYz", "note": "Copy this key now. It is shown only once."})
        if path.startswith("/apps/keys/") and req.method == "DELETE":
            st["keys"].clear()
            return j({"removed": "vk_1"})
        if path == "/apps/hooks":
            h = {"id": "vh_1", "url": body["url"], "events": ["sound.ready"], "made": ISO(), "last_at": "", "last_status": "", "last_event": ""}
            st["hooks"].append(h)
            return j({**h, "secret": "whsec_TOPSECRET", "note": "Copy the signing secret now. It is shown only once."})
        if path == "/dubs":
            return j({"dubs": [{"id": "db_own", "status": "ready", "mode": "own", "title": "launch.mp4", "langs": ["es"], "made": ISO(-60)}]})
        if path == "/dub/db_own":
            return j({"id": "db_own", "status": "ready", "mode": "own", "source_lang": "en", "title": "launch.mp4",
                      "langs": [{"code": "es", "name": "Spanish", "status": "ready", "video_id": "vo_dv", **({"remaking": True} if st["redo"] else {})}]})
        if path == "/dub/db_own/lines":
            return j({"lang": "es", "mode": "own", "own": True, "editable": True, "remaking": bool(st["redo"]),
                      "note": "Changed lines are made again together when you tap Make the changes.",
                      "lines": [{"n": 0, "start": 0, "end": 2, "speaker": "spk_0", "src": "Hello", "dst": "Hola", "edited": bool(st["saved"])}]})
        if path == "/dub/db_own/lines/0" and req.method == "PUT":
            st["saved"].append(body)
            return j({"n": 0, "dst": body["text"], "edited": True})
        if path == "/dub/db_own/lines/0/redo":
            st["redo"].append(body)
            return j({"status": "working", "lang": "es", "lines": 1, "charged_seconds": 2, "credits": 1})
        return route.fallback()
    pg.route("**/api/vocal/**", more)


def test_the_pending_pieces_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    st = {"calls": [], "tts": [], "sent": [], "rows": [], "items": [], "change": [], "uploads": 0, "settings": [], "addlang": [],
          "stream": False, "keep": 0, "dialogue": [], "takedub": [], "stream_calls": [], "puts": [], "keys": [], "hooks": [],
          "saved": [], "redo": []}
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    ctx.add_init_script(FAKE_MIC)
    pg = ctx.new_page()
    errs, dialogs = [], []
    pg.on("pageerror", lambda e: errs.append(str(getattr(e, "stack", "") or e)[:400]))
    pg.on("dialog", lambda d: (dialogs.append(d.message), d.accept()))
    pg.route("**/api/console/config", lambda r: r.fulfill(json=CONFIG))
    install(pg, st)
    extra(pg, st)
    open_vocal(pg, base)

    # takes 1 / 2 / 4; no stream button while streaming is not connected
    page_to(pg, "speech")
    assert pg.locator("#hvView [data-m='S.takes']").evaluate_all("bs => bs.map(b => b.dataset.val)") == ["1", "2", "4"]
    assert pg.locator("#hvView [data-a='stream']").count() == 0

    # the dialogue extras ride the request
    page_to(pg, "dialogue")
    pg.locator("#hvLt0").fill("Welcome to the show, today we talk about bread.")
    pg.locator("#hvView input[data-m='UI.dlg.reactions']").check()
    pg.locator("#hvView input[data-m='UI.dlg.music']").check()
    pg.locator("#hvView [data-a='dlgmake']").click()
    pg.wait_for_function("() => true")
    pg.wait_for_timeout(500)
    assert st["dialogue"][-1]["reactions"] is True and st["dialogue"][-1]["music"] == "soft"

    # Dub it on a sound: language from the menu, the price asked first, then the request
    page_to(pg, "sounds")
    pg.locator("#hvView [data-a='sndmenu'][data-id='vo_aaaaaaaaaaaa']").click()
    pg.locator(".hmenu .mi", has_text="Dub it into another language").click()
    pg.locator(".hmenu .msearch input").fill("span")
    pg.locator(".hmenu .mi:visible", has_text="Spanish").first.click()
    pg.wait_for_timeout(600)
    assert dialogs and "Spanish" in dialogs[-1] and "credits" in dialogs[-1]
    assert st["takedub"] == [("/take/vo_aaaaaaaaaaaa/dub", {"langs": ["es"], "chat": ""})]

    # own-voice dub: change a line, then Make the changes (asked first)
    page_to(pg, "dub")
    pg.locator("#hvView [data-a='dubopen'][data-id='db_own']").click()
    pg.wait_for_selector("#hvView textarea[data-dubline='0']")
    assert pg.locator("#hvView [data-a='dubredo']").count() == 0                    # no per-line Redo on own voices
    assert pg.locator("#hvView [data-a='ownredo']").is_disabled()
    ta = pg.locator("#hvView textarea[data-dubline='0']")
    ta.fill("Buenas")
    ta.dispatch_event("change")
    pg.wait_for_function("() => !document.querySelector('#hvView [data-a=ownredo]')?.disabled")
    assert st["saved"][-1] == {"lang": "es", "text": "Buenas"}      # the test fires change itself, the blur may fire it again
    pg.locator("#hvView [data-a='ownredo']").click()
    pg.wait_for_function("() => document.querySelector('#hvView').textContent.includes('Making the changed lines')")
    assert st["redo"] == [{"lang": "es"}] and "ElevenLabs charges" in dialogs[-1]

    # Settings: keep my sounds, an app key and a webhook secret shown once
    page_to(pg, "settings")
    pg.wait_for_function("() => document.querySelector('#hvView').textContent.includes('No app keys yet')")
    pg.locator("#hvView [data-a='defkeep']").click()
    pg.locator(".hmenu .mi", has_text="30 days").click()
    pg.wait_for_function("() => document.querySelector('#hvView [data-a=defkeep]').textContent.includes('30 days')")
    assert st["puts"][-1] == {"keep_days": 30}
    pg.locator("#hvKeyN").fill("Shop site")
    pg.locator("#hvView form[data-f='appkey'] button").click()
    pg.wait_for_function("() => document.querySelector('#hvView .hv-once')?.textContent.includes('hv_live_SECRETVALUE9xYz')")
    assert "hv_live_…9xYz" in pg.locator("#hvView").text_content()
    pg.locator("#hvView [data-a='oncehide']").click()
    assert "SECRETVALUE" not in pg.locator("#hvView").text_content()
    pg.locator("#hvHookU").fill("https://shop.example/hoola")
    pg.locator("#hvView form[data-f='apphook'] button").click()
    pg.wait_for_function("() => document.querySelector('#hvView .hv-once')?.textContent.includes('whsec_TOPSECRET')")
    c = pg.evaluate(CHECKS)
    assert not c["sideways"] and not c["wide"] and c["select"] == 0, c["wide"]

    # Play while it is made: only for a Premium voice, only when streaming is connected
    st["stream"] = True
    open_vocal(pg, base)
    page_to(pg, "speech")
    assert pg.locator("#hvView [data-a='stream']").count() == 0                     # Meera is a Standard voice
    pg.locator("#hvView [data-a='vpopen']").first.click()
    pg.locator("#hvVp [data-a='vpuse'][data-id='v_thandi']").click()
    pg.locator("#hvText").fill("Sawubona, welcome to the shop.")
    pg.locator("#hvView [data-a='stream']").click()
    pg.wait_for_function("() => (document.querySelector('#hvAudio')?.getAttribute('src') || '').includes('/api/vocal/stream/tok_abc')")
    assert st["stream_calls"][-1]["voice"] == "v_thandi"
    assert not errs, errs
    ctx.close()

    # the settings page at phone width: nothing sideways
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.route("**/api/console/config", lambda r: r.fulfill(json=CONFIG))
    install(pg, st)
    extra(pg, st)
    open_vocal(pg, base)
    page_to(pg, "settings", narrow=True)
    pg.wait_for_function("() => document.querySelector('#hvView').textContent.includes('For your own apps')")
    c = pg.evaluate(CHECKS)
    assert not c["sideways"] and not c["wide"], c["wide"]
    ctx.close()
