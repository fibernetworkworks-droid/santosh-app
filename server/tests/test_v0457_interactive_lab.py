"""v0.457 HOOLA INTERACTIVE Phase 0: the Model Lab (owner: "LET WE BUILD OUR OWN HEYGEN ... AS GPU ON VPS",
"DONE MODEL LAB").

The GPU is not in this sandbox, so these tests prove what can be proved without one: the licence gate refuses what it
must, the Hoola-side client refuses a face without consent and caps every size, the key never leaks, and the lab's own
rules are present in its code."""
import ast
import re
import sys
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "avatar_engine"
MODAL_SRC = (ENGINE / "modal_app.py").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github" / "workflows" / "interactive-lab.yml").read_text(encoding="utf-8")


@pytest.fixture()
def reg():
    sys.path.insert(0, str(ENGINE))
    try:
        import registry
        yield registry
    finally:
        sys.path.remove(str(ENGINE))


# ---------------------------------------------------------------- the licence gate
def test_refused_licences_never_load(reg):
    for k in ("f5_tts", "xtts_v2", "fish_s1_mini", "wav2lip"):
        assert reg.MODELS[k]["use"] == "refused", k
        with pytest.raises(reg.Refused):
            reg.check(k, "lab")
        with pytest.raises(reg.Refused):
            reg.check(k, "ship")


def test_lab_only_models_cannot_ship(reg):
    lab_only = [k for k, m in reg.MODELS.items() if m["use"] == "lab_only"]
    assert {"indicf5", "face_parse_bisenet", "dwpose"} <= set(lab_only)   # the open licence questions, named
    for k in lab_only:
        assert reg.check(k, "lab")["use"] == "lab_only"
        with pytest.raises(reg.Refused):
            reg.check(k, "ship")
        assert reg.MODELS[k].get("note"), f"{k}: a lab-only model must say WHY"


def test_shippable_models_are_the_licence_checked_ones(reg):
    ship = {k for k, m in reg.MODELS.items() if m["use"] == "commercial"}
    assert ship == {"chatterbox", "faster_whisper_small", "indic_parler", "musetalk", "sd_vae", "whisper_tiny"}   # whisper small: MIT code + MIT weights, read 3 Nov 2026
    assert "hi" in reg.MODELS["chatterbox"]["langs"] and reg.MODELS["chatterbox"]["clone"] is True
    assert {"hi", "mr", "ta", "te", "bn"} <= set(reg.MODELS["indic_parler"]["langs"])
    assert reg.MODELS["indic_parler"]["clone"] is False                  # described in words, never cloned
    with pytest.raises(reg.Refused):
        reg.check("chatterbox", "nonsense")                              # an unknown purpose is not a pass
    with pytest.raises(reg.Refused):
        reg.check("no-such-model")


def test_voices_and_public_rows(reg):
    assert set(reg.voices("ship")) == {"chatterbox", "indic_parler"}
    assert set(reg.voices("lab")) == {"chatterbox", "indic_parler", "indicf5"}
    rows = reg.public()
    assert len(rows) == len(reg.MODELS) and all(r["licence"] and r["use"] in reg.USES for r in rows)


# ---------------------------------------------------------------- Hoola's client
def _lab(monkeypatch, url="https://lab.test", key="k"):
    from app import config
    from app.interactive import lab
    config.get_settings.cache_clear()
    monkeypatch.setenv("AVATAR_ENGINE_URL", url)
    monkeypatch.setenv("AVATAR_ENGINE_KEY", key)
    config.get_settings.cache_clear()
    return lab


def test_off_until_configured(env, monkeypatch):
    lab = _lab(monkeypatch, url="", key="")
    assert lab.configured() is False
    with pytest.raises(lab.LabError, match="not set up"):
        lab.voice("hello")


def test_a_face_needs_consent(env, monkeypatch):
    lab = _lab(monkeypatch)
    sent = []
    monkeypatch.setattr(lab.httpx, "request", lambda *a, **k: sent.append(k) or httpx.Response(200, json={"ok": True}))
    for bad in ("", "yes", "signed:", "ai", "signed:x"):
        with pytest.raises(lab.LabError, match="consent"):
            lab.face_prepare("meera", b"video-bytes", bad)
    assert sent == []                                                     # refused BEFORE any upload
    lab.face_prepare("meera", b"video-bytes", "ai_generated")
    lab.face_prepare("meera", b"video-bytes", "signed:consent-7781")
    assert len(sent) == 2


