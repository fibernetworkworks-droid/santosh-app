"""v0.787 HOOLA VOCAL - the voice studio on Hoola's own engines. The engines are faked here (the sandbox has no key
and no GPU); what is tested is everything Hoola itself decides: consent, her pronunciation rules, cutting long words,
joining, history, the honest "not connected" switchboard, and that nobody reaches another tenant's sound."""
import asyncio
import io
import json
import pathlib
import wave

import pytest

from app.vocal import service as V
from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

ROOT = pathlib.Path(__file__).resolve().parents[2]


def tone(seconds=0.2, rate=24000):
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(b"\x01\x00" * int(rate * seconds))
    return b.getvalue()


@pytest.fixture
def vocal(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app.create import service as CS
    from app.interactive import lab
    said = []

    async def voice(text, voice_name="", language="Hindi", style="friendly", speed=1.0, tenant=""):
        said.append(("hoola", voice_name, language, text))
        return {"bytes": tone(), "ext": ".wav", "voice": voice_name, "seconds": 0.2}

    def labvoice(text, *, lang="hi", model="chatterbox", ref_audio=None, ref_text="", description=""):
        said.append((model, bool(ref_audio), description, text))
        return tone(rate=22050)

    monkeypatch.setattr(CS, "voice", voice)
    monkeypatch.setattr(CS, "ready", lambda: {"voice": True, "song": False, "dub": False})
    monkeypatch.setattr(lab, "voice", labvoice)
    monkeypatch.setattr(lab, "configured", lambda: True)
    return said


def run(c):
    return asyncio.run(c)


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.912.0"
    assert "0.912.0+911" in (ROOT / "pubspec.yaml").read_text()


def test_speech_is_kept_with_her_rules_applied_by_code(vocal):
    V.rule_add("t1", "Akola", "Uh-ko-laa")
    V.rule_add("t1", "FNW", "F N W", lang="en")                       # another language's rule must not fire
    r = run(V.tts("t1", "Akola mein FNW ki dukaan. akola aaiye!", voice="hv_Kore", lang="hi"))
    assert r["kind"] == "tts" and r["applied"] == 2 and r["chars"] == 38 and r["seconds"] > 0
    assert vocal[-1][3] == "Uh-ko-laa mein FNW ki dukaan. Uh-ko-laa aaiye!"      # whole words, any case, only her language
    assert r["text"].startswith("Akola")                              # history keeps HER words, not the respelling
    f, h = V.audio_file("t1", r["id"])
    assert f.is_file() and h["voice_name"] == "Kore"
    with pytest.raises(V.VocalError):
        V.audio_file("t2", r["id"])                                   # another tenant cannot fetch it
    with pytest.raises(V.VocalError):
        V.audio_file("t1", "../../etc/passwd")


def test_long_words_are_cut_at_sentence_ends_never_rewritten(vocal):
    text = " ".join(f"Yeh vaakya number {i} hai." for i in range(400))
    parts = V.pieces(text, 4800)
    assert len(parts) > 1 and all(len(p) <= 4800 for p in parts) and " ".join(parts) == text
    assert all(p.endswith(".") for p in parts)
    assert V.pieces("x" * 1300, 500) and "".join(V.pieces("x" * 1300, 500)) == "x" * 1300
    r = run(V.tts("t1", text, voice="hv_Puck"))
    assert len([s for s in vocal if s[0] == "hoola"]) == len(parts) and r["seconds"] > 0.2 * len(parts)
    with pytest.raises(V.VocalError, match="Studio"):
        run(V.tts("t1", "a" * (V.MAX_TOTAL + 1)))


def test_a_cloned_voice_needs_her_yes_and_a_real_recording(vocal, tmp_path):
    rec = tmp_path / "me.wav"; rec.write_bytes(tone(1.0))
    with pytest.raises(V.VocalError, match="agreed"):
        V.voice_clone("t1", "Me", str(rec), False)
    with pytest.raises(V.VocalError, match="agreed"):
        V.voice_clone("t1", "Me", str(rec), "yes")                    # only a real True counts
    assert not V._load("t1")["voices"] and not list((V._home("t1") / "samples").iterdir())   # nothing stored without it
    fake = tmp_path / "x.wav"; fake.write_bytes(b"<html>not sound</html>")
    with pytest.raises(V.VocalError, match="not a sound"):
        V.voice_clone("t1", "Me", str(fake), True)
    v = V.voice_clone("t1", "Me", str(rec), True)
    assert v["kind"] == "clone" and v["consent_at"]
    run(V.tts("t1", "Namaste.", voice=v["id"]))
    assert vocal[-1][0] == "chatterbox" and vocal[-1][1] is True      # her recording rode to the engine
    V.voice_remove("t1", v["id"])
    assert not list((V._home("t1") / "samples").iterdir())            # the recording goes with the voice


def test_a_described_voice_never_copies_a_named_person(vocal):
    with pytest.raises(V.VocalError, match="named people"):
        V.voice_design("t1", "Star", "Make it sound exactly like a famous film actor")
    v = V.voice_design("t1", "Dadi", "An older woman, warm and slow, telling a bedtime story", gender="female")
    run(V.tts("t1", "Ek tha raja.", voice=v["id"]))
    assert vocal[-1][0] == "indic_parler" and "older woman" in vocal[-1][2]


def test_dialogue_reads_each_speaker_in_her_chosen_voice(vocal):
    lines = [{"speaker": "Asha", "text": "Kitne ka hai?"}, {"speaker": "Ravi", "text": "Sau rupaye."}, {"speaker": "Asha", "text": "Theek."}]
    with pytest.raises(V.VocalError, match="voice for Ravi"):
        run(V.dialogue("t1", lines, {"Asha": "hv_Kore"}))
    r = run(V.dialogue("t1", lines, {"Asha": "hv_Kore", "Ravi": "hv_Puck"}))
    assert r["lines"] == 3 and [s[1] for s in vocal] == ["Kore", "Puck", "Kore"]
    assert r["seconds"] >= 0.6 + 2 * V.LINE_GAP_S - 0.1                # three readings + the quiet between speakers
    mine = V.voice_design("t1", "Dadi", "An older woman, warm and slow, kind")
    with pytest.raises(V.VocalError, match="two kinds"):               # 24 kHz and 22 kHz cannot be joined - refused, not garbled
        run(V.dialogue("t1", lines, {"Asha": "hv_Kore", "Ravi": mine["id"]}))


def test_a_reading_exports_only_when_every_chapter_is_read(vocal):
    p = V.project_save("t1", title="Kahani", voice="hv_Kore", chapters=[{"title": "Ek", "text": "Pehla hissa."}, {"title": "Do", "text": "Doosra hissa."}])
    with pytest.raises(V.VocalError, match="Ek, Do"):
        V.project_export("t1", p["id"])
    run(V.chapter_make("t1", p["id"], 0)); run(V.chapter_make("t1", p["id"], 1))
    book = V.project_export("t1", p["id"])
    assert book["kind"] == "book" and book["seconds"] > 0.4
    p2 = V.project_save("t1", pid=p["id"], title="Kahani", chapters=[{"title": "Ek", "text": "Pehla hissa."}, {"title": "Do", "text": "Badla hua."}])
    assert p2["chapters"][0].get("audio") and not p2["chapters"][1].get("audio")     # changed words lose their old reading


def test_effects_cleanup_history_and_usage(vocal, tmp_path):
    s = V.sfx("t1", V.sfx_presets()[0], 7)
    assert s["kind"] == "sfx" and V.sfx("t1", V.sfx_presets()[0], 7)["size"] == s["size"]    # same preset + seed = same sound
    with pytest.raises(V.VocalError):
        V.sfx("t1", "explosion; rm -rf /")
    run(V.tts("t1", "Namaste duniya.", voice="hv_Kore"))
    o = V.overview("t1")
    assert o["usage"]["made"] == 3 and o["usage"]["characters"] == 15 and o["usage"]["by_kind"] == {"sfx": 2, "tts": 1}
    V.history_remove("t1", s["id"])
    assert len(V._load("t1")["history"]) == 2 and not (V._home("t1") / "audio" / f"{s['id']}.wav").exists()
    json.dumps(o)                                                     # the overview is plain data


def test_what_is_not_connected_is_reported_not_faked(vocal, monkeypatch):
    from app.create import service as CS
    from app.interactive import lab
    c = V.connected()
    for never in ("changer", "isolate", "sfx_text", "pro_clone", "audio_native", "api", "watermark", "rupee_meter"):
        assert c[never] is False, never
    monkeypatch.setattr(CS, "ready", lambda: {"voice": False, "song": False, "dub": False})
    monkeypatch.setattr(lab, "configured", lambda: False)
    c = V.connected()
    assert not c["tts"] and not c["clone"] and not c["design"] and c["sfx_presets"]
    assert V.overview("t1")["voices"] == []                           # no engine = no voice offered
    with pytest.raises(V.VocalError, match="GEMINI_API_KEY"):
        run(V.tts("t1", "Namaste.", voice="hv_Kore"))
    v = V.voice_design("t1", "Dadi", "An older woman, warm and slow, kind")
    with pytest.raises(V.VocalError, match="not connected"):
        run(V.tts("t1", "Namaste.", voice=v["id"]))


def test_no_code_from_the_agpl_project_and_the_routes_are_mounted():
    src = (ROOT / "server/app/vocal/service.py").read_text() + (ROOT / "server/app/vocal/api.py").read_text()
    for word in ("voicestudio", "omnivoice", "VoiceStudio"):
        assert word not in src
    main = (ROOT / "server/app/main.py").read_text()
    assert "_vocal_router(require_key, current_tenant)" in main and '"vocal": bool(getattr(st, "vocal_page", False))' in main


OV = {"voices": [{"id": "hv_Kore", "name": "Kore", "gender": "female", "tone": "Confident", "kind": "hoola", "ready": True},
                 {"id": "hv_Puck", "name": "Puck", "gender": "male", "tone": "Upbeat", "kind": "hoola", "ready": True},
                 {"id": "mv_1", "name": "<i>Mine</i>", "kind": "clone", "tone": "Your recording", "gender": "", "ready": False, "consent_at": "2026-11-11T08:00:00+00:00"}],
      "hoola_voices": 2, "my_voices": 1, "rules": [{"id": "pr_1", "word": "Akola", "say": "Uh-ko-laa", "lang": ""}],
      "history": [{"id": "vo_aaaaaaaaaaaa", "kind": "tts", "title": "<b>Namaste</b> duniya", "voice_name": "Kore", "seconds": 4, "made": "2026-11-11T09:00:00+00:00", "ext": "wav"}],
      "projects": [{"id": "vp_1", "title": "Kahani", "lang": "hi", "voice": "hv_Kore", "made": "2026-11-11T09:00:00+00:00",
                    "chapters": [{"title": "Ek", "text": "Pehla.", "audio": "vo_aaaaaaaaaaaa", "seconds": 4}, {"title": "Do", "text": "Doosra."}]}],
      "usage": {"month": "2026-11", "made": 1, "characters": 15, "minutes": 0.1, "by_kind": {"tts": 1}, "kept": 1, "kept_max": 200},
      "langs": {"hi": "Hindi", "en": "English"}, "styles": {"friendly": "Friendly", "story": "Storyteller"}, "sfx": ["coin", "jump"],
      "limits": {"characters": 40000, "lines": 40, "voices": 30, "sample_mb": 2, "history": 200},
      "status": {"engines": {"speech": True, "lab": False, "ffmpeg": True, "music": False, "dub": False, "stt": False},
                 "connected": {"tts": True, "library": True, "dialogue": True, "studio": True, "clone": False, "design": False, "sfx_presets": True,
                               "sfx_text": False, "cleanup": True, "isolate": False, "changer": False, "stt": False, "music": False, "dub": False}}}


def test_the_page_in_a_real_browser(arena_server):  # noqa: F811
    """Hoola Vocal is its own full page with its own sidebar: every one of the twelve pages opens with no script error
    and no sideways scroll, says its title once, never runs her text as HTML, SAYS what is not connected, and a
    typed line is sent to the server with the voice and language she chose."""
    base, browser, key = arena_server
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs, sent = [], []
    pg.on("pageerror", lambda e: errs.append(str(getattr(e, "stack", "") or e)[:400]))
    pg.route("**/api/console/config", lambda r: r.fulfill(json={"app": "Hoola", "v2": True, "stream": True, "sessions": True, "panel": True,
                                                                   "projects": True, "human": True, "interactive": True, "vocal": True}))
    pg.route("**/api/vocal/overview", lambda r: r.fulfill(json=OV))
    pg.route("**/api/vocal/audio**", lambda r: r.fulfill(body=b"RIFF", content_type="audio/wav"))

    def tts(r):
        sent.append(r.request.post_data_json)
        r.fulfill(json={**OV["history"][0], "id": "vo_bbbbbbbbbbbb"})
    pg.route("**/api/vocal/tts", tts)
    pg.goto(base + "/console/")
    pg.wait_for_selector(".sn[data-v='vocal']")
    pg.locator(".sn[data-v='vocal']").click()
    pg.wait_for_selector("#hvRoot .hi-hero")
    assert pg.locator("#hvRoot .hi-rb[data-p]").count() == 12
    assert pg.evaluate("getComputedStyle(document.querySelector('#hvRoot .hi-rail')).display") == "flex"       # the shared design system reaches this page
    home = pg.locator("#hvRoot").text_content()
    assert "What should Hoola say?" in home and "<b>Namaste</b> duniya" in home and "GPU voice engine" in home
    assert pg.locator("#hvRoot b b").count() == 0                                   # her title is text, never markup
    import os
    shots = os.environ.get("CONSOLE_SHOTS")
    for page, said in [("voices", "Kore"), ("tts", "Generate speech"), ("dialogue", "Cast"), ("studio", "Kahani"), ("changer", "Not connected on this server yet"),
                       ("sfx", "coin"), ("isolate", "Lift a voice out of music"), ("more", "Speech to text"), ("dict", "Uh-ko-laa"), ("history", "duniya"),
                       ("settings", "Characters spoken")]:
        pg.locator(f"#hvRoot .hi-rb[data-p='{page}']").click()
        pg.wait_for_function("p => document.querySelector('#hvRoot .hi-rb[aria-current=page]')?.dataset.p === p", arg=page)
        assert said in pg.locator("#hvView").text_content(), page
        assert pg.locator("#hvRoot h1").count() == 1, page
        assert pg.evaluate("document.querySelector('#hvView').scrollWidth <= document.querySelector('#hvView').clientWidth + 1"), page
        assert pg.evaluate("[...document.querySelectorAll('#hvRoot select')].every(s => getComputedStyle(s).appearance === 'none')"), page
        if shots:
            pg.wait_for_timeout(1000)
            pg.screenshot(path=f"{shots}/hv-{page}.png")
    pg.locator("#hvRoot .hi-rb[data-p='voices']").click()
    pg.locator("#hvRoot .hi-tab", has_text="My voices").click()
    assert pg.evaluate("document.querySelector('#hvRoot').hidden") is False            # a tab click stays on the page (the console owns data-v)
    v = pg.locator("#hvView").text_content()
    assert "<i>Mine</i>" in v and "Consent given" in v and "needs the GPU voice engine" in v
    assert pg.locator("#hvRoot .hv-voice [data-a='usev']").first.is_disabled()      # a voice that cannot speak here cannot be chosen
    pg.locator("#hvRoot .hi-tab", has_text="Clone a voice").click()
    assert pg.locator("#hvCOk").get_attribute("required") is not None               # the yes is a required field
    pg.locator("#hvRoot .hi-rb[data-p='studio']").click()
    pg.locator("#hvRoot .hi-av", has_text="Kahani").click()
    pg.wait_for_selector("#hvPTitle")
    assert pg.locator("#hvRoot [data-a='export']").is_disabled()                    # one chapter is not read yet
    pg.locator("#hvRoot .hi-rb[data-p='tts']").click()
    pg.locator("#hvText").fill("Namaste Akola.")
    assert "14 / 40,000" in pg.locator("#hvCount").text_content()
    pg.locator("#hvVoice").select_option("hv_Puck")
    pg.locator("#hvRoot form[data-f='tts'] button.hi-btn").click()
    pg.wait_for_function("() => !document.querySelector('#hvBar').hidden")           # the result opens in the player bar
    assert sent == [{"text": "Namaste Akola.", "voice": "hv_Puck", "lang": "hi", "style": "friendly", "speed": 1, "rules": True}]
    if shots:
        pg.wait_for_timeout(600)
        pg.screenshot(path=f"{shots}/hv-tts-done.png")
        pg.locator("#hvRoot .hi-rb[data-p='home']").click()
        pg.wait_for_timeout(1000)
        pg.screenshot(path=f"{shots}/hv-home.png")
        pg.evaluate("document.documentElement.setAttribute('data-theme','dark')")
        pg.locator("#hvRoot .hi-rb[data-p='voices']").click()
        pg.locator("#hvRoot .hi-tab", has_text="Library").click()
        pg.wait_for_timeout(1000)
        pg.screenshot(path=f"{shots}/hv-voices-dark.png")
        pg.evaluate("document.documentElement.removeAttribute('data-theme')")
    pg.locator("#hvRoot .hi-rb[data-a='back']").click()
    pg.wait_for_function("() => document.querySelector('#hvRoot').hidden === true")
    assert not errs, errs
    ctx.close()
