"""v0.999.90 HOOLA VOCAL, GLOBAL - the console page (static/console/vocal.js + vocal2.css) walked in a real Chromium.

The server half of the contract (docs/HOOLA_VOCAL_GLOBAL.md) is mocked here route by route with contract-shaped JSON,
so this test checks the PAGE: every menu page opens with exactly one heading, no script error, no sideways scroll at
1280 and at 390 wide; every disabled control says why beside it; the speech request is contract-shaped; the Vocal chat
appends the settings note to her message and never shows it in her bubble; her text is never run as HTML.
v0.999.96 (docs/HOOLA_VOCAL_REDESIGN.md) moved the page onto the Create Studio frame, so the pins changed with the
contract: 13 sidebar rows in four groups (History is Your sounds; Languages lives under Settings), the one heading is
the crumb, every dropdown is the console menu (.hmenu, not the old .hv-pop), the 1-to-3 takes and formats come from
the overview, and a disabled premium control says ElevenLabs is not connected WITHOUT naming the server key. The
redesign's own walk is tests/test_v0999_96_vocal_redesign_console.py."""
import json
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

CONFIG = {"app": "Hoola", "v2": True, "stream": True, "sessions": True, "panel": True, "projects": True, "human": True,
          "interactive": True, "vocal": True}
NOW = datetime.now(timezone.utc)
ISO = lambda s=0: (NOW + timedelta(seconds=s)).isoformat()  # noqa: E731

OVG = {
    "voices": [
        {"id": "v_amani", "name": "Amani", "gender": "female", "age": "middle", "tone": "Warm, gentle", "accent": "Kenya", "langs": ["sw", "en"],
         "use": "Narration", "engine": "gemini", "tier": "standard", "kind": "hoola", "ready": True, "color": "#C9E7DF"},
        {"id": "v_lucia", "name": "Lucía", "gender": "female", "age": "young", "tone": "Bright, friendly", "accent": "Mexico", "langs": ["es", "en"],
         "use": "Ads", "engine": "gemini", "tier": "standard", "kind": "hoola", "ready": True, "color": "#F6C7D6"},
        {"id": "v_thandi", "name": "Thandi", "gender": "female", "age": "middle", "tone": "Rich, confident", "accent": "South Africa", "langs": ["zu"],
         "use": "Conversation", "engine": "eleven", "tier": "premium", "kind": "hoola", "ready": False, "color": "#E8D9C9"},
        {"id": "v_mine", "name": "<i>Mine</i>", "gender": "", "age": "", "tone": "Your recording", "accent": "", "langs": ["en"], "use": "",
         "engine": "gemini", "tier": "standard", "kind": "clone", "ready": True, "color": "#D7D2F2"}],
    "langs": [
        {"code": "en", "name": "English", "native": "English", "region": "Europe", "speech": "yes", "clone": "yes", "dialogue": "yes", "dub": "yes", "voices": 30, "quality": "excellent"},
        {"code": "sw", "name": "Swahili", "native": "Kiswahili", "region": "Africa", "speech": "yes", "clone": "yes", "dialogue": "yes", "dub": "yes", "voices": 9, "quality": "good"},
        {"code": "ja", "name": "Japanese", "native": "日本語", "region": "Asia", "speech": "yes", "clone": "yes", "dialogue": "yes", "dub": "yes", "voices": 18, "quality": "excellent"},
        {"code": "es", "name": "Spanish", "native": "Español", "region": "Americas", "speech": "yes", "clone": "yes", "dialogue": "yes", "dub": "yes", "voices": 38, "quality": "excellent"},
        {"code": "zu", "name": "Zulu", "native": "isiZulu", "region": "Africa", "speech": "premium", "clone": "premium", "dialogue": "premium", "dub": "yes", "voices": 4, "quality": "fair"},
        {"code": "qu", "name": "Quechua", "native": "Runa Simi", "region": "Americas", "speech": "none", "clone": "none", "dialogue": "none", "dub": "none", "voices": 0, "quality": "none"}],
    "styles": {"warm": "Warm", "news": "News", "story": "Story"},
    "feelings": ["warm", "whispers", "laughs", "sighs", "excited", "serious", "slowly", "cheerful"],
    "engines": [{"id": "gemini", "name": "Gemini voice", "does": "Speech, dialogue, readings", "langs": "130+ languages", "state": "ready"},
                {"id": "eleven", "name": "ElevenLabs", "does": "Premium voice, voice changer, sound effects", "langs": "90+ languages", "state": "needs_key"},
                {"id": "lab", "name": "Hoola GPU lab", "does": "Clone and design fallback", "langs": "", "state": "off"},
                {"id": "server", "name": "Hoola server", "does": "Noise clean-up, loudness, joining", "langs": "Any language", "state": "ready"}],
    "prices": [{"job": "tts", "engine": "gemini", "credits": 15, "usd": 0.015}, {"job": "dub_own", "engine": "eleven", "credits": 2200, "usd": 2.2},
               {"job": "cleanup", "engine": "server", "credits": 0, "usd": 0}],
    "rules": [{"id": "pr_1", "word": "Akola", "say": "Uh-ko-laa", "lang": ""}],
    "history": [{"id": "vo_aaaaaaaaaaaa", "kind": "tts", "title": "<b>Karibu</b> Mkate", "voice_name": "Amani", "lang": "sw", "engine": "gemini",
                 "seconds": 12, "made": ISO(-3600), "ext": "wav", "credits": 4}],
    "projects": [{"id": "vp_1", "title": "The Lighthouse Keeper", "lang": "en", "voice": "v_amani", "made": ISO(-7200),
                  "chapters": [{"title": "The Island", "text": "The wind came first.", "audio": "vo_aaaaaaaaaaaa", "seconds": 4}, {"title": "The Storm", "text": "Then the rain."}]}],
    "usage": {"month": "2026-11", "made": 1, "characters": 40, "minutes": 0.2, "by_kind": {"tts": 1}, "kept": 1, "kept_max": 200, "credits_left": 4820},
    "limits": {"characters": 100000, "lines": 40, "history": 200},
    "sfx": ["coin", "jump"],
    "status": {"engines": {}, "connected": {"clone": True, "design": True}},
}
PAGES = [("chat", "nothing is spent until you send"), ("speech", "Add a tone"), ("voices", "Amani"), ("mine", "Read this out loud"),
         ("dialogue", "How it sounds"), ("studio", "The Lighthouse Keeper"), ("dub", "product-tour.mp4"), ("changer", "ElevenLabs is not connected"),
         ("cleanup", "Take the voice out of music"), ("sfx", "Quick game sounds"), ("dict", "Uh-ko-laa"), ("sounds", "<b>Karibu</b> Mkate"),
         ("settings", "What things cost")]

