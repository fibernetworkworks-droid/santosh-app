"""Hoola Interactive - Model Lab on Modal (docs/INTERACTIVE_AVATAR_PLAN.md, Phase 0 / 1).

What it is: the three voice engines and the face engine, each in its own GPU container (their library versions clash:
Chatterbox needs transformers 5.2, Parler pins 4.46.1, MuseTalk needs torch 2.0.1 + mmcv 2.0.1), one shared volume for
downloaded weights, and one locked web endpoint. Containers start on demand and shut down after 2 idle minutes, so
an idle lab costs nothing.

Run from this folder (or let .github/workflows/interactive-lab.yml do it):
    modal deploy modal_app.py          # the web endpoint + engines
    modal run modal_app.py::prefetch   # download every lab-allowed model into the volume (no GPU)
    modal run modal_app.py::smoke      # one Hindi + English line per voice, one talking clip; files into ./lab_out

Secrets (Modal secret "hoola-lab", created by the workflow from GitHub secrets; never in this file):
    ENGINE_KEY  - the bearer key the Hoola server sends
    HF_TOKEN    - a Hugging Face token whose account accepted AI4Bharat's terms (IndicF5, Indic Parler-TTS are gated)

Lab rules, in code: every model passes registry.check() (refused licences never load); a face is prepared only with a
consent tag ("ai_generated" or "signed:<record id>"); sizes are capped; nothing a user sends is kept after the call
except a prepared face, which lives only under its avatar id until deleted.
"""
from __future__ import annotations

import base64
import os
import re
import shutil
import subprocess
import time
import uuid

import modal

import registry

APP = "hoola-lab"
GPU = os.environ.get("HOOLA_LAB_GPU", "L4")          # L4 is in Modal's free monthly credit range; A10G / L40S for speed tests
IDLE = 120                                          # seconds an idle container lives (credit saver)
MODELS_DIR = "/models"
HF_ENV = {"HF_HOME": f"{MODELS_DIR}/hf", "HF_HUB_ENABLE_HF_TRANSFER": "0"}
MUSE_DIR = "/opt/MuseTalk"
MAX_TEXT = 600
MAX_REF_AUDIO = 2 * 1024 * 1024
MAX_FACE_VIDEO = 30 * 1024 * 1024
MAX_SPEAK_AUDIO = 8 * 1024 * 1024
AVATAR_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")
CONSENT = re.compile(r"^(ai_generated|signed:[A-Za-z0-9_-]{4,64})$")

app = modal.App(APP)
volume = modal.Volume.from_name("hoola-lab-models", create_if_missing=True)
secret = modal.Secret.from_name("hoola-lab")

# ---------------------------------------------------------------- images (one per clashing stack)
_base = modal.Image.debian_slim(python_version="3.11").apt_install("ffmpeg", "git").env(HF_ENV)
chatterbox_image = _base.pip_install("chatterbox-tts==0.1.7", "soundfile", "huggingface_hub").add_local_python_source("registry")
indicf5_image = (_base.pip_install("git+https://github.com/ai4bharat/IndicF5.git", "soundfile", "huggingface_hub")
                 # newest `datasets` needs pyarrow>=24, which needs NumPy 2; this stack is on NumPy 1.26 -> pin a matching pair
                 .pip_install("pyarrow==16.1.0", "datasets==2.21.0")
                 .run_commands("git clone --depth 1 https://github.com/AI4Bharat/IndicF5.git /opt/IndicF5")
                 .add_local_python_source("registry"))
parler_image = (_base.pip_install("git+https://github.com/huggingface/parler-tts.git", "soundfile", "huggingface_hub")
                .pip_install("pyarrow==16.1.0", "datasets==2.21.0")   # same datasets / pyarrow / NumPy pairing as IndicF5
                .add_local_python_source("registry"))
