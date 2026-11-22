"""v0.999.90 HOOLA VOCAL GLOBAL - our own ElevenLabs for every user in the world (owner: "GO BUILD ALL" on the design
canvas claude.ai/artifact/Uf3iF3gBt1q8qq57gZJcue; contract docs/HOOLA_VOCAL_GLOBAL.md).

The engines are faked (no keys in the sandbox): what is tested is everything Hoola decides - which engine reads which
language, never another language, feelings turned into each engine's form, takes, consent, design options, the shapes
sent to Google and ElevenLabs, the paragraph cache, dubbing, the Vocal chat, prices and the page contract."""
import asyncio
import base64
import io
import json
import pathlib
import wave

import pytest

from app.vocal import consent as C
from app.vocal import eleven as EL
from app.vocal import engines as EN
from app.vocal import gvoice as GV
from app.vocal import langs as L
from app.vocal import service as V

ROOT = pathlib.Path(__file__).resolve().parents[2]


def tone(seconds=0.4, rate=24000):
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(b"\x01\x00" * int(rate * seconds))
    return b.getvalue()


def run(c):
    return asyncio.run(c)


class Resp:
    def __init__(self, status=200, body=None, content=b""):
        self.status_code, self._b, self.content = status, body, content if content else (json.dumps(body).encode() if body is not None else b"")
        self.text = self.content.decode("utf-8", "ignore")

    def json(self):
        return self._b if self._b is not None else json.loads(self.content or b"{}")


@pytest.fixture
def vg(tmp_path, monkeypatch):
    """Gemini ready (faked), ElevenLabs off, no GPU lab. `said` records what the engines were asked."""
    monkeypatch.chdir(tmp_path)
    from app.create import service as CS
    from app.interactive import lab
    said = []

    async def voice(text, voice_name="", language="English", style="friendly", speed=1.0, tenant=""):
        said.append(("gemini", voice_name, language, style, text))
        return {"bytes": tone(), "ext": ".wav", "voice": voice_name, "seconds": 0.4}

    monkeypatch.setattr(CS, "voice", voice)
    monkeypatch.setattr(CS, "ready", lambda: {"voice": True, "song": False, "dub": True, "image": True})
    monkeypatch.setattr(lab, "configured", lambda: False)
    monkeypatch.setattr(EL, "key", lambda: "")
    monkeypatch.setattr(V, "_CAT", {"at": 9e18, "gemini": [], "eleven": [], "busy": False})
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key", raising=False)
    return said


# ---------------------------------------------------------------- languages
def test_every_language_with_its_own_name_and_its_engine():
    assert len(L.LANGS) >= 140 and len({x["code"] for x in L.LANGS}) == len(L.LANGS)
    assert sum(x["gemini"] for x in L.LANGS) >= 125
    assert {x["region"] for x in L.LANGS} <= set(L.REGIONS)
    sw = L.BY_CODE["sw"]
    assert sw["native"] == "Kiswahili" and sw["gemini"] and L.BY_CODE["ja"]["native"] == "日本語"
    for code in ("zu", "ur", "yo", "cy", "mi"):                       # Gemini lacks these: premium only
        assert not L.gemini_speaks(code) and L.eleven_speaks(code), code
    assert L.eleven_model_for("yo") == "eleven_v3" and L.eleven_model_for("zu") == "eleven_v4"
    assert L.code_of("sw-KE") == "sw" and L.code_of("Kiswahili") == "sw" and L.code_of("Tagalog") == "fil"
    assert L.code_of("es_MX") == "es" and L.code_of("Auto") == "auto" and L.code_of("Klingon") == ""
    assert L.detect("Karibu Mkate Bora! Mkate wetu huokwa kila asubuhi.") == "sw"
    assert L.detect("Bienvenidos a la panadería, gracias por venir") == "es"
    assert L.detect("नमस्ते दुनिया, आपका स्वागत है") == "hi" and L.detect("こんにちは、ようこそ") == "ja"
    assert L.detect("مرحبا بكم في المخبز") == "ar" and L.detect("Olá, bem-vindos à nossa loja, obrigado") == "pt"