UNSAID = """() => [...document.querySelectorAll('#hvView :is(button,input,select,textarea):disabled')].map(e => {
  const id = e.getAttribute('aria-describedby'), w = id && document.getElementById(id);
  return (w && w.textContent.trim()) || e.closest('.hv-vrow,.hv-mv,.hv-snd,.hv-sample') ? null : e.outerHTML.slice(0, 140); }).filter(Boolean)"""
WIDE = """() => [...document.querySelectorAll('#hvView *')].filter(e => e.getClientRects().length && e.getBoundingClientRect().right > document.querySelector('#hvView').getBoundingClientRect().right - 30)
  .slice(0, 8).map(e => e.tagName + '.' + e.className + ' ' + Math.round(e.getBoundingClientRect().left) + '-' + Math.round(e.getBoundingClientRect().right)).join(' | ')"""
STACKED = """() => [...document.querySelectorAll('#hvView .hv-split')].every(g => { const [a, b] = g.children; if (!a || !b) return true;
  const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect(); return rb.top >= ra.bottom - 1 || rb.left >= ra.right - 1; })"""
NO_SIDEWAYS = """() => { const v = document.querySelector('#hvView'), r = document.querySelector('#hvRoot');
  return v.scrollWidth <= v.clientWidth + 1 && r.scrollWidth <= r.clientWidth + 1 && document.documentElement.scrollWidth <= innerWidth + 1; }"""