face_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "git", "libgl1", "libglib2.0-0")
    .pip_install("torch==2.0.1", "torchvision==0.15.2", "torchaudio==2.0.2", index_url="https://download.pytorch.org/whl/cu118")
    .run_commands(
        f"git clone --depth 1 https://github.com/TMElyralab/MuseTalk.git {MUSE_DIR}",
        f"cd {MUSE_DIR} && git rev-parse HEAD > COMMIT && pip install -r requirements.txt",
        "pip install --no-cache-dir -U openmim",
        "mim install mmengine", 'mim install "mmcv==2.0.1"', 'mim install "mmdet==3.1.0"',
        # chumpy's setup.py imports pip, which pip's isolated build env lacks -> build it in this env first
        "pip install --no-build-isolation chumpy", 'mim install "mmpose==1.1.0"',
        "pip install gdown",
        # MuseTalk's script points downloads at a mirror; the lab downloads from the source.
        f"sed -i '/HF_ENDPOINT/d' {MUSE_DIR}/download_weights.sh",
        # last: the pins MuseTalk's own requirements.txt uses (a later install had pulled NumPy 2, which cv2 cannot load)
        "pip install 'numpy==1.23.5' 'huggingface_hub==0.30.2'",
    )
    .env(HF_ENV)
    .add_local_python_source("registry")
)
web_image = modal.Image.debian_slim(python_version="3.11").pip_install("fastapi[standard]").add_local_python_source("registry")


def _wav_bytes(wav, sr: int) -> bytes:
    import io

    import numpy as np
    import soundfile as sf
    a = wav.detach().cpu().numpy() if hasattr(wav, "detach") else np.asarray(wav)
    a = a.squeeze()
    if a.dtype == np.int16:
        a = a.astype(np.float32) / 32768.0
    buf = io.BytesIO()
    sf.write(buf, a.astype("float32"), sr, format="WAV")
    return buf.getvalue()


def _tmp(data: bytes | None, suffix: str) -> str | None:
    if not data:
        return None
    p = f"/tmp/{uuid.uuid4().hex}{suffix}"
    with open(p, "wb") as f:
        f.write(data)
    return p


# ---------------------------------------------------------------- voice engines
@app.cls(gpu=GPU, image=chatterbox_image, volumes={MODELS_DIR: volume}, secrets=[secret], scaledown_window=IDLE, timeout=600)
class Chatterbox:
    @modal.enter()
    def load(self):
        registry.check("chatterbox", "lab")
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        t = time.time()
        try:   # newer releases choose the T3 checkpoint; the PyPI 0.1.7 we pin does not take the argument
            self.model = ChatterboxMultilingualTTS.from_pretrained(device="cuda", t3_model="v3")
        except TypeError:
            self.model = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
        self.load_s = round(time.time() - t, 1)
        volume.commit()

    @modal.method()
    def speak(self, text: str, lang: str = "hi", ref_audio: bytes | None = None, **_) -> dict:
        ref = _tmp(ref_audio, ".wav")
        t = time.time()
        wav = self.model.generate(text, language_id=lang, **({"audio_prompt_path": ref} if ref else {}))
        out = _wav_bytes(wav, self.model.sr)
        return {"wav": out, "sr": self.model.sr, "synth_s": round(time.time() - t, 2), "load_s": self.load_s}


@app.cls(gpu=GPU, image=indicf5_image, volumes={MODELS_DIR: volume}, secrets=[secret], scaledown_window=IDLE, timeout=600)
class IndicF5:
    @modal.enter()
    def load(self):
        registry.check("indicf5", "lab")
        from transformers import AutoModel
        t = time.time()
        self.model = AutoModel.from_pretrained("ai4bharat/IndicF5", trust_remote_code=True, token=os.environ.get("HF_TOKEN"))
        self.load_s = round(time.time() - t, 1)
        volume.commit()

    @modal.method()
    def speak(self, text: str, lang: str = "hi", ref_audio: bytes | None = None, ref_text: str = "", **_) -> dict:
        if not ref_audio or not ref_text:   # IndicF5 always clones: the repo's own sample prompt stands in for a voice
            ref_path = "/opt/IndicF5/prompts/PAN_F_HAPPY_00001.wav"
            ref_text = ("ਭਹੰਪੀ ਵਿੱਚ ਸਮਾਰਕਾਂ ਦੇ ਭਵਨ ਨਿਰਮਾਣ ਕਲਾ ਦੇ ਵੇਰਵੇ ਗੁੰਝਲਦਾਰ ਅਤੇ ਹੈਰਾਨ ਕਰਨ ਵਾਲੇ ਹਨ, "
                        "ਜੋ ਮੈਨੂੰ ਖੁਸ਼ ਕਰਦੇ  ਹਨ।")
        else:
            ref_path = _tmp(ref_audio, ".wav")
        t = time.time()
        audio = self.model(text, ref_audio_path=ref_path, ref_text=ref_text)
        return {"wav": _wav_bytes(audio, 24000), "sr": 24000, "synth_s": round(time.time() - t, 2), "load_s": self.load_s}