def test_sizes_and_names_capped(env, monkeypatch):
    lab = _lab(monkeypatch)
    monkeypatch.setattr(lab.httpx, "request", lambda *a, **k: httpx.Response(200, json={}))
    with pytest.raises(lab.LabError, match="30 MB"):
        lab.face_prepare("m", b"x" * (lab.MAX_FACE_VIDEO + 1), "ai_generated")
    with pytest.raises(lab.LabError, match="8 MB"):
        lab.face_speak("m", b"x" * (lab.MAX_SPEAK_AUDIO + 1))
    with pytest.raises(lab.LabError, match="Too long"):
        lab.voice("x" * (lab.MAX_TEXT + 1))
    with pytest.raises(lab.LabError, match="2 MB"):
        lab.voice("hi", ref_audio=b"x" * (lab.MAX_REF_AUDIO + 1))
    with pytest.raises(lab.LabError, match="Unknown voice model"):
        lab.voice("hi", model="xtts_v2")                                  # a refused model is not reachable from Hoola
    for bad in ("Meera", "../x", "a" * 41, "", "x y"):
        with pytest.raises(lab.LabError):
            lab.face_prepare(bad, b"v", "ai_generated")
        with pytest.raises(lab.LabError):
            lab.face_forget(bad)


def test_key_travels_only_in_the_header(env, monkeypatch):
    lab = _lab(monkeypatch, key="super-secret-key")
    seen = {}

    def fake(method, url, **kw):
        seen.update(method=method, url=url, **kw)
        return httpx.Response(200, content=b"RIFFfake")
    monkeypatch.setattr(lab.httpx, "request", fake)
    assert lab.voice("नमस्ते", lang="hi") == b"RIFFfake"
    assert seen["headers"]["Authorization"] == "Bearer super-secret-key"
    assert "super-secret-key" not in str(seen["json"]) and "super-secret-key" not in seen["url"]
    assert seen["json"]["text"] == "नमस्ते" and seen["json"]["model"] == "chatterbox"


def test_engine_failures_become_plain_errors(env, monkeypatch):
    lab = _lab(monkeypatch)
    for resp, msg in ((httpx.Response(401), "refused our key"),
                      (httpx.Response(403, json={"detail": "f5_tts is refused"}), "refused"),
                      (httpx.Response(500, text="boom"), "refused")):
        monkeypatch.setattr(lab.httpx, "request", lambda *a, _r=resp, **k: _r)
        with pytest.raises(lab.LabError, match=msg):
            lab.voice("hi")

    def timeout(*a, **k):
        raise httpx.TimeoutException("slow")
    monkeypatch.setattr(lab.httpx, "request", timeout)
    with pytest.raises(lab.LabError, match="did not answer in time"):
        lab.voice("hi")


# ---------------------------------------------------------------- the GPU app's own rules
def test_gpu_app_is_locked_and_guarded():
    assert "hmac.compare_digest" in MODAL_SRC                              # no == on a key
    assert 'if not want or not hmac.compare_digest' in MODAL_SRC           # no key configured = locked, not open
    assert MODAL_SRC.count("Depends(key)") >= 5                            # every route, health included
    assert "registry.check(" in MODAL_SRC and 'CONSENT.match' in MODAL_SRC
    assert "stdin=subprocess.DEVNULL" in MODAL_SRC                         # MuseTalk asks y/n; it must never block
    assert "scaledown_window=IDLE" in MODAL_SRC and "IDLE = 120" in MODAL_SRC   # an idle lab costs nothing
    assert "-r\", \"25\"" in MODAL_SRC or '"-r", "25"' in MODAL_SRC        # MuseTalk is trained at 25 fps
    assert ast.parse(MODAL_SRC)                                            # it parses on this Python too
    assert not re.search(r"ENGINE_KEY\s*=\s*[\"'][^\"']+[\"']", MODAL_SRC)  # no key literal anywhere
    assert "modal.Secret.from_name" in MODAL_SRC