def install(pg, st):
    """Routes the page calls, contract-shaped. `st` keeps what was sent and the chat's rows."""
    def vocal(route):
        req = route.request
        u = urlparse(req.url)
        path, qs = u.path[len("/api/vocal"):], parse_qs(u.query)
        body = req.post_data_json if req.method in ("POST", "PUT") and req.post_data else None
        st["calls"].append((req.method, path, body))
        j = lambda d, s=200: route.fulfill(status=s, content_type="application/json", body=json.dumps(d))  # noqa: E731
        if path == "/overview":
            return j(OVG)
        if path in ("/audio", "/voice/preview"):
            return route.fulfill(body=b"RIFF\x24\x00\x00\x00WAVEfmt ", content_type="audio/wav")
        if path == "/quote":
            n = 11 * int((body or {}).get("takes") or 1)
            return j({"credits": n, "usd": n / 1000, "engine": "gemini", "engine_name": "Gemini voice", "line": "nothing is spent until you press it"})
        if path == "/tts":
            st["tts"].append(body)
            return j({"items": [{"id": f"vo_t{i}", "kind": "tts", "title": "Karibu", "voice_name": "Amani", "lang": "sw", "engine": "gemini", "seconds": 3,
                                 "made": ISO(), "ext": "wav", "take": "AB"[i], "job": "jb_x"} for i in range(int(body.get("takes") or 1))],
                      "lang": "sw", "lang_name": "Swahili", "engine": "gemini", "credits": 22})
        if path == "/chat":
            return j({"id": "vc_1", "title": "Vocal chat"})
        if path.startswith("/chat/vc_1/ok"):
            return j({"ok": True})
        if path == "/chat/vc_1/items":
            return j({"items": st["items"]})
        if path == "/chats":
            return j({"chats": [{"id": "vc_1", "title": "Vocal chat", "at": ISO()}]})
        if path == "/consent-line":
            return j({"line": "Ninakubali Hoola itengeneze sauti yangu.", "english": "I agree that Hoola makes my voice.", "lang": qs.get("lang", ["en"])[0], "locale": "sw-KE"})
        if path == "/dubs":
            return j({"dubs": [{"id": "db_1", "status": "ready", "title": "product-tour.mp4", "langs": ["ja"], "made": ISO(-60)}]})
        if path == "/dub/db_1":
            return j({"id": "db_1", "status": "ready", "mode": "matched", "source_lang": "en", "title": "product-tour.mp4",
                      "langs": [{"code": "ja", "name": "日本語 Japanese", "status": "ready", "audio_id": "vo_dub"}],
                      "lines": [{"start": 4, "end": 9, "speaker": "Sara", "text": "This screen shows every order.", "tr": {"ja": "この画面で注文を確認できます。"}}]})
        return j({"detail": "not mocked"}, 404)

    def conv(route):
        req = route.request
        path = urlparse(req.url).path
        j = lambda d: route.fulfill(content_type="application/json", body=json.dumps(d))  # noqa: E731
        if path.endswith("/messages") and req.method == "POST":
            b = req.post_data_json
            st["sent"].append(b)
            st["rows"].append({"id": "m1", "role": "user", "text": b["text"], "at": ISO(1)})
            st["rows"].append({"id": "m2", "role": "assistant", "text": "Here are two takes, in Kiswahili.", "at": ISO(3)})
            st["items"][:] = [{"id": f"vo_c{i}", "kind": "tts", "title": "Karibu Mkate Bora", "voice_name": "Amani", "lang": "sw", "engine": "gemini",
                               "seconds": 6, "made": ISO(2), "ext": "wav", "take": "AB"[i], "job": "jb_1", "chat": "vc_1", "credits": 2} for i in range(2)]
            return j({"ok": True})
        if path.endswith("/messages"):
            return j({"messages": st["rows"]})
        if path.endswith("/result"):
            return j({"status": "done" if st["rows"] else "idle", "line": ""})
        return j({"ok": True})
    pg.route("**/api/vocal/**", vocal)
    pg.route("**/api/conversations/vc_1/**", conv)


def open_vocal(pg, base):
    pg.goto(base + "/console/")
    pg.wait_for_selector(".sn[data-v='vocal']", state="attached")
    pg.evaluate("document.querySelector(\".sn[data-v='vocal']\").click()")
    pg.wait_for_selector("#hvRoot .hv-chat")


def page_to(pg, name):
    if pg.locator("#hvRoot .hv-top .hv-menu").is_visible():                       # phone width: the sidebar is a drawer
        pg.locator("#hvRoot .hv-top .hv-menu").click()
        pg.wait_for_function("() => document.querySelector('#hvRoot .hv-side').getBoundingClientRect().left > -1")
        pg.wait_for_timeout(320)
    pg.locator(f"#hvRoot .hv-nv[data-p='{name}']").click()
    pg.wait_for_function("p => document.querySelector('#hvRoot .hv-nv[aria-current=page]')?.dataset.p === p", arg=name)
    pg.wait_for_timeout(350)