def test_the_consent_line_is_googles_exact_statement():
    pt = C.line_for("pt")
    assert pt["locale"] == "pt-BR" and pt["own"] and pt["line"].startswith("Eu sou o proprietário desta voz")
    assert len(C.STATEMENTS) == 30 and C.STATEMENTS["hi-IN"].endswith("सहमति देता हूं")        # no full stop: as Google wrote it
    sw = V.consent_line("sw")
    assert sw["line"] == C.ENGLISH and not sw["own"] and "Swahili" in sw["note"]                   # said, not invented


# ---------------------------------------------------------------- speech
def test_auto_language_takes_and_feelings_never_spoken(vg):
    r = run(V.tts("t1", "[warm] Karibu Mkate Bora! [laughs] Mkate wetu huokwa kila asubuhi.", voice="hv_Kore", takes=2, chat="c1"))
    assert r["lang"] == "sw" and r["lang_name"] == "Swahili" and len(r["items"]) == 2
    a, b = r["items"]
    assert (a["take"], b["take"]) == ("A", "B") and a["job"] == b["job"] and a["chat"] == "c1" and a["engine"] == "gemini"
    assert a["title"] == "Karibu Mkate Bora! Mkate wetu huokwa kila asubuhi." and a["credits"] >= 1
    eng = vg[-1]
    assert eng[2] == "Swahili" and "warm" in eng[3] and "<laugh>" in eng[4] and "[" not in eng[4]
    assert [x["id"] for x in V.chat_items("t1", "c1")] == [b["id"], a["id"]]
    f, h = V.audio_file("t1", a["id"])
    assert b"Made with AI by Hoola Vocal" in f.read_bytes()                 # the AI mark rides in every WAV
    with pytest.raises(V.VocalError):
        V.audio_file("t2", a["id"])


def test_a_language_no_engine_speaks_is_refused_never_read_in_another(vg):
    with pytest.raises(V.VocalError, match="premium engine.*ElevenLabs key"):
        run(V.tts("t1", "Sawubona, wamukelekile.", lang="zu"))
    with pytest.raises(V.VocalError, match="No voice engine"):
        run(V.tts("t1", "Allillanchu.", lang="qu-xx-unknown"))
    assert vg == []                                                    # nothing reached an engine in another language


def test_premium_speech_through_elevenlabs_with_its_own_shape(vg, monkeypatch):
    sent = []

    def http(method, url, **kw):
        sent.append((method, url, kw))
        return Resp(content=b"\x00\x01" * 2400)
    monkeypatch.setattr(EL, "key", lambda: "xi-test")
    monkeypatch.setattr(EL, "_http", http)
    r = run(V.tts("t1", "[whispers] Sawubona, wamukelekile.", lang="zu", voice="ev_abc123"))
    m, url, kw = sent[-1]
    assert m == "POST" and url.endswith("/v1/text-to-speech/abc123") and kw["params"]["output_format"] == "pcm_24000"
    assert kw["json"]["model_id"] == "eleven_v4" and kw["json"]["language_code"] == "zu"
    assert kw["json"]["text"].startswith("[whispers]") and kw["headers"]["xi-api-key"] == "xi-test"   # v3/v4 read tags natively
    assert r["engine"] == "eleven" and r["seconds"] > 0 and vg == []


def test_a_preview_is_made_once_then_kept(vg):
    a = run(V.preview("t1", "hv_Puck", "es"))
    b = run(V.preview("t2", "hv_Puck", "es"))                          # a shared library voice: the second hearing is free
    assert a == b and len(vg) == 1 and vg[0][4] == V.PREVIEW["es"] and vg[0][2] == "Spanish"


# ---------------------------------------------------------------- her own voices on Google's engine
def _fake_google(monkeypatch, voice_id="voice_123"):
    sent = []

    def http(method, url, **kw):
        sent.append((method, url, kw))
        if method == "DELETE":
            return Resp(body={})
        if url.endswith("/interactions"):
            return Resp(body={"output_audio": {"data": base64.b64encode(tone(0.3)).decode()}})
        body = kw.get("json") or {}
        v = body.get("voice") or {}
        if v.get("type") == "replicated":
            return Resp(body={"replicated_voice": {"id": voice_id}})
        return Resp(body={"id": f"{voice_id}_{len(sent)}", "sample_audio": {"mime_type": "audio/wav",
                                                                           "data": base64.b64encode(tone(0.5)).decode()}})
    monkeypatch.setattr(GV, "_http", http)
    return sent