def test_every_voice_model_in_the_app_is_allowed(reg):
    for name in re.findall(r'registry\.check\("([a-z0-9_]+)"', MODAL_SRC):
        assert reg.MODELS[name]["use"] != "refused", name


def test_workflow_runs_only_by_hand_and_keeps_the_proof():
    assert "workflow_dispatch" in WORKFLOW and "on:\n  workflow_dispatch" in WORKFLOW   # never on a push: GPU costs
    for job in ("setup", "prefetch", "smoke", "deploy", "down"):
        assert job in WORKFLOW, job
    assert "upload-artifact" in WORKFLOW and "lab_out" in WORKFLOW         # the clips + REPORT.txt come back
    assert "secrets.MODAL_TOKEN_ID" in WORKFLOW and "secrets.HOOLA_ENGINE_KEY" in WORKFLOW
    assert "modal app stop hoola-lab" in WORKFLOW                          # a way to stop paying


def test_face_bench_and_face_only_jobs_exist_and_the_embedded_script_parses():
    """v0.462: the speed benchmark runs a script inside the face container, so a syntax slip would only show after a
    45-minute GPU run. Parse it here, and keep the two extra hand-run jobs wired to their entrypoints + the artifact."""
    m = re.search(r'_BENCH_SCRIPT = """(.*?)\n"""\n', MODAL_SRC, re.S)
    assert m and ast.parse(m.group(1))
    assert "from scripts import realtime_inference as rt" in m.group(1)       # MuseTalk's own Avatar class, not a copy
    for job, entry in (("face", "smoke_face"), ("bench", "bench_face")):
        assert job in WORKFLOW and f"modal_app.py::{entry}" in WORKFLOW, job
        assert f"def {entry}" in MODAL_SRC
    assert "inputs.job == 'bench'" in WORKFLOW and "REPORT_bench.txt" in MODAL_SRC
    # the lab never hangs a whole run on one call again
    assert "def _call(" in MODAL_SRC and "fc.get(timeout=wait)" in MODAL_SRC


def _playback_fn():
    """Pull `_playback` out of the GPU app's source (the app itself needs Modal to import) so its maths can be tested."""
    tree = ast.parse(MODAL_SRC)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_playback")
    ns: dict = {}
    exec(compile(ast.Module([fn], []), "modal_app", "exec"), ns)
    return ns["_playback"]


def test_stall_maths_for_the_concurrency_test():
    """The 'how many students per GPU' verdict is only as good as this replay: a stream is smooth when each batch is ready
    before the 25 fps playhead needs it, and every late batch freezes the picture for exactly how late it was."""
    play = _playback_fn()
    # 8 frames = 0.32 s of picture. Ready every 0.20 s (faster than playback): no stall, however long it runs.
    fast = play([(0.30 + 0.20 * k, 8) for k in range(10)])
    assert fast["stall_s"] == 0 and fast["stalls"] == 0 and fast["first_s"] == 0.3
    # Ready every 0.50 s (slower than the 0.32 s each batch plays): the picture waits 0.18 s for every batch after the first.
    slow = play([(0.30 + 0.50 * k, 8) for k in range(5)])
    assert slow["stalls"] == 4 and abs(slow["stall_s"] - 4 * 0.18) < 0.01
    # Nothing came back: reported as nothing, never as 'smooth'.
    assert play([])["first_s"] is None
    assert "max_containers=4" in MODAL_SRC and "@modal.concurrent" not in MODAL_SRC   # one student per card: sharing hung the GPU
    assert "streams" in WORKFLOW and "modal_app.py::bench_streams" in WORKFLOW and "REPORT_streams.txt" in MODAL_SRC


def test_live_face_overlaps_cpu_with_gpu_and_the_streams_test_cannot_hang_for_half_an_hour():
    """The first `streams` run on an L40S showed one student at 23.5 fps (< 25) although the GPU alone does ~40: the CPU
    half of each frame (blend + JPEG) ran in line with the GPU half, and 4 streams hung until Modal's 1800 s limit."""
    assert "cpu=4" in MODAL_SRC and "ThreadPoolExecutor(max_workers=6)" in MODAL_SRC
    assert "pending = None" in MODAL_SRC and "self.pool.submit(finish" in MODAL_SRC      # next GPU batch runs while this one is blended
    assert "deadline = time.time() + 420" in MODAL_SRC and "timeout=600" in MODAL_SRC      # a stuck stream costs minutes


