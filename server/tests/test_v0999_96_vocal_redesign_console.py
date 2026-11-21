"""v0.999.96 HOOLA VOCAL REDESIGN - the console page (static/console/vocal.js + vocal2.css) walked in a real Chromium.

The contract is docs/HOOLA_VOCAL_REDESIGN.md (sections 1 and 4). The server is mocked route by route with
contract-shaped JSON (the engines are fakes), so this checks the PAGE at 1440 light, 1440 dark and 390 light:
the Create Studio frame (248 px sidebar with the real Hoola mark, four groups, the credits card, a 52 px top bar with
the crumb), every sidebar page opens with no script error and nothing wider than the window, the Vocal chat's composer
docked at the bottom with its settings sheet above the box, every dropdown is the console menu (no native select, no
visible file input), no page names a server key, the download menu names the formats the overview lists, the 0-credit
state explains itself with a link, the voice changer records in the page, and Create Studio -> Voice shows the Vocal
Speech page. Screenshots go to CONSOLE_SHOTS when it is set."""
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
JS = open(os.path.join(os.path.dirname(__file__), "..", "app", "static", "console", "vocal.js"), encoding="utf-8").read()
CSS = open(os.path.join(os.path.dirname(__file__), "..", "app", "static", "console", "vocal2.css"), encoding="utf-8").read()
V2CSS = open(os.path.join(os.path.dirname(__file__), "..", "app", "static", "console", "v2.css"), encoding="utf-8").read()
STUDIO = open(os.path.join(os.path.dirname(__file__), "..", "app", "static", "console", "studio.js"), encoding="utf-8").read()