def test_every_page_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs = []
    st = {"calls": [], "tts": [], "sent": [], "rows": [], "items": []}
    pg.on("pageerror", lambda e: errs.append(str(getattr(e, "stack", "") or e)[:400]))
    pg.route("**/api/console/config", lambda r: r.fulfill(json=CONFIG))
    install(pg, st)
    open_vocal(pg, base)
    assert pg.locator("#hvRoot .hv-nv[data-p]").count() == 13                     # Make 5, Voices 2, Tools 3, Assets 3
    assert "4,820 credits left" in pg.locator("#hvSide").text_content()
    for width in (1280, 390):
        pg.set_viewport_size({"width": width, "height": 900})
        for name, said in PAGES:
            page_to(pg, name)
            if name == "dub":
                pg.wait_for_function("() => document.querySelector('#hvView').textContent.includes('product-tour.mp4')")
            text = pg.locator("#hvView").text_content()
            assert said in text, (width, name)
            assert pg.locator("#hvRoot h1").count() == 1, (width, name)
            assert pg.evaluate(NO_SIDEWAYS), (width, name, pg.evaluate(WIDE))
            assert pg.evaluate(UNSAID) == [], (width, name)
            assert pg.evaluate(STACKED), (width, name)                               # a side panel never sits on top of the page
            if os.environ.get("CONSOLE_SHOTS"):
                pg.wait_for_timeout(700)
                pg.screenshot(path=f"{os.environ['CONSOLE_SHOTS']}/hv-{width}-{name}.png")
    pg.set_viewport_size({"width": 1280, "height": 900})
    assert pg.locator("#hvRoot b b, #hvRoot i i").count() == 0                     # her titles are text, never markup

    # Speech: a tone at the cursor, a language from the console menu, the premium engine says why it is off (no key name)
    page_to(pg, "speech")
    pg.locator("#hvText").fill("Karibu Mkate Bora! ")
    pg.locator("#hvText").evaluate("t => { t.focus(); t.selectionStart = t.selectionEnd = t.value.length; }")
    pg.locator("#hvRoot [data-a='tonemenu']").click()
    pg.locator(".hmenu .mi", has_text="Laughs").click()
    assert pg.locator("#hvText").input_value() == "Karibu Mkate Bora! [laughs] "
    pg.locator("#hvRoot [data-a='spmore']").click()
    pg.locator("#hvRoot [data-a='picklang']").click()
    pg.locator(".hmenu .msearch input").fill("swa")
    assert pg.locator(".hmenu .mi:visible").count() == 1
    pg.locator(".hmenu .mi:visible", has_text="Swahili").click()
    pg.locator("#hvRoot [data-a='picklang']").click()
    pg.locator(".hmenu .msearch input").fill("quechua")
    qu = pg.locator(".hmenu .mi:visible", has_text="Quechua")
    assert qu.get_attribute("aria-disabled") == "true" and "No engine yet" in pg.locator(".hmenu").text_content()
    pg.keyboard.press("Escape")
    pg.locator("#hvRoot [data-a='pickengine']").click()
    el = pg.locator(".hmenu .mi", has_text="ElevenLabs")
    assert el.get_attribute("aria-disabled") == "true" and "not connected" in el.text_content() and "API_KEY" not in el.text_content()
    pg.keyboard.press("Escape")
    pg.locator("#hvRoot [data-a='pickfmt']").click()
    pg.locator(".hmenu .mi", has_text="MP3").click()
    pg.wait_for_function("() => /credits/.test(document.querySelector('[data-qbtn=speech]').textContent)")
    assert "22 credits" in pg.locator("[data-qbtn='speech']").text_content()          # the price before the tap
    pg.locator("[data-qbtn='speech']").click()
    pg.wait_for_selector("#hvTakes .hv-takecard")
    assert st["tts"] == [{"text": "Karibu Mkate Bora! [laughs] ", "voice": "v_amani", "lang": "sw", "style": "warm", "speed": 1, "expressive": 0.5,
                          "takes": 2, "engine": "auto", "format": "mp3", "rules": True}]
    assert pg.locator("#hvTakes .hv-takecard").count() == 2
    pg.locator("#hvTakes [data-a='keep']").first.click()
    assert "Kept" in pg.locator("#hvTakes .hv-takecard").first.text_content()

    # Voices: a premium voice whose engine is not set up cannot be heard or used
    page_to(pg, "voices")
    th = pg.locator("#hvRoot .hv-vrow", has_text="Thandi")
    assert th.locator("[data-a='hear']").is_disabled() and th.locator("[data-a='usev']").is_disabled()
    th.locator("[data-a='vsel']").click()
    assert "ElevenLabs is not connected" in pg.locator("#hvRoot .hv-vdetail").text_content() and "API_KEY" not in pg.locator("#hvView").text_content()
    # Dubbing: their own voices is premium, disabled with the reason
    page_to(pg, "dub")
    own = pg.locator("#hvRoot [data-m='UI.dubNew.mode'][data-val='own']")
    assert own.is_disabled() and own.get_attribute("aria-describedby")
    pg.locator("#hvRoot [data-a='dubopen']").click()
    pg.wait_for_function("() => document.querySelector('#hvView').textContent.includes('この画面で注文を確認できます。')")
    assert pg.locator("#hvRoot h1").count() == 1
    # Your voice: the consent line in her language, with its English meaning
    page_to(pg, "mine")
    pg.wait_for_function("() => document.querySelector('#hvView .hv-consent')")
    assert "I agree that Hoola makes my voice." in pg.locator("#hvView").text_content()
    assert pg.locator("#hvCOk").get_attribute("required") is not None

    # The Vocal chat: her words go with the settings note, her bubble shows only her words, the takes land in the chat
    page_to(pg, "chat")
    pg.locator("#hvRoot [data-a='setopen']").click()
    pg.locator("#hvSetp [data-m='S.takes'][data-val='2']").click()
    assert "Swahili" in pg.locator("#hvSum").text_content()
    pg.locator("#hvSetp [data-a='setdone']").click()
    pg.locator("#hvAsk").fill("Read this welcome for my bakery, warm and a little slow.")
    pg.locator("#hvRoot [data-qbtn='chat']").click()
    pg.wait_for_function("() => document.querySelectorAll('#hvThread [data-vset] .hv-take').length === 2", timeout=15000)
    assert len(st["sent"]) == 1
    sent = st["sent"][0]["text"]
    assert sent.startswith("Read this welcome for my bakery, warm and a little slow.\n\n[Vocal settings: make speech; language sw; voice v_amani; style warm; speed 1; takes 2; engine auto]")
    bubbles = pg.locator("#hvThread .hck-bub").all_text_contents()
    assert bubbles == ["Read this welcome for my bakery, warm and a little slow."]
    assert "Vocal settings" not in pg.locator("#hvThread").text_content()
    pg.wait_for_function("() => document.querySelector('#hvThread .hck-txt')")
    assert pg.evaluate("() => !!(document.querySelector('#hvThread .hck-bub').compareDocumentPosition([...document.querySelectorAll('#hvThread .hck-txt')].pop()) & Node.DOCUMENT_POSITION_FOLLOWING)")
    assert pg.locator("#hvRoot h1").count() == 1
    pg.wait_for_function("() => document.querySelector('#hvThread').textContent.includes('two takes')")
    if os.environ.get("CONSOLE_SHOTS"):
        pg.wait_for_timeout(700)
        pg.screenshot(path=f"{os.environ['CONSOLE_SHOTS']}/hv-chat-takes.png")
        page_to(pg, "speech")
        pg.screenshot(path=f"{os.environ['CONSOLE_SHOTS']}/hv-speech-takes.png")
        pg.evaluate("document.documentElement.setAttribute('data-theme','dark')")
        page_to(pg, "voices")
        pg.screenshot(path=f"{os.environ['CONSOLE_SHOTS']}/hv-voices-dark.png")
        pg.evaluate("document.documentElement.removeAttribute('data-theme')")
        page_to(pg, "chat")
    pg.locator("#hvRoot .hv-nv[data-a='back']").click()
    pg.wait_for_function("() => document.querySelector('#hvRoot').hidden === true")
    assert not errs, errs
    ctx.close()