def test_a_clone_needs_her_yes_her_spoken_consent_and_ten_seconds(vg, monkeypatch, tmp_path):
    sent = _fake_google(monkeypatch)
    rec, short, agree = tmp_path / "me.wav", tmp_path / "s.wav", tmp_path / "ok.wav"
    rec.write_bytes(tone(12)); short.write_bytes(tone(3)); agree.write_bytes(tone(5))
    with pytest.raises(V.VocalError, match="agreed"):
        V.voice_clone("t1", "Me", str(rec), "yes", consent_path=str(agree))
    with pytest.raises(V.VocalError, match="consent line"):
        V.voice_clone("t1", "Me", str(rec), True)                       # Google makes a voice only with the spoken yes
    with pytest.raises(V.VocalError, match="10 seconds"):
        V.voice_clone("t1", "Me", str(short), True, consent_path=str(agree))
    assert not V._load("t1")["voices"] and not sent
    v = V.voice_clone("t1", "Me", str(rec), True, lang="pt", consent_path=str(agree))
    body = sent[-1][2]["json"]["voice"]
    assert body["type"] == "replicated" and body["model"] == "gemini-3.8-flash-tts"
    src = base64.b64decode(body["replicated"]["source_audio"]["data"])
    assert src[:4] == b"RIFF" and body["replicated"]["consent_audio"]["mime_type"] == "audio/wav"
    assert v["gid"] == "voice_123" and v["engine"] == "gemini" and v["consent_locale"] == "pt-BR"
    V.voice_remove("t1", v["id"])
    assert sent[-1][0] == "DELETE" and sent[-1][1].endswith("/voices/voice_123")      # Google's copy goes too
    assert not list((V._home("t1") / "samples").iterdir())                              # both recordings deleted


def test_design_gives_three_options_and_keeps_only_the_picked_one(vg, monkeypatch):
    sent = _fake_google(monkeypatch)
    with pytest.raises(V.VocalError, match="named people"):
        V.design_preview("t1", "Make it sound exactly like a famous film actor")
    out = V.design_preview("t1", "An older man with a deep, kind voice, slow and calm", gender="male")
    assert len(out["previews"]) == 3 and all(p["audio_id"] for p in out["previews"])
    assert sent[0][2]["json"]["voice"]["type"] == "prompted" and "deep, kind" in sent[0][2]["json"]["voice"]["prompted"]["input"]
    f, _ = V.audio_file("t1", out["previews"][1]["audio_id"])
    assert f.read_bytes()[:4] == b"RIFF"
    v = V.design_save("t1", out["previews"][1]["pid"], "Grandpa Joe")
    assert v["kind"] == "design" and v["gid"] and v["engine"] == "gemini"
    assert [s[0] for s in sent[-2:]] == ["DELETE", "DELETE"]           # the two options she did not pick are deleted


def test_remix_changes_a_copy_never_the_base(vg, monkeypatch):
    sent = _fake_google(monkeypatch)
    with pytest.raises(V.VocalError, match="named people"):
        V.voice_remix("t1", "hv_Kore", "make her sound like a famous singer's voice of fame", "X")
    v = V.voice_remix("t1", "hv_Kore", "a little older, a warm British accent", "Kore older")
    assert sent[-1][2]["json"]["voice"]["prompted"]["base_voice"] == "Kore" and v["base"] == "hv_Kore" and v["kind"] == "remix"
    run(V.tts("t1", "Hello there.", voice=v["id"], lang="en"))