def overview(broke=False):
    return {
        "voices": [
            {"id": "v_meera", "name": "Meera", "gender": "female", "age": "middle", "tone": "Warm", "accent": "India", "langs": ["hi", "en"],
             "use": "Narration", "engine": "gemini", "tier": "standard", "kind": "hoola", "ready": True},
            {"id": "v_lucia", "name": "Lucía", "gender": "female", "age": "young", "tone": "Bright", "accent": "Mexico", "langs": ["es", "en"],
             "use": "Ads", "engine": "gemini", "tier": "standard", "kind": "hoola", "ready": True},
            {"id": "v_thandi", "name": "Thandi", "gender": "female", "age": "middle", "tone": "Rich", "accent": "South Africa", "langs": ["zu"],
             "use": "Conversation", "engine": "eleven", "tier": "premium", "kind": "hoola", "ready": True},
            {"id": "v_mine", "name": "<i>My voice</i>", "tone": "Your recording", "langs": ["en"], "engine": "eleven", "kind": "clone", "ready": True, "made": ISO(-86400)},
            {"id": "v_old", "name": "Old storyteller", "tone": "Described", "langs": ["en"], "engine": "gemini", "kind": "design", "ready": True}],
        "langs": [
            {"code": "en", "name": "English", "native": "English", "region": "Europe", "speech": "yes", "clone": "yes", "dialogue": "yes", "dub": "yes", "voices": 30, "quality": "excellent"},
            {"code": "hi", "name": "Hindi", "native": "हिन्दी", "region": "Asia", "speech": "yes", "clone": "yes", "dialogue": "yes", "dub": "yes", "voices": 24, "quality": "excellent"},
            {"code": "sw", "name": "Swahili", "native": "Kiswahili", "region": "Africa", "speech": "yes", "clone": "yes", "dialogue": "yes", "dub": "yes", "voices": 9, "quality": "good"},
            {"code": "es", "name": "Spanish", "native": "Español", "region": "Americas", "speech": "yes", "clone": "yes", "dialogue": "yes", "dub": "yes", "voices": 38, "quality": "excellent"},
            {"code": "zu", "name": "Zulu", "native": "isiZulu", "region": "Africa", "speech": "premium", "clone": "premium", "dialogue": "premium", "dub": "yes", "voices": 4, "quality": "fair"},
            {"code": "qu", "name": "Quechua", "native": "Runa Simi", "region": "Americas", "speech": "none", "clone": "none", "dialogue": "none", "dub": "none", "voices": 0, "quality": "none"}],
        "styles": {"warm": "Warm", "calm": "Calm", "news": "News reader", "story": "Storyteller"},
        "feelings": ["warm", "whispers", "laughs", "pause"],
        "engines": [{"id": "gemini", "name": "Gemini voice", "does": "Speech, dialogue, readings", "langs": "130 languages", "state": "ready", "why": ""},
                    {"id": "eleven", "name": "ElevenLabs (premium)", "does": "Shared voices, changer, effects", "langs": "70 languages", "state": "ready", "why": ""},
                    {"id": "lab", "name": "Hoola GPU lab", "does": "Your own voices", "langs": "", "state": "off", "why": "Needs LAB_API_KEY in the server's .env."},
                    {"id": "server", "name": "Hoola server", "does": "Clean-up, formats, subtitles", "langs": "Any language", "state": "ready", "why": ""}],
        "prices": [{"job": "Speech, 1 minute", "engine": "gemini", "credits": 2, "usd": 0.002}, {"job": "Dub in their own voices, 1 minute", "engine": "eleven", "credits": 34, "usd": 0.034}],
        "formats": [{"id": "mp3", "name": "MP3", "note": "Small, for sharing"}, {"id": "wav", "name": "WAV", "note": "Studio quality"},
                    {"id": "ogg", "name": "OGG", "note": "For WhatsApp"}, {"id": "m4a", "name": "M4A", "note": "For iPhone"}],
        "rules": [{"id": "pr_1", "word": "Mithas", "say": "Mi-thaas", "ipa": "mɪˈt̪ʰaːs", "lang": "hi"}],
        "rules_kept": ["A cloned voice needs the speaker's spoken yes.", "Every file carries an AI mark."],
        "history": [{"id": "vo_aaaaaaaaaaaa", "kind": "tts", "title": "<b>Diwali</b> offer · a very long title that must never collapse into nothing at phone width",
                     "voice_name": "Meera", "lang": "hi", "engine": "gemini", "seconds": 14, "made": ISO(-60), "ext": "mp3", "credits": 4},
                    {"id": "vo_bbbbbbbbbbbb", "kind": "dialogue", "title": "Shop podcast, episode 3", "voice_name": "Meera", "lang": "en", "seconds": 252, "made": ISO(-7200), "ext": "wav"}],
        "projects": [{"id": "vp_1", "title": "The Lighthouse Keeper", "lang": "en", "voice": "v_meera", "made": ISO(-7200),
                      "chapters": [{"title": "The keeper", "text": "The wind came first.", "audio": "vo_aaaaaaaaaaaa", "seconds": 4}, {"title": "The storm", "text": "Then the rain."}]}],
        "usage": {"month": "2026-11", "made": 2, "characters": 100000, "minutes": 4.4, "by_kind": {"tts": 1}, "kept": 2, "kept_max": 300,
                  "credits_used": 180, **({"credits_left": 0} if broke else {"credits_left": 4820})},
        "limits": {"characters": 100000, "lines": 40, "history": 300, "dub_langs_matched": 4, "dub_langs_own": 6, "dub_speakers": 6},
        "credits_page": "/console/?v=credits",
        "sfx": ["coin", "jump"],
        "status": {"engines": {}, "connected": {"clone": True, "design": True, "shared_library": True, "natural_dialogue": True, "dub_editor": True, "stream": False}},
    }


PAGES = [("chat", "Say anything, in any language"), ("speech", "Add a tone"), ("dialogue", "How it sounds"), ("studio", "The Lighthouse Keeper"),
         ("dub", "product-tour.mp4"), ("voices", "Meera"), ("mine", "Read this out loud"), ("changer", "Record here"), ("cleanup", "Take the voice out of music"),
         ("sfx", "Quick game sounds"), ("sounds", "Shop podcast, episode 3"), ("dict", "Mi-thaas"), ("settings", "What things cost")]

CHECKS = """() => {
  const R = document.querySelector('#hvRoot'), W = innerWidth, out = {};
  out.wide = [...R.querySelectorAll('*')].filter(e => { const r = e.getBoundingClientRect(); return e.getClientRects().length && r.width && r.right > W + 1
      && !e.closest('.hv-side') && getComputedStyle(e).position !== 'fixed'; }).slice(0, 6).map(e => e.tagName + '.' + e.className + ' ' + Math.round(e.getBoundingClientRect().right));
  out.sideways = document.documentElement.scrollWidth > W + 1 || R.scrollWidth > R.clientWidth + 1;
  out.h1 = R.querySelectorAll('h1').length;
  out.select = R.querySelectorAll('select').length;
  out.file = [...R.querySelectorAll('input[type=file]')].filter(i => i.getClientRects().length && i.getBoundingClientRect().width > 2).length;
  out.unsaid = [...R.querySelectorAll('#hvView :is(button,input,textarea):disabled')].filter(e => !e.closest('.hv-seg') || true).map(e => {
    const id = e.getAttribute('aria-describedby'), w = id && document.getElementById(id); return (w && w.textContent.trim()) || e.closest('[role=radiogroup],.hv-vrow,.hv-mv,.hv-snd,.hv-sample') ? null : e.outerHTML.slice(0, 140); }).filter(Boolean);
  out.text = R.textContent;
  return out; }"""