@app.cls(gpu=GPU, image=parler_image, volumes={MODELS_DIR: volume}, secrets=[secret], scaledown_window=IDLE, timeout=600)
class IndicParler:
    @modal.enter()
    def load(self):
        registry.check("indic_parler", "lab")
        from parler_tts import ParlerTTSForConditionalGeneration
        from transformers import AutoTokenizer
        t = time.time()
        tok = os.environ.get("HF_TOKEN")
        self.model = ParlerTTSForConditionalGeneration.from_pretrained("ai4bharat/indic-parler-tts", token=tok).to("cuda")
        self.tok = AutoTokenizer.from_pretrained("ai4bharat/indic-parler-tts", token=tok)
        self.desc_tok = AutoTokenizer.from_pretrained(self.model.config.text_encoder._name_or_path, token=tok)
        self.load_s = round(time.time() - t, 1)
        volume.commit()

    @modal.method()
    def speak(self, text: str, lang: str = "hi", description: str = "", **_) -> dict:
        description = description or ("A warm female teacher speaks clearly at a moderate pace in a quiet room; "
                                      "the recording is very clear and close.")
        t = time.time()
        d = self.desc_tok(description, return_tensors="pt").to("cuda")
        p = self.tok(text, return_tensors="pt").to("cuda")
        gen = self.model.generate(input_ids=d.input_ids, attention_mask=d.attention_mask,
                                  prompt_input_ids=p.input_ids, prompt_attention_mask=p.attention_mask)
        sr = self.model.config.sampling_rate
        return {"wav": _wav_bytes(gen, sr), "sr": sr, "synth_s": round(time.time() - t, 2), "load_s": self.load_s}


VOICES = {"chatterbox": Chatterbox, "indicf5": IndicF5, "indic_parler": IndicParler}


# ---------------------------------------------------------------- face engine (MuseTalk 1.5)

# What MuseTalk 1.5 needs, from its own download_weights.sh: (repo, file, folder under models/). The v1.0 weights are not
# fetched - this lab runs --version v15. We do not use that script: it upgrades huggingface_hub (which removes the
# `huggingface-cli` it then calls), needs curl, and prints "downloaded successfully" whatever happened.
_MUSE_FILES = [
    ("TMElyralab/MuseTalk", "musetalkV15/musetalk.json", ""),
    ("TMElyralab/MuseTalk", "musetalkV15/unet.pth", ""),
    ("stabilityai/sd-vae-ft-mse", "config.json", "sd-vae"),
    ("stabilityai/sd-vae-ft-mse", "diffusion_pytorch_model.bin", "sd-vae"),
    ("openai/whisper-tiny", "config.json", "whisper"),
    ("openai/whisper-tiny", "pytorch_model.bin", "whisper"),
    ("openai/whisper-tiny", "preprocessor_config.json", "whisper"),
    ("yzd-v/DWPose", "dw-ll_ucoco_384.pth", "dwpose"),
    ("ByteDance/LatentSync", "latentsync_syncnet.pt", "syncnet"),
]
_FACE_PARSE_GDRIVE = "154JgKpzCPW82qINcVieuPH3fZ2e0P812"
_RESNET18 = "https://download.pytorch.org/models/resnet18-5c106cde.pth"


def _fetch_muse_weights(models: str) -> bool:
    """Download what is missing, then check every file is really there. Returns True when it downloaded something."""
    import urllib.request

    from huggingface_hub import hf_hub_download
    got = False
    for sub in ("musetalkV15", "sd-vae", "whisper", "dwpose", "syncnet", "face-parse-bisent"):
        os.makedirs(f"{models}/{sub}", exist_ok=True)
    for repo, name, folder in _MUSE_FILES:
        dest = f"{models}/{folder}/{name}" if folder else f"{models}/{name}"
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            continue
        hf_hub_download(repo, name, local_dir=f"{models}/{folder}" if folder else models, token=os.environ.get("HF_TOKEN") or None)
        got = True
    parse = f"{models}/face-parse-bisent/79999_iter.pth"
    if not (os.path.exists(parse) and os.path.getsize(parse) > 0):
        import gdown
        gdown.download(id=_FACE_PARSE_GDRIVE, output=parse, quiet=True)
        got = True
    resnet = f"{models}/face-parse-bisent/resnet18-5c106cde.pth"
    if not (os.path.exists(resnet) and os.path.getsize(resnet) > 0):
        urllib.request.urlretrieve(_RESNET18, resnet)
        got = True
    missing = [n for _, n, f in _MUSE_FILES if not os.path.exists(f"{models}/{f}/{n}" if f else f"{models}/{n}")]
    missing += [os.path.basename(x) for x in (parse, resnet) if not (os.path.exists(x) and os.path.getsize(x) > 0)]
    if missing:
        raise RuntimeError("MuseTalk weights missing after download: " + ", ".join(missing))
    return got