def test_a_hung_live_stream_leaves_a_thread_dump_and_opencv_does_not_add_its_own_threads():
    """The second `streams` run: ONE student 37.7 fps and smooth, TWO students hung with no error text. The next hang must say
    where every thread is stuck (faulthandler dump into the container log) and OpenCV must not spawn a second pool."""
    assert "faulthandler.dump_traceback_later(240, repeat=True)" in MODAL_SRC and "cv2.setNumThreads(1)" in MODAL_SRC


def test_a_prepared_face_is_shared_through_the_volume_so_any_container_can_stream_it():
    """One student per card means a second student lands on a COLD container, which has never prepared the face (84-160 s):
    it must load it from the volume (committed by `prepare`), and an unknown or badly named face must still be refused."""
    assert "volume.commit()      # results/ is the volume" in MODAL_SRC
    assert "def _avatar(self, avatar_id: str):" in MODAL_SRC and "preparation=False" in MODAL_SRC
    assert "av = self._avatar(avatar_id)" in MODAL_SRC and "latents.pt" in MODAL_SRC


def test_e2e_bench_wired():
    import re
    import struct
    wf = open("../.github/workflows/interactive-lab.yml").read()
    assert "bench_e2e" in wf and "e2e, studio, deploy" in wf
    assert "def bench_e2e" in MODAL_SRC and "REPORT_e2e.txt" in MODAL_SRC
    ns: dict = {}
    exec(re.search(r"def _wav_seconds.*?\n\n\n", MODAL_SRC, re.S).group(0), ns)
    pcm = b"\0\0" * 24000
    hdr = b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, 24000, 48000, 2, 16) + b"data" + struct.pack("<I", len(pcm))
    assert abs(ns["_wav_seconds"](hdr + pcm) - 1.0) < 0.01


def test_chunker_and_warm_switch():
    import re
    ns: dict = {}
    exec(re.search(r"def split_speech.*?\n\n\n", MODAL_SRC, re.S).group(0), ns)
    sp = ns["split_speech"]
    long_t = " ".join(["शब्द%d" % i + ("," if i % 6 == 0 else "") for i in range(1, 61)])
    parts = sp(long_t)
    sizes = [len(p.split()) for p in parts]
    assert 3 <= sizes[0] <= 7 and len(parts) >= 3
    assert sizes[1] > sizes[0] and min(sizes) >= 3                       # chunks grow, none is a stub
    assert " ".join(parts).split() == long_t.split()                     # nothing lost, nothing added
    assert sp("") == [] and sp("नमस्ते") == ["नमस्ते"]
    assert len(sp("एक दो तीन चार पाँच")) == 1
    assert "min_containers=WARM" in MODAL_SRC and 'HOOLA_LAB_WARM", "0"' in MODAL_SRC
    assert "HOOLA_LAB_WARM" in open("../.github/workflows/interactive-lab.yml").read()
    assert '"runaway"' in MODAL_SRC and "e2e_chunk" in MODAL_SRC or 'keep(f"chunk' in MODAL_SRC


def test_parallel_voice_containers():
    assert "min_containers=VOICE_WARM" in MODAL_SRC and 'HOOLA_LAB_VOICES' in MODAL_SRC
    assert "HOOLA_LAB_VOICES" in open("../.github/workflows/interactive-lab.yml").read()
    assert "make(i: int, c: str)" in MODAL_SRC                   # chunks are asked for at once, not one after another