def install(pg, st):
    def vocal(route):
        req = route.request
        u = urlparse(req.url)
        path, qs = u.path[len("/api/vocal"):], parse_qs(u.query)
        body = req.post_data_json if req.method in ("POST", "PUT") and req.post_data else None
        st["calls"].append((req.method, path, body))
        j = lambda d, s=200: route.fulfill(status=s, content_type="application/json", body=json.dumps(d))  # noqa: E731
        if path == "/overview":
            return j(overview(st.get("broke")))
        if path in ("/audio", "/voice/preview", "/library/preview"):
            return route.fulfill(body=b"RIFF\x24\x00\x00\x00WAVEfmt ", content_type="audio/wav")
        if path == "/quote":
            n = 2 * int((body or {}).get("takes") or 1)
            return j({"credits": n, "usd": n / 1000, "engine": "gemini", "engine_name": "Gemini voice", "line": "nothing is spent until you tap"})
        if path == "/tts":
            st["tts"].append(body)
            return j({"items": [{"id": f"vo_t{i}", "kind": "tts", "title": "Diwali offer", "voice_name": "Meera", "lang": "hi", "engine": "gemini", "seconds": 14,
                                 "made": ISO(), "ext": body.get("format"), "take": "AB"[i], "job": "jb_x"} for i in range(int(body.get("takes") or 1))],
                      "lang": "hi", "lang_name": "Hindi", "engine": "gemini", "credits": 4})
        if path == "/change":
            st["change"].append(body)
            return j({"id": "vo_chg", "kind": "change", "title": "Changed", "seconds": 3, "made": ISO(), "ext": "mp3"})
        if path == "/chat":
            return j({"id": "vc_1", "title": "Vocal chat"})
        if path.startswith("/chat/vc_1/ok"):
            return j({"ok": True})
        if path == "/chat/vc_1/items":
            return j({"items": st["items"]})
        if path == "/chats":
            return j({"chats": [{"id": "vc_1", "title": "Vocal chat", "at": ISO()}]})
        if path == "/consent-line":
            return j({"line": "Main Hoola ko apni awaaz ki ek copy banane ki anumati deti hoon.", "english": "I let Hoola make a copy of my voice.", "lang": qs.get("lang", ["en"])[0]})
        if path == "/library":
            return j({"voices": [{"id": "sh_kavya", "owner": "u_1", "name": "Kavya", "line": "Bright · Hindi, Marathi · ads", "langs": ["hi"], "gender": "female",
                                  "age": "young", "accent": "India", "use": "Ads", "uses": 12400, "preview": "/api/vocal/library/preview?url=x"}], "more": False, "ready": True, "page": 1})
        if path == "/dubs":
            return j({"dubs": [{"id": "db_1", "status": "ready", "title": "product-tour.mp4", "langs": ["es"], "made": ISO(-60)}]})
        if path == "/dub/db_1":
            return j({"id": "db_1", "status": "ready", "mode": "matched", "source_lang": "en", "title": "product-tour.mp4",
                      "langs": [{"code": "es", "name": "Spanish", "status": "ready", "audio_id": "vo_dub", "video_id": "vo_dubv"}]})
        if path == "/dub/db_1/lines":
            return j({"lang": "es", "lang_name": "Spanish", "mode": "matched", "credits_redo": 1, "editable": True,
                      "lines": [{"n": 1, "start": 0, "end": 4, "speaker": "Priya", "src": "Every box is made by hand.", "dst": "Cada caja se hace a mano.", "too_long": False, "edited": False},
                                {"n": 2, "start": 9, "end": 11.1, "speaker": "Rahul", "src": "And no colours. Ever.", "dst": "Y nada de colorantes. Nunca jamás.", "too_long": True, "edited": False}]})
        return j({"detail": "not mocked"}, 404)

    def conv(route):
        req = route.request
        path = urlparse(req.url).path
        j = lambda d: route.fulfill(content_type="application/json", body=json.dumps(d))  # noqa: E731
        if path.endswith("/messages") and req.method == "POST":
            b = req.post_data_json
            st["sent"].append(b)
            st["rows"].append({"id": "m1", "role": "user", "text": b["text"], "at": ISO(1)})
            st["rows"].append({"id": "m2", "role": "assistant", "text": "Two takes in Hindi with Meera, warm and a little slower.", "at": ISO(3)})
            st["items"][:] = [{"id": f"vo_c{i}", "kind": "tts", "title": "Diwali offer", "voice_name": "Meera", "lang": "hi", "engine": "gemini",
                               "seconds": 14, "made": ISO(2), "ext": "mp3", "take": "AB"[i], "job": "jb_1", "chat": "vc_1", "credits": 2} for i in range(2)]
            return j({"ok": True})
        if path.endswith("/messages"):
            return j({"messages": st["rows"]})
        if path.endswith("/result"):
            return j({"status": "done" if st["rows"] else "idle", "line": ""})
        return j({"ok": True})

    def files(route):
        st["uploads"] += 1
        return route.fulfill(content_type="application/json", body=json.dumps({"file_id": f"f_up{st['uploads']}"}))
    pg.route("**/api/vocal/**", vocal)
    pg.route("**/api/conversations/vc_1/**", conv)
    pg.route("**/api/conversations/*/files", files)