# ---------------------------------------------------------------- dialogue, podcast, studio
def test_dialogue_up_to_six_speakers_and_a_podcast_from_her_source(vg, monkeypatch):
    lines = [{"speaker": f"S{i}", "text": "Hola."} for i in range(7)]
    with pytest.raises(V.VocalError, match="6 speakers"):
        run(V.dialogue("t1", lines, {f"S{i}": "hv_Kore" for i in range(7)}))
    r = run(V.dialogue("t1", [{"speaker": "Maya", "text": "¿Qué tal?"}, {"speaker": "Kofi", "text": "Muy bien."}],
                       {"Maya": "hv_Kore", "Kofi": "hv_Puck"}, chat="c9"))
    assert r["kind"] == "dialogue" and r["lang"] == "es" and r["chat"] == "c9" and [s[1] for s in vg] == ["Kore", "Puck"]
    seen = []

    def gem(prompt):
        seen.append(prompt)
        return {"title": "Q3", "lines": [{"speaker": "Maya", "text": "[cheerful] Welcome back!"}, {"speaker": "Nobody", "text": "Sales grew."}]}
    monkeypatch.setattr(V, "_gem_json", gem)
    with pytest.raises(V.VocalError, match="few paragraphs"):
        run(V.podcast("t1", "too short"))
    out = run(V.podcast("t1", "Our bakery sold more bread this quarter. " * 10, 2, [{"name": "Maya"}, {"name": "Kofi"}], "en"))
    assert out["lines"][1]["speaker"] == "Kofi" and "never invent" in seen[0] and "<source>" in seen[0]


def test_studio_imports_casts_and_rereads_only_what_changed(vg, monkeypatch):
    text = "# The Island\n\nThe wind came first.\n\n\"Tom! Is the lamp turning?\"\n\n# The Storm\n\nShe climbed the steps."
    p = V.project_import("t1", text=text, title="The Lighthouse Keeper")
    assert [c["title"] for c in p["chapters"]] == ["The Island", "The Storm"] and p["lang"] == "en"
    monkeypatch.setattr(V, "_gem_json", lambda prompt: {"characters": [{"name": "Elena", "gender": "female"}],
                                                        "who": ["Narrator", "Elena"]})
    cast = run(V.project_cast("t1", p["id"], 0))
    assert cast["paragraphs"][1]["who"] == "Elena" and any(c["name"] == "Elena" and c["voice"] for c in cast["characters"])
    run(V.chapter_make("t1", p["id"], 0))
    run(V.chapter_make("t1", p["id"], 1))
    first = len(vg)
    assert first == 3                                                  # 2 paragraphs + 1 paragraph
    run(V.chapter_make("t1", p["id"], 0))
    assert len(vg) == first                                            # nothing changed: every paragraph from the cache
    srt = V.project_export("t1", p["id"], "srt")
    body = V.audio_file("t1", srt["id"])[0].read_text()
    assert "00:00:00,000 -->" in body and "The wind came first." in body and srt["ext"] == "srt"
    mp3 = V.project_export("t1", p["id"], "mp3")
    assert mp3["ext"] == "mp3" and V.audio_file("t1", mp3["id"])[0].read_bytes()[:3] in (b"ID3", b"\xff\xfb", b"\xff\xf3")


# ---------------------------------------------------------------- sound tools
def test_sounds_from_words_changer_and_people_removal_need_their_engine(vg, monkeypatch, tmp_path):
    rec = tmp_path / "r.wav"; rec.write_bytes(tone(1))
    with pytest.raises(V.VocalError, match="ElevenLabs key"):
        V.sfx_text("t1", "rain on a tin roof")
    with pytest.raises(V.VocalError, match="ElevenLabs key"):
        V.change("t1", str(rec), "ev_x")
    with pytest.raises(V.VocalError, match="ElevenLabs key"):
        V.cleanup("t1", str(rec), people=True)
    sent = []

    def http(method, url, **kw):
        sent.append((method, url, kw))
        return Resp(content=b"ID3" + b"\x00" * 400)
    monkeypatch.setattr(EL, "key", lambda: "xi-test")
    monkeypatch.setattr(EL, "_http", http)
    out = V.sfx_text("t1", "rain on a tin roof", seconds=10, loop=True, takes=4, chat="c2")
    assert len(out["items"]) == 4 and {i["take"] for i in out["items"]} == {"A", "B", "C", "D"}
    body = sent[-1][2]["json"]
    assert body["model_id"] == "eleven_text_to_sound_v3" and body["loop"] is True and body["duration_seconds"] == 10
    with pytest.raises(V.VocalError, match="Premium voice"):
        V.change("t1", str(rec), "hv_Kore")                            # the changer speaks only in premium voices