@app.cls(gpu=GPU, image=face_image, volumes={MODELS_DIR: volume}, secrets=[secret], scaledown_window=IDLE, timeout=1800)
class Face:
    """Lab wrapper around MuseTalk's own real-time script. It reloads the weights on every call (slow, fine for the
    lab); Phase 3 replaces it with an in-process engine that keeps them warm and streams frames."""

    @modal.enter()
    def setup(self):
        for k in ("musetalk", "sd_vae", "whisper_tiny", "dwpose", "face_parse_bisenet"):
            registry.check(k, "lab")
        for name, sub in (("models", "musetalk_models"), ("results", "musetalk_results")):
            target = f"{MODELS_DIR}/{sub}"
            os.makedirs(target, exist_ok=True)
            link = f"{MUSE_DIR}/{name}"
            if os.path.islink(link) or not os.path.exists(link):
                if os.path.islink(link):
                    os.unlink(link)
                os.symlink(target, link)
        if _fetch_muse_weights(f"{MUSE_DIR}/models"):
            volume.commit()
        self.commit = open(f"{MUSE_DIR}/COMMIT").read().strip()[:12]

    def _run(self, avatar_id: str, video: str, preparation: bool, clips: dict) -> float:
        import yaml
        cfg = f"/tmp/{uuid.uuid4().hex}.yaml"
        with open(cfg, "w") as f:
            yaml.safe_dump({avatar_id: {"preparation": preparation, "bbox_shift": 0, "video_path": video,
                                        "audio_clips": clips}}, f)
        t = time.time()
        r = subprocess.run(["python", "-m", "scripts.realtime_inference", "--inference_config", cfg, "--version", "v15",
                            "--unet_model_path", "models/musetalkV15/unet.pth",
                            "--unet_config", "models/musetalkV15/musetalk.json", "--fps", "25"],
                           cwd=MUSE_DIR, stdin=subprocess.DEVNULL, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError("MuseTalk failed: " + (r.stderr or r.stdout)[-1500:])
        return round(time.time() - t, 1)

    @modal.method()
    def prepare(self, avatar_id: str, video: bytes, consent: str) -> dict:
        if not AVATAR_ID.match(avatar_id or ""):
            raise ValueError("avatar_id: lower-case letters, digits, - and _ (max 40)")
        if not CONSENT.match(consent or ""):
            raise ValueError("consent must be 'ai_generated' or 'signed:<record id>' - no face without it")
        if not video or len(video) > MAX_FACE_VIDEO:
            raise ValueError("reference video missing or over 30 MB")
        src_dir = f"{MODELS_DIR}/avatar_src"
        os.makedirs(src_dir, exist_ok=True)
        raw, src = _tmp(video, ".mp4"), f"{src_dir}/{avatar_id}.mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-r", "25", src], check=True)   # MuseTalk is trained at 25 fps
        shutil.rmtree(f"{MUSE_DIR}/results/v15/avatars/{avatar_id}", ignore_errors=True)        # the script would ask y/n
        secs = self._run(avatar_id, src, True, {})
        with open(f"{src_dir}/{avatar_id}.consent", "w") as f:
            f.write(consent)
        volume.commit()
        return {"avatar_id": avatar_id, "prepare_s": secs, "musetalk_commit": self.commit}

    @modal.method()
    def speak(self, avatar_id: str, audio: bytes) -> dict:
        if not AVATAR_ID.match(avatar_id or "") or not os.path.exists(f"{MODELS_DIR}/avatar_src/{avatar_id}.consent"):
            raise ValueError("unknown avatar (prepare it first, with consent)")
        if not audio or len(audio) > MAX_SPEAK_AUDIO:
            raise ValueError("audio missing or over 8 MB")
        clip = "c" + uuid.uuid4().hex[:10]
        wav = _tmp(audio, ".wav")
        secs = self._run(avatar_id, f"{MODELS_DIR}/avatar_src/{avatar_id}.mp4", False, {clip: wav})
        out = f"{MUSE_DIR}/results/v15/avatars/{avatar_id}/vid_output/{clip}.mp4"
        with open(out, "rb") as f:
            data = f.read()
        os.remove(out)
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", wav],
                                   capture_output=True, text=True).stdout.strip() or 0)
        return {"mp4": data, "render_s": secs, "audio_s": round(dur, 2),
                "x_realtime": round(secs / dur, 2) if dur else None, "musetalk_commit": self.commit}

    @modal.method()
    def forget(self, avatar_id: str) -> dict:
        if not AVATAR_ID.match(avatar_id or ""):
            raise ValueError("bad avatar_id")
        for p in (f"{MODELS_DIR}/avatar_src/{avatar_id}.mp4", f"{MODELS_DIR}/avatar_src/{avatar_id}.consent"):
            if os.path.exists(p):
                os.remove(p)
        shutil.rmtree(f"{MUSE_DIR}/results/v15/avatars/{avatar_id}", ignore_errors=True)
        volume.commit()
        return {"forgotten": avatar_id}