FAKE_MIC = """navigator.mediaDevices && (navigator.mediaDevices.getUserMedia = async () => {
  const ac = new AudioContext(), o = ac.createOscillator(), d = ac.createMediaStreamDestination(); o.connect(d); o.start(); return d.stream; });"""


def open_vocal(pg, base):
    pg.goto(base + "/console/")
    pg.wait_for_selector(".sn[data-v='vocal']", state="attached")
    pg.evaluate("document.querySelector(\".sn[data-v='vocal']\").click()")      # the console's own sidebar is a drawer at phone width
    pg.wait_for_selector("#hvRoot .hv-chat")


def page_to(pg, name, narrow=False):
    if narrow:
        pg.locator("#hvRoot .hv-menu").click()
        pg.wait_for_function("() => document.querySelector('#hvRoot .hv-side').getBoundingClientRect().left > -1")
        pg.wait_for_timeout(320)
    pg.locator(f"#hvRoot .hv-nv[data-p='{name}']").click()
    pg.wait_for_function("p => document.querySelector('#hvRoot .hv-nv[aria-current=page]')?.dataset.p === p", arg=name)
    pg.wait_for_timeout(420)


def test_the_files_keep_the_contract():
    assert "<select" not in JS and "type=\"file\"" not in JS                 # every dropdown is the console menu; pickers are hidden
    assert "HoolaMenu.open" in JS and "HoolaMark.svg()" in JS
    assert not __import__("re").search(r"#[0-9A-Fa-f]{3,6}\b", CSS)          # tokens only, no hard-coded colours
    assert "ELEVENLABS_API_KEY" not in JS and "GEMINI_API_KEY" not in JS
    assert "#hvRoot .hv-two" not in V2CSS and ":is(#hiRoot,#hvRoot) .hi-rail" in V2CSS   # old Vocal rules gone, Interactive kept
    assert "HoolaVocal.mountSpeech(host" in STUDIO and "Make voice-over" not in STUDIO
    assert "'clock'" in JS and 'aria-label="Earlier chats"' in JS