# ---------------------------------------------------------------- dubbing
def test_matched_dub_runs_in_the_background_and_keeps_its_lines(vg, monkeypatch, tmp_path):
    from app.create import service as CS
    vid = tmp_path / "tour.mp4"; vid.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 200)
    monkeypatch.setattr(V, "_seconds_of", lambda p: 40.0)

    async def dub(video, name, langs, keep_sound=True, voices_for=None, progress=None):
        return {"source_language": "English", "lines": [{"start": 0.5, "end": 2.0, "speaker": "S1", "text": "Hello",
                                                         "tr": {"Japanese": "こんにちは"}}],
                "outputs": [{"language": "Japanese", "bytes": b"MP4", "seconds": 40.0}]}
    monkeypatch.setattr(CS, "dub", dub)
    with pytest.raises(V.VocalError, match="Zulu"):
        V.dub_start("t1", str(vid), ["zu"])                            # matched voices: Gemini lacks Zulu - refused
    with pytest.raises(V.VocalError, match="ElevenLabs key"):
        V.dub_start("t1", str(vid), ["ja"], mode="own")
    r = V.dub_start("t1", str(vid), ["ja"])
    V._DUB_THREADS.get(r["id"]) and V._DUB_THREADS[r["id"]].join(10)
    g = V.dub_get("t1", r["id"])
    assert g["status"] == "ready" and g["langs"][0]["video_id"] and g["lines"][0]["tr"]["ja"] == "こんにちは"
    assert V.dubs("t1")[0]["id"] == r["id"]


# ---------------------------------------------------------------- the Vocal chat, prices, the page contract
def test_the_vocal_chat_is_its_own_chat_and_knows_its_rules(vg, monkeypatch):
    from app import convs, vocalchat
    from app.db import Conversation, init_db, session
    try:
        init_db()
    except Exception:   # noqa: BLE001
        pytest.skip("no database here")
    c = vocalchat.new_chat("t1")
    assert vocalchat.is_vocal(c["id"]) and vocalchat.owns("t1", c["id"]) and not vocalchat.owns("t2", c["id"])
    with session() as s:
        assert s.get(Conversation, c["id"]).kind == "vocal"
    assert '"vocal"' in (ROOT / "server/app/callconv.py").read_text() and '"vocal"' in (ROOT / "server/app/convs.py").read_text()
    run(V.tts("t1", "Hello and welcome.", voice="hv_Kore", chat=c["id"]))
    b = vocalchat.block("t1", c["id"])
    assert "create_studio action=voice" in b and "hv_Kore" in b and "Made in this chat" in b
    from app.agent import create_tools as CT
    assert "dialogue" in CT.CREATE_TOOLS[0]["input_schema"]["properties"]["action"]["enum"]


def test_prices_shown_before_the_tap_and_the_page_contract(vg):
    q = EN.quote("tts", chars=900, takes=2)
    assert q["credits"] >= 20 and "nothing is spent until you tap" in q["line"]
    assert EN.quote("dub_own", seconds=60, engine="eleven")["credits"] == 2200
    o = V.overview("t1")
    json.dumps(o)
    v = o["voices"][0]
    for k in ("id", "name", "gender", "tone", "langs", "engine", "tier", "kind", "ready", "color"):
        assert k in v, k
    lang = next(x for x in o["langs"] if x["code"] == "zu")
    assert lang["speech"] == "premium" and lang["quality"] == "not_tested" and lang["native"] == "isiZulu"
    assert {e["id"] for e in o["engines"]} == {"gemini", "eleven", "lab", "server"}
    assert next(e for e in o["engines"] if e["id"] == "eleven")["state"] == "needs_key"
    assert o["prices"] and o["feelings"][0] == "warm" and o["limits"]["characters"] == 100000


def test_the_routes_and_version():
    paths = (ROOT / "server/app/vocal/api.py").read_text()
    for route in ('"/quote"', '"/podcast"', '"/consent-line"', '"/voice/design/save"', '"/voice/remix"', '"/change"',
                  '"/dub"', '"/dub/{did}"', '"/dubs"', '"/project/import"', '"/project/cast"'):
        assert route in paths, route
    assert "/api/vocal/chat/{conv}/items" in (ROOT / "server/app/vocalchat.py").read_text()
    assert "_vocalchat_mod.mount(app, current_tenant, require_key)" in (ROOT / "server/app/main.py").read_text()
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.103"