# ---------------------------------------------------------------- the locked web endpoint (Hoola server -> lab)
@app.function(image=web_image, secrets=[secret], timeout=1800)
@modal.asgi_app()
def web():
    import hmac

    from fastapi import Depends, FastAPI, Header, HTTPException
    from fastapi.responses import Response

    api = FastAPI(title="Hoola Interactive Model Lab")

    def key(authorization: str = Header(default="")):
        want = os.environ.get("ENGINE_KEY", "")
        got = authorization.removeprefix("Bearer ").strip()
        if not want or not hmac.compare_digest(got, want):     # no key configured = locked, never open
            raise HTTPException(401, "locked")

    def b64(v, cap, name):
        if not v:
            return None
        try:
            data = base64.b64decode(v, validate=True)
        except Exception:
            raise HTTPException(400, f"{name}: not base64")
        if len(data) > cap:
            raise HTTPException(413, f"{name}: too large")
        return data

    @api.get("/health", dependencies=[Depends(key)])
    def health():
        return {"ok": True, "gpu": GPU, "models": registry.public()}

    @api.post("/voice", dependencies=[Depends(key)])
    def voice(body: dict):
        m = str(body.get("model") or "chatterbox")
        try:
            registry.check(m, "lab")
        except registry.Refused as e:
            raise HTTPException(403, str(e))
        if m not in VOICES:
            raise HTTPException(400, "not a voice model")
        text = str(body.get("text") or "").strip()
        if not text or len(text) > MAX_TEXT:
            raise HTTPException(400, f"text: 1-{MAX_TEXT} characters")
        r = VOICES[m]().speak.remote(text=text, lang=str(body.get("lang") or "hi")[:5],
                                     ref_audio=b64(body.get("ref_audio_b64"), MAX_REF_AUDIO, "ref_audio_b64"),
                                     ref_text=str(body.get("ref_text") or "")[:400],
                                     description=str(body.get("description") or "")[:400])
        return Response(r["wav"], media_type="audio/wav",
                        headers={"X-Synth-Seconds": str(r["synth_s"]), "X-Load-Seconds": str(r["load_s"])})

    @api.post("/face/prepare", dependencies=[Depends(key)])
    def face_prepare(body: dict):
        try:
            return Face().prepare.remote(str(body.get("avatar_id") or ""), b64(body.get("video_b64"), MAX_FACE_VIDEO, "video_b64"),
                                         str(body.get("consent") or ""))
        except ValueError as e:
            raise HTTPException(400, str(e))

    @api.post("/face/speak", dependencies=[Depends(key)])
    def face_speak(body: dict):
        try:
            r = Face().speak.remote(str(body.get("avatar_id") or ""), b64(body.get("audio_b64"), MAX_SPEAK_AUDIO, "audio_b64"))
        except ValueError as e:
            raise HTTPException(400, str(e))
        return Response(r["mp4"], media_type="video/mp4",
                        headers={"X-Render-Seconds": str(r["render_s"]), "X-Times-Realtime": str(r["x_realtime"])})

    @api.post("/face/forget", dependencies=[Depends(key)])
    def face_forget(body: dict):
        return Face().forget.remote(str(body.get("avatar_id") or ""))

    return api


# ---------------------------------------------------------------- lab jobs (run from the workflow)
@app.function(image=chatterbox_image, volumes={MODELS_DIR: volume}, secrets=[secret], timeout=3600)
def _prefetch_hf(repos: list[str]) -> dict:
    from huggingface_hub import snapshot_download
    done, failed = [], {}
    for repo in repos:
        try:   # a gated or missing model must not stop the others
            snapshot_download(repo, token=os.environ.get("HF_TOKEN") or None)
            done.append(repo)
        except Exception as e:
            failed[repo] = f"{type(e).__name__}: {str(e)[:160]}"
    volume.commit()
    return {"done": done, "failed": failed}