def test_every_page_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    shots = os.environ.get("CONSOLE_SHOTS")
    st = {"calls": [], "tts": [], "sent": [], "rows": [], "items": [], "change": [], "uploads": 0}
    for scheme, width in (("light", 1440), ("dark", 1440), ("light", 390)):
        ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        ctx.add_init_script(FAKE_MIC)
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(getattr(e, "stack", "") or e)[:400]))
        pg.route("**/api/console/config", lambda r: r.fulfill(json=CONFIG))
        install(pg, st)
        open_vocal(pg, base)
        narrow = width < 720
        side = pg.locator("#hvRoot .hv-side")
        assert pg.locator("#hvRoot .hv-nv[data-p]").count() == 13      # Make 5, Voices 2, Tools 3, Assets 3
        assert pg.locator("#hvRoot .hv-mark svg.hm-svg").count() == 1          # the real Hoola mark
        assert [t.strip() for t in pg.locator("#hvRoot .hv-gh").all_text_contents()] == ["Make", "Voices", "Tools", "Assets"]
        assert "4,820 credits left" in side.text_content() and "180 of 5,000 used" in side.text_content()
        if not narrow:
            assert abs(side.bounding_box()["width"] - 248) < 1.5
            assert abs(pg.locator("#hvRoot .hv-top").bounding_box()["height"] - 52) < 1.5
            assert pg.locator("#hvRoot .hv-menu").is_hidden()
        else:
            assert pg.locator("#hvRoot .hv-menu").is_visible()
            assert side.bounding_box()["x"] + side.bounding_box()["width"] <= 1     # a drawer, off screen until opened
        for name, said in PAGES:
            page_to(pg, name, narrow)
            if name == "dub":
                pg.wait_for_function("() => document.querySelector('#hvView').textContent.includes('product-tour.mp4')")
            if name == "voices":
                pg.wait_for_function("() => document.querySelector('#hvView').textContent.includes('Meera')")
            c = pg.evaluate(CHECKS)
            assert said in c["text"], (width, name)
            assert c["h1"] == 1, (width, name)
            assert not c["sideways"] and not c["wide"], (width, scheme, name, c["wide"])
            assert c["select"] == 0 and c["file"] == 0, (width, name)
            assert c["unsaid"] == [], (width, name, c["unsaid"])
            assert "API_KEY" not in c["text"] and ".env" not in c["text"], (width, name)
            assert pg.locator("#hvRoot .hv-crumb").text_content().startswith("Vocal ·"), name
            if shots and name in ("speech", "voices", "dub") and width == 1440:
                pg.screenshot(path=f"{shots}/vocal-{scheme}-{width}-{name}.png")
            if shots and width == 390 and name in ("speech", "sounds"):
                pg.screenshot(path=f"{shots}/vocal-{scheme}-{width}-{name}.png", full_page=True)
        assert pg.locator("#hvRoot b b, #hvRoot i i").count() == 0                     # her titles are text, never markup

        # the Vocal chat: the composer docked at the bottom, the settings sheet above the box, the settings note on send
        page_to(pg, "chat", narrow)
        chat = pg.locator("#hvRoot .hv-chat").bounding_box()
        comp = pg.locator("#hvRoot .hv-comp").bounding_box()
        assert abs((chat["y"] + chat["height"]) - (comp["y"] + comp["height"])) < 2, (chat, comp)
        if not narrow:
            assert abs(chat["width"] - 560) < 2
            assert chat["y"] + chat["height"] >= 900 - 2 - (pg.locator("#hvBar").bounding_box() or {"height": 0})["height"]
        assert "credits" in pg.locator("#hvRoot [data-qline='chat']").text_content()
        send = pg.locator("#hvRoot [data-qbtn='chat']")
        assert "on" not in (send.get_attribute("class") or "")                       # grey until there are words
        pg.locator("#hvRoot [data-a='setopen']").click()
        sheet, box = pg.locator("#hvSetp").bounding_box(), pg.locator("#hvRoot .hv-box").bounding_box()
        assert sheet["y"] + sheet["height"] <= box["y"] + 1
        pg.locator("#hvSetp [data-m='S.takes'][data-val='2']").click()
        pg.locator("#hvSetp [data-a='picklang']").click()
        pg.locator(".hmenu .msearch input").fill("hin")
        pg.locator(".hmenu .mi:visible", has_text="Hindi").first.click()
        assert "Hindi" in pg.locator("#hvSum").text_content() and pg.locator("#hvSum").text_content().startswith("Speech ·")
        pg.locator("#hvSetp [data-a='setdone']").click()
        assert pg.locator("#hvSetp").is_hidden()
        if shots and width == 1440:
            pg.screenshot(path=f"{shots}/vocal-{scheme}-{width}-chat-empty.png")
        if not st["sent"]:
            pg.locator("#hvAsk").fill("Read our Diwali offer, a warm woman's voice, a little slow.")
            assert "on" in send.get_attribute("class")
            send.click()
            pg.wait_for_function("() => document.querySelectorAll('#hvThread [data-vset] .hv-take').length === 2", timeout=15000)
            sent = st["sent"][0]["text"]
            assert sent.startswith("Read our Diwali offer, a warm woman's voice, a little slow.\n\n[Vocal settings: make speech; language hi; voice v_meera;")
            assert pg.locator("#hvThread .hck-bub").all_text_contents() == ["Read our Diwali offer, a warm woman's voice, a little slow."]
            assert "Vocal settings" not in pg.locator("#hvThread").text_content()
            assert "Made by AI · marked in the file" in pg.locator("#hvThread").text_content()
        else:
            pg.wait_for_function("() => document.querySelectorAll('#hvThread [data-vset] .hv-take').length === 2", timeout=15000)
        comp = pg.locator("#hvRoot .hv-comp").bounding_box()
        chat = pg.locator("#hvRoot .hv-chat").bounding_box()
        assert abs((chat["y"] + chat["height"]) - (comp["y"] + comp["height"])) < 2         # still docked with a thread above it
        pg.locator("#hvThread [data-a='takemenu']").first.click()
        menu = pg.locator(".hmenu").text_content()
        assert all(x in menu for x in ("MP3", "Small, for sharing", "OGG", "For WhatsApp", "M4A", "For iPhone")) and "FLAC" not in menu
        pg.keyboard.press("Escape")
        assert pg.locator("#hvRoot [data-a='chats'] svg path").get_attribute("d").startswith("M12 4a8 8")   # Earlier chats = a clock
        if shots:
            pg.wait_for_timeout(600)
            pg.screenshot(path=f"{shots}/vocal-{scheme}-{width}-chat.png")
        assert not errs, (scheme, width, errs)
        ctx.close()