def test_live_socket_and_student_page():
    import shutil
    import subprocess
    from pathlib import Path
    src = MODAL_SRC
    assert 'api.websocket("/live")(live_socket)' in src and "live_socket.__annotations__" in src
    body = src[src.index("async def live_socket"):src.index('api.websocket("/live")')]
    assert 'hello.get("key")' in body and "compare_digest" in body          # key in the first message, never in the address
    assert "AVATAR_ID.match(avatar)" in body and "MAX_TEXT" in body          # same guards as the other doors
    assert "asyncio.create_task(voice.speak.remote.aio" in body              # every chunk's voice starts at once
    assert "async for b in face.stream.remote_gen.aio" in body               # read to the end: cancelling restarts a container
    assert ".cancel()" not in body                                           # voice calls are never cancelled
    assert "the live talk stopped" in body and "str(e)" not in body.split("say(type=\"error\", msg=\"the live")[1][:80]   # no internals to the browser
    root = Path(__file__).resolve().parents[1] / "app" / "static" / "interactive"
    html = (root / "live.html").read_text()
    assert "live.js" in html and 'type="password"' not in html and 'id="key"' not in html     # no key box: the page gets a pass
    assert "/api/interactive/ticket" in html and 'localStorage.getItem("hoola.console.token")' in html
    assert "localStorage.setItem" not in html and "sessionStorage" not in html
    if shutil.which("node"):
        r = subprocess.run(["node", str(Path(__file__).with_name("live_js_check.js")), str(root / "live.js")], capture_output=True, text=True)
        assert r.returncode == 0 and "live.js ok" in r.stdout, r.stdout + r.stderr


def test_live_ticket_end_to_end(env, monkeypatch):
    """The Hoola server signs a 2-minute pass; the engine's own check accepts it for that avatar only, and nothing else."""
    import re
    import time

    lab = _lab(monkeypatch, url="https://x--hoola-lab-web.us-east.modal.run", key="k" * 40)
    ns: dict = {"time": time}
    exec(re.search(r"def _ticket_ok.*?\n\n\n", MODAL_SRC, re.S).group(0), ns)
    ok = ns["_ticket_ok"]
    t = lab.make_ticket("lab-live")
    assert ok(t, "lab-live", "k" * 40)
    assert not ok(t, "someone-else", "k" * 40)                  # one avatar only
    assert not ok(t, "lab-live", "j" * 40)                      # wrong key
    assert not ok(t[:-2] + "00", "lab-live", "k" * 40)          # tampered
    old = f"{int(time.time()) - 5}.lab-live." + t.split(".", 2)[2]
    assert not ok(old, "lab-live", "k" * 40)                    # expired (and the signature no longer matches the new time)
    assert "k" * 10 not in t                                    # the key is not in the pass
    assert lab.live_address().startswith("wss://x--hoola-lab-web")
    with pytest.raises(lab.LabError):
        lab.make_ticket("Bad Name!")
    _lab(monkeypatch, url="", key="")
    with pytest.raises(lab.LabError):
        lab.make_ticket("lab-live")


def test_ticket_route_is_owner_only_and_never_returns_the_key(env, monkeypatch):
    from fastapi.testclient import TestClient

    from app import main
    from app.config import get_settings
    monkeypatch.setenv("AVATAR_ENGINE_URL", "https://x--hoola-lab-web.us-east.modal.run")
    monkeypatch.setenv("AVATAR_ENGINE_KEY", "secret-engine-key-" + "z" * 20)
    get_settings.cache_clear()
    with TestClient(main.app) as c:
        r = c.post("/api/interactive/ticket", json={"avatar_id": "lab-live"})
        assert r.status_code == 200, r.text
        assert r.json()["address"].startswith("wss://") and r.json()["ticket"].count(".") == 2
        assert "secret-engine-key" not in r.text
        assert c.post("/api/interactive/ticket", json={"avatar_id": "Not Valid"}).status_code == 503


def test_engine_attach_job_uses_the_saved_secret():
    wf = (ROOT / ".github" / "workflows" / "vps-ops.yml").read_text(encoding="utf-8")
    assert "- engine_attach" in wf and "secrets.HOOLA_ENGINE_KEY" in wf and "engine_attach)" in wf
    body = wf[wf.index("engine_attach)"):wf.index("zoo_check)")]
    assert "AVATAR_ENGINE_KEY" in body and "value hidden" in body and "echo \"$ENGINE_KEY_IN" not in body
    assert "ENGINE_KEY_IN" in wf.split("jobs:")[1][:3000]       # passed through env, never typed into a script by hand