@app.local_entrypoint()
def prefetch():
    """Download every lab-allowed voice model's weights into the volume (no GPU). The face weights download on the
    face container's first start, through MuseTalk's own script."""
    repos = [registry.MODELS[k]["repo"] for k in registry.voices("lab")]
    print("downloading:", repos)
    r = _prefetch_hf.remote(repos)
    print("downloaded:", r["done"])
    for repo, why in r["failed"].items():
        print(f"FAILED {repo}: {why}")
        if "gated" in why.lower() or "403" in why or "401" in why:
            print(f"  -> open https://huggingface.co/{repo} while logged in, accept the terms, then run prefetch again")
    if not r["done"]:
        raise SystemExit("No model could be downloaded.")


def _call(label: str, method, *args, wait: int = 600, **kw):
    """Run one remote call with a hard wait, so one hung model costs `wait` seconds and not the whole run."""
    t = time.time()
    print(f"[{time.strftime('%H:%M:%S')}] {label}: start (waiting up to {wait}s)", flush=True)
    fc = method.spawn(*args, **kw)
    try:
        out = fc.get(timeout=wait)
    except Exception:
        try:
            fc.cancel()
        except Exception:
            pass
        print(f"[{time.strftime('%H:%M:%S')}] {label}: gave up after {round(time.time() - t)}s", flush=True)
        raise
    print(f"[{time.strftime('%H:%M:%S')}] {label}: done in {round(time.time() - t)}s", flush=True)
    return out


@app.local_entrypoint()
def smoke():
    """One Hindi and one English line per voice model, then one talking clip from MuseTalk's own sample face (lab
    only, never shipped). Files + a timing table land in ./lab_out for the workflow to upload; the report is rewritten
    after every row, so a cancelled run still keeps what finished."""
    os.makedirs("lab_out", exist_ok=True)
    lines = {"hi": "नमस्ते आरव! आज हम सीखेंगे कि ग्राफ से गति कैसे दिखती है।",
             "en": "Hello Aarav! Today we will see how a simple graph can show motion."}
    rows: list[str] = []

    def note(row: str) -> None:
        rows.append(row)
        print(row, flush=True)
        with open("lab_out/REPORT.txt", "w") as f:
            f.write(f"GPU {GPU}\n" + "\n".join(rows) + "\n")

    for name, cls in VOICES.items():
        for lang, text in lines.items():
            if lang not in (registry.MODELS[name].get("langs") or []):
                continue
            try:
                r = _call(f"{name} {lang}", cls().speak, text=text, lang=lang, wait=900)
                with open(f"lab_out/{name}_{lang}.wav", "wb") as f:
                    f.write(r["wav"])
                note(f"{name:13} {lang}  load {r['load_s']}s  synth {r['synth_s']}s  OK")
            except Exception as e:   # one broken model must not hide the others' results
                note(f"{name:13} {lang}  FAILED: {type(e).__name__} {str(e)[:200]}")
    try:
        sample = _call("face prepare", Face().prepare, "lab-sample", _sample_face.remote(), "ai_generated", wait=1500)
        hi = open("lab_out/chatterbox_hi.wav", "rb").read() if os.path.exists("lab_out/chatterbox_hi.wav") else None
        if hi:
            r = _call("face speak", Face().speak, "lab-sample", hi, wait=1200)
            with open("lab_out/face_hi.mp4", "wb") as f:
                f.write(r["mp4"])
            note(f"face          hi  prepare {sample['prepare_s']}s  render {r['render_s']}s for {r['audio_s']}s audio "
                 f"= {r['x_realtime']}x real time  (MuseTalk {r['musetalk_commit']})")
        else:
            note("face          hi  SKIPPED: no Chatterbox Hindi clip to drive it")
        Face().forget.remote("lab-sample")
    except Exception as e:
        note(f"face              FAILED: {type(e).__name__} {str(e)[:300]}")


@app.function(image=face_image, timeout=300)
def _sample_face() -> bytes:
    """MuseTalk's own demo clip (shipped in its MIT repo) - a lab stand-in until our consented / AI-made face exists."""
    with open(f"{MUSE_DIR}/data/video/yongen.mp4", "rb") as f:
        return f.read()