def test_speech_changer_credits_and_create_voice(arena_server):  # noqa: F811
    base, browser, key = arena_server
    shots = os.environ.get("CONSOLE_SHOTS")
    st = {"calls": [], "tts": [], "sent": [], "rows": [], "items": [], "change": [], "uploads": 0}
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    ctx.add_init_script(FAKE_MIC)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(getattr(e, "stack", "") or e)[:400]))
    pg.route("**/api/console/config", lambda r: r.fulfill(json=CONFIG))
    install(pg, st)
    open_vocal(pg, base)

    # Speech: a tone at the cursor, a language from the menu, a no-engine language greyed with its reason, the format menu
    page_to(pg, "speech")
    pg.locator("#hvText").fill("Is Diwali, Mithas par 20% chhoot. ")
    pg.locator("#hvText").evaluate("t => { t.focus(); t.selectionStart = t.selectionEnd = t.value.length; }")
    pg.locator("#hvRoot [data-a='tag'][data-val='warm']").click()
    assert pg.locator("#hvText").input_value().endswith("[warm] ")
    assert "1 word from your dictionary" in pg.locator("#hvCount").text_content()
    pg.locator("#hvRoot [data-a='picklang']").click()
    pg.locator(".hmenu .msearch input").fill("quechua")
    q = pg.locator(".hmenu .mi:visible", has_text="Quechua")
    assert q.get_attribute("aria-disabled") == "true" and "No engine yet" in q.text_content()
    pg.locator(".hmenu .msearch input").fill("hindi")
    pg.locator(".hmenu .mi:visible", has_text="Hindi").first.click()
    pg.locator("#hvRoot [data-a='pickfmt']").click()
    assert [t.split()[0] for t in pg.locator(".hmenu .mi .mt>span").all_text_contents()] == ["MP3", "WAV", "OGG", "M4A"]
    pg.locator(".hmenu .mi", has_text="OGG").click()
    pg.wait_for_function("() => /credits/.test(document.querySelector('[data-qbtn=speech]').textContent)")
    assert "Speak it · 4 credits" in pg.locator("#hvRoot [data-qbtn='speech']").text_content()
    assert "Hoola Auto picks Gemini voice for Hindi" in pg.locator("#hvRoot [data-qline='speech']").text_content()
    pg.locator("#hvRoot [data-qbtn='speech']").click()
    pg.wait_for_selector("#hvTakes .hv-takecard")
    b = st["tts"][-1]
    assert b["format"] == "ogg" and b["lang"] == "hi" and b["voice"] == "v_meera" and b["takes"] == 2 and b["text"].endswith("[warm] ")
    pg.locator("#hvTakes [data-a='dlmenu']").first.click()
    assert "For WhatsApp" in pg.locator(".hmenu").text_content()
    pg.keyboard.press("Escape")
    assert pg.locator("#hvRoot .hv-num").first.text_content()                       # numbers set in tabular figures
    page_to(pg, "settings")
    assert "100,000" in pg.locator("#hvView").text_content() and "LAB_API_KEY" not in pg.locator("#hvView").text_content()

    # the voice changer records in the page: MediaRecorder -> upload -> /change, into her own voice on ElevenLabs
    page_to(pg, "changer")
    pg.locator("#hvRoot [data-a='pickinto']").click()
    assert "My voice" in pg.locator(".hmenu").text_content()
    old = pg.locator(".hmenu .mi", has_text="Old storyteller")
    assert old.get_attribute("aria-disabled") == "true" and "needs a voice on ElevenLabs" in old.text_content()
    pg.locator(".hmenu .mi", has_text="My voice").click()
    pg.locator("#hvRoot [data-a='rec'][data-k='chg']").click()
    pg.wait_for_selector("#hvRoot [data-a='recstop'][data-k='chg']")
    pg.wait_for_timeout(1300)
    pg.locator("#hvRoot [data-a='recstop'][data-k='chg']").click()
    pg.wait_for_function("() => !document.querySelector('[data-qbtn=chg]').disabled", timeout=10000)
    assert "recording-chg." in pg.locator("#hvView").text_content()
    pg.locator("#hvRoot [data-qbtn='chg']").click()
    pg.wait_for_selector("#hvView .hv-takecard")
    assert st["change"] and st["change"][0]["file_id"].startswith("f_up") and st["change"][0]["voice"] == "v_mine"

    # the dubbing editor: lines from /lines, a too-long line warned, subtitles in the download list
    page_to(pg, "dub")
    pg.locator("#hvRoot [data-a='dubopen']").click()
    pg.wait_for_selector("#hvRoot textarea[data-dubline='2']")
    assert "Longer than the 2.1 s" in pg.locator("#hvView").text_content() and "Subtitles, VTT" in pg.locator("#hvView").text_content()
    assert pg.locator("#hvRoot .hv-crumb").text_content().replace("\xa0", " ").startswith("Vocal · Dubbing ·")
    if shots:
        pg.screenshot(path=f"{shots}/vocal-dub-editor.png")

    # 0 credits: the paid button explains and links to Credits
    st["broke"] = True
    open_vocal(pg, base)
    page_to(pg, "speech")
    btn = pg.locator("#hvRoot [data-qbtn='speech']")
    assert btn.is_disabled()
    why = pg.locator("#" + btn.get_attribute("aria-describedby"))
    assert "no credits left" in why.text_content() and why.locator("a").get_attribute("href") == "/console/?v=credits"
    page_to(pg, "chat")
    assert pg.locator("#hvRoot [data-qbtn='chat']").is_disabled() and "Get credits" in pg.locator("#hvRoot .hv-comp").text_content()
    st["broke"] = False

    # Create Studio -> Voice = the Vocal Speech page inside the Studio frame
    pg.locator("#hvRoot .hv-nv[data-a='back']").click()
    pg.wait_for_function("() => document.querySelector('#hvRoot').hidden === true")
    st["broke"] = False
    pg.goto(base + "/console/?v=creative")
    pg.wait_for_selector("#cstudio #snav [data-go]", timeout=20000)
    pg.evaluate("() => document.querySelector('#cstudio').shadowRoot.querySelector('#snav [data-go=\"voice\"]').click()")
    pg.wait_for_selector("#vocalhost #hvRoot .hv-panel [data-qbtn='speech']")
    host = pg.locator("#vocalhost #hvRoot")
    assert "Add a tone" in host.text_content() and "Takes" in host.text_content()
    assert "Make voice-over" not in pg.locator("#vocalhost").text_content()
    pg.wait_for_timeout(500)
    assert pg.evaluate("() => { const r = document.querySelector('#cstudio').shadowRoot.querySelector('#vocalhost').getBoundingClientRect(); return r.width > 600 && r.height > 500; }")
    assert "Create · Voice" in pg.evaluate("() => document.querySelector('#cstudio').shadowRoot.querySelector('#crumb').textContent")
    if shots:
        pg.screenshot(path=f"{shots}/vocal-create-voice.png")
    assert not errs, errs
    ctx.close()
