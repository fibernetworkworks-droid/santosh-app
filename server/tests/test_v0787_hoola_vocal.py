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
    assert APP_VERSION == "0.999.92"
    assert "0.999.92+1087" in (ROOT / "pubspec.yaml").read_text()


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
    parts = V.pieces(text, V.PIECE["gemini"])                         # v0.999.90: each engine has its own piece size
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
    for never in ("changer", "isolate", "sfx_text", "pro_clone", "audio_native", "api"):   # v0.999.90: the AI mark + the price meter exist now
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


def test_the_page_in_a_real_browser(arena_server):  # noqa: F811
    """Hoola Vocal is its own full page with its own sidebar. v0.999.90 rebuilt it to the global design (the Vocal chat
    home + 13 more pages; the full walk is tests/test_v0999_90_vocal_console.py). The intent kept here from v0.787:
    every page opens with no script error and no sideways scroll and says its title once, her text is never run as
    HTML, what is not connected is SAID, and a typed line is sent with the voice and language she chose."""
    from tests.test_v0999_90_vocal_console import CONFIG, PAGES, install, open_vocal, page_to
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
    assert pg.locator("#hvRoot .hv-nv[data-p]").count() == 14
    for page, said in PAGES:
        page_to(pg, page)
        if page == "dub":
            pg.wait_for_function("() => document.querySelector('#hvView').textContent.includes('product-tour.mp4')")
        assert said in pg.locator("#hvView").text_content(), page
        assert pg.locator("#hvRoot h1").count() == 1, page
        assert pg.evaluate("document.querySelector('#hvView').scrollWidth <= document.querySelector('#hvView').clientWidth + 1"), page
    page_to(pg, "history")
    assert "<b>Karibu</b> Mkate" in pg.locator("#hvView").text_content() and pg.locator("#hvRoot b b").count() == 0   # her title is text
    page_to(pg, "changer")
    assert "ElevenLabs is not connected" in pg.locator("#hvView").text_content()       # not connected = said, never faked
    page_to(pg, "voices")
    pg.locator("#hvRoot .hi-tab", has_text="Your voices").click()
    assert pg.evaluate("document.querySelector('#hvRoot').hidden") is False            # a tab click stays on the page (the console owns data-v)
    assert "<i>Mine</i>" in pg.locator("#hvView").text_content()
    pg.locator("#hvRoot .hv-vc [data-a='usev']").first.click()                          # Use = that voice on the Speech page
    pg.wait_for_selector("#hvText")
    pg.locator("#hvText").fill("Namaste Akola.")
    assert "14 / 100,000" in pg.locator("#hvCount").text_content()
    pg.locator("#hvRoot [data-a='picklang']").click()
    pg.locator("#hvPopQ").fill("japanese")
    pg.locator(".hv-pop [data-val='ja']").click()
    pg.locator("[data-qbtn='speech']").click()
    pg.wait_for_function("() => !document.querySelector('#hvBar').hidden")              # the first take opens in the player bar
    assert len(st["tts"]) == 1 and st["tts"][0]["voice"] == "v_mine" and st["tts"][0]["lang"] == "ja" and st["tts"][0]["text"] == "Namaste Akola."
    pg.locator("#hvRoot .hv-nv[data-a='back']").click()
    pg.wait_for_function("() => document.querySelector('#hvRoot').hidden === true")
    assert not errs, errs
    ctx.close()