def test_studio_helpers_and_door():
    """Hoola Studio (the HeyGen feature set): the pure helpers work, every op is behind the key and its consent rules."""
    import io
    import re
    import struct
    import wave

    ns: dict = {}
    for fn in ("_wav_seconds", "_wav_concat", "_vtt"):
        exec(re.search(rf"def {fn}\(.*?\n\n\n", MODAL_SRC, re.S).group(0), ns)

    def wav(sec, rate=24000):
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(struct.pack("<h", 0) * int(rate * sec))
        return buf.getvalue()

    joined = ns["_wav_concat"]([wav(1.0), wav(0.5)], gap_s=0.25)
    assert abs(ns["_wav_seconds"](joined) - 1.75) < 0.02
    with pytest.raises(ValueError):
        ns["_wav_concat"]([wav(1.0, 24000), wav(1.0, 16000)])            # mixed formats are refused, not played at the wrong speed
    v = ns["_vtt"]([(0.0, 2.5, "नमस्ते"), (2.5, 61.0, "दूसरा")])
    assert v.startswith("WEBVTT") and "00:00:00.000 --> 00:00:02.500" in v and "00:01:01.000" in v

    assert 'STUDIO_OPS = ("video", "photo_face", "voice_save", "transcribe", "dub", "podcast", "personalised")' in MODAL_SRC
    door = MODAL_SRC[MODAL_SRC.index('@api.post("/studio/{op}"'):MODAL_SRC.index("async def live_socket")]
    assert "Depends(key)" in door and door.count("Depends(key)") == 2 and "b64(p[k], cap, k)" in door
    job = MODAL_SRC[MODAL_SRC.index("def studio_job"):MODAL_SRC.index("def _sample_photo")]
    assert "signed:" in job and "dubbing a real person needs consent" in job and "finally:" in job   # consent + temp face / voice always removed
    save = MODAL_SRC[MODAL_SRC.index("def save_voice"):MODAL_SRC.index("def _voice_ref")]
    assert "signed:" in save and "ai_generated" not in save                    # a cloned voice can never be 'ai generated'
    assert "faster_whisper_small" in (ROOT / "avatar_engine" / "registry.py").read_text()
    assert "studio_card" in WORKFLOW and "inputs.job == 'studio'" in WORKFLOW


def test_studio_card_fixes_from_the_first_real_run():
    """Studio card run 33 (L40S): 5/10. Each failure, pinned to its real cause from the log."""
    live = MODAL_SRC[MODAL_SRC.index("class Live:"):MODAL_SRC.index("class Live:") + 20000]
    # photo avatar called self._prepare_impl, which only the old Face class had
    assert "def _prepare_impl(self, avatar_id: str, video: bytes, consent: str)" in live
    assert "return self._prepare_impl(avatar_id, video, consent)" in live.split("def prepare_photo")[1][:1200]
    # transcribe returned numpy floats into the numpy-free studio image
    hear = MODAL_SRC[MODAL_SRC.index("class Hear:"):MODAL_SRC.index("def _speak_chunks")]
    assert "round(sg.start" not in hear and "round(float(sg.start), 2)" in hear and "round(float(w.start), 2)" in hear
    # dub got a silent sample video: no sound = no voice to copy, said plainly; the card now sends a speaking clip
    dub = MODAL_SRC[MODAL_SRC.index('if op == "dub":'):MODAL_SRC.index('if op == "podcast":')]
    assert dub.index("_has_audio(src)") < dub.index("save_voice")
    assert '"dub", {"video": _sample_talking.remote()' in MODAL_SRC


def test_voice_never_cut_off_mid_sentence_and_takes_judged_both_ways():
    m = re.search(r'CB_PATCH = r"""(.*?)"""', MODAL_SRC, re.S)
    assert m and "'" not in m.group(1)                       # it rides inside python -c '...'
    code = m.group(1)
    assert "assert s.count(old) == 1" in code and "self.complete and len(self.generated_tokens) >= 4" in code
    assert 'base64.b64encode(CB_PATCH.encode())' in MODAL_SRC and '| base64 -d | python' in MODAL_SRC
    ns: dict = {}
    exec(re.search(r"def _take_off.*?\n\n\n", MODAL_SRC, re.S).group(0), ns)
    off = ns["_take_off"]
    assert off(4.5, 10) < off(1.0, 10) and off(4.5, 10) < off(12.0, 10)
    speak = MODAL_SRC[MODAL_SRC.index("def speak(self, text: str, lang"):MODAL_SRC.index("@app.cls", MODAL_SRC.index("def speak(self, text: str, lang"))]
    assert "floor <= secs <= limit" in speak and '"cut_short": secs < floor' in speak
