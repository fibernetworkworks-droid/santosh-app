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
import json
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
WARM = int(os.environ.get("HOOLA_LAB_WARM", "0"))      # containers kept running (0 = scale to zero); 1 = a teacher mid-lesson never meets a cold start
VOICE_WARM = int(os.environ.get("HOOLA_LAB_VOICES", "3" if WARM else "0"))   # voice containers kept warm (one per early chunk: two chunks sharing a card each ran ~30 % slower): chunks 2, 3... are made at the SAME time as chunk 1 on the others
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
# Chatterbox 0.1.7 stops a sentence the moment ANY two identical speech tokens come in a row (its own comment says "3x";
# the code checks 2, and the "only after the text is spoken" condition is commented out) - a held vowel is two identical
# tokens, so words were cut off mid-sentence ("Detected 2x repetition ... forcing EOS" in the studio card log). Patched at
# build time to what the comment meant: 4 in a row, and only once the whole text has been spoken. Build fails if the
# line it patches ever changes.
CB_PATCH = r"""
import importlib.util, pathlib
p = pathlib.Path(importlib.util.find_spec("chatterbox").submodule_search_locations[0]) / "models/t3/inference/alignment_stream_analyzer.py"
s = p.read_text()
old = "len(self.generated_tokens) >= 3 and\n            len(set(self.generated_tokens[-2:])) == 1"
new = "self.complete and len(self.generated_tokens) >= 4 and\n            len(set(self.generated_tokens[-4:])) == 1"
assert s.count(old) == 1, "chatterbox repetition check changed - re-read it before patching"
p.write_text(s.replace(old, new))
print("chatterbox repetition guard patched")
"""
chatterbox_image = (_base.pip_install("chatterbox-tts==0.1.7", "soundfile", "huggingface_hub")
                    # one line: a build step is a single Dockerfile RUN, so the script travels base64-encoded
                    .run_commands(f"echo {base64.b64encode(CB_PATCH.encode()).decode()} | base64 -d | python")
                    .add_local_python_source("registry"))
indicf5_image = (_base.pip_install("git+https://github.com/ai4bharat/IndicF5.git", "soundfile", "huggingface_hub")
                 # newest `datasets` needs pyarrow>=24, which needs NumPy 2; this stack is on NumPy 1.26 -> pin a matching pair
                 .pip_install("pyarrow==16.1.0", "datasets==2.21.0")
                 # IndicF5's own requirements.txt says transformers<4.50; newer builds remote-code models on the `meta`
                 # device and vocos / torchaudio then fail with "Tensor on device cpu is not on the expected device meta"
                 .pip_install("transformers==4.49.0", "huggingface_hub<1.0")
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
        # last: NumPy must stay on 1.x (a later install had pulled NumPy 2, which cv2 cannot load) but matplotlib needs
        # >=1.25 on Python 3.11, so not MuseTalk's 1.23.5; hub pinned to what its requirements.txt uses
        "pip install 'numpy==1.26.4' 'huggingface_hub==0.30.2'",
    )
    .env(HF_ENV)
    .add_local_python_source("registry")
)
hear_image = (modal.Image.debian_slim(python_version="3.11").apt_install("ffmpeg")
              .pip_install("faster-whisper==1.1.0", "requests", "huggingface_hub").add_local_python_source("registry"))
studio_image = modal.Image.debian_slim(python_version="3.11").apt_install("ffmpeg").add_local_python_source("registry")
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


def _take_off(secs: float, words: int) -> float:
    """How far a voice take is from the normal length of `words` Hindi words (about 0.45 s a word)."""
    return abs(secs - max(0.6, words * 0.45))


def _tmp(data: bytes | None, suffix: str) -> str | None:
    if not data:
        return None
    p = f"/tmp/{uuid.uuid4().hex}{suffix}"
    with open(p, "wb") as f:
        f.write(data)
    return p


# ---------------------------------------------------------------- voice engines
@app.cls(gpu=GPU, image=chatterbox_image, volumes={MODELS_DIR: volume}, secrets=[secret], scaledown_window=IDLE, timeout=600,
         min_containers=VOICE_WARM, max_containers=4)
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
    def save_voice(self, voice_id: str, wav: bytes, consent: str) -> dict:
        """My Voice: keep ONE recorded reference clip of a person who agreed (consent = 'signed:<record id>'). Cloning a
        voice that is not hers is exactly what the consent tag exists to stop."""
        if not AVATAR_ID.match(voice_id or ""):
            raise ValueError("voice_id: lower-case letters, digits, - and _ (max 40)")
        if not re.match(r"^signed:[A-Za-z0-9_-]{4,64}$", consent or ""):
            raise ValueError("a cloned voice needs consent 'signed:<record id>' - the person must have agreed")
        if not wav or len(wav) > MAX_SPEAK_AUDIO:
            raise ValueError("voice sample missing or over 8 MB")
        os.makedirs(f"{MODELS_DIR}/voices", exist_ok=True)
        with open(f"{MODELS_DIR}/voices/{voice_id}.wav", "wb") as f:
            f.write(wav)
        with open(f"{MODELS_DIR}/voices/{voice_id}.consent", "w") as f:
            f.write(consent)
        volume.commit()
        return {"voice_id": voice_id, "bytes": len(wav)}

    @modal.method()
    def delete_voice(self, voice_id: str) -> dict:
        if not AVATAR_ID.match(voice_id or ""):
            raise ValueError("bad voice_id")
        for ext in (".wav", ".consent"):
            pth = f"{MODELS_DIR}/voices/{voice_id}{ext}"
            if os.path.exists(pth):
                os.remove(pth)
        volume.commit()
        return {"deleted": voice_id}

    def _voice_ref(self, voice_id: str):
        path = f"{MODELS_DIR}/voices/{voice_id}.wav"
        if not os.path.exists(path):
            volume.reload()
        if not os.path.exists(path):
            raise ValueError(f"voice '{voice_id}' is not saved")
        with open(path, "rb") as f:
            return f.read()

    @modal.method()
    def speak(self, text: str, lang: str = "hi", ref_audio: bytes | None = None, voice_id: str = "", **_) -> dict:
        if voice_id:
            if not AVATAR_ID.match(voice_id):
                raise ValueError("bad voice_id")
            ref_audio = self._voice_ref(voice_id)
        ref = _tmp(ref_audio, ".wav")
        t = time.time()
        # Guard both ways. A line of N words should speak for about N x 0.45 s (Hindi). More than N x 1.0 s + 2.5 s is a
        # runaway (one word once rambled for 12 s); less than N x 0.22 s means the voice stopped early and dropped words.
        # Either one is made again (max 3 takes); the take closest to the normal length is kept.
        n = len(text.split())
        limit, floor = n * 1.0 + 2.5, n * 0.22
        best, tries = None, 0
        for _ in range(3):
            tries += 1
            w = self.model.generate(text, language_id=lang, **({"audio_prompt_path": ref} if ref else {}))
            peak = float(w.abs().max()) or 1.0                       # cut the silent tail the sampler leaves after the last word (keep 0.2 s)
            loud = (w.abs() > 0.02 * peak).nonzero()
            if loud.numel():
                w = w[..., : min(w.shape[-1], int(loud[:, -1].max()) + int(0.2 * self.model.sr))]
            secs = w.shape[-1] / self.model.sr
            if best is None or _take_off(secs, n) < _take_off(best[1], n):
                best = (w, secs)
            if floor <= secs <= limit:
                break
        wav, secs = best
        out = _wav_bytes(wav, self.model.sr)
        return {"wav": out, "sr": self.model.sr, "synth_s": round(time.time() - t, 2), "load_s": self.load_s,
                "tries": tries, "runaway": secs > limit, "cut_short": secs < floor}


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

# Run INSIDE the face container (cwd = MuseTalk). It imports MuseTalk's own realtime script as a module, fills in the
# globals its Avatar class reads (the script normally builds them under __main__), loads every model ONCE, then times the
# same clip again and again at several batch sizes. That is the steady-state speed the one-process-per-call lab path hides.
_BENCH_SCRIPT = """
import argparse, json, os, shutil, subprocess, time
from types import SimpleNamespace
import torch
from transformers import WhisperModel
from musetalk.utils.audio_processor import AudioProcessor
from musetalk.utils.face_parsing import FaceParsing
from musetalk.utils.utils import load_all_model
from scripts import realtime_inference as rt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video"); ap.add_argument("--audio"); ap.add_argument("--out")
    ap.add_argument("--batches", default="4,8,20"); ap.add_argument("--timed", type=int, default=2)
    a = ap.parse_args()
    rt.args = SimpleNamespace(version="v15", extra_margin=10, parsing_mode="jaw", skip_save_images=True,
                              audio_padding_length_left=2, audio_padding_length_right=2)
    t0 = time.time()
    device = torch.device("cuda:0")
    vae, unet, pe = load_all_model(unet_model_path="models/musetalkV15/unet.pth", vae_type="sd-vae",
                                   unet_config="models/musetalkV15/musetalk.json", device=device)
    rt.timesteps = torch.tensor([0], device=device)
    pe = pe.half().to(device)
    vae.vae = vae.vae.half().to(device)
    unet.model = unet.model.half().to(device)
    rt.audio_processor = AudioProcessor(feature_extractor_path="models/whisper")
    rt.weight_dtype = unet.model.dtype
    whisper = WhisperModel.from_pretrained("models/whisper").to(device=device, dtype=rt.weight_dtype).eval()
    whisper.requires_grad_(False)
    rt.fp = FaceParsing(left_cheek_width=90, right_cheek_width=90)
    rt.device, rt.vae, rt.unet, rt.pe, rt.whisper = device, vae, unet, pe, whisper
    load_s = round(time.time() - t0, 1)

    shutil.rmtree("results/v15/avatars/bench", ignore_errors=True)
    t1 = time.time()
    av = rt.Avatar(avatar_id="bench", video_path=a.video, bbox_shift=0, batch_size=20, preparation=True)
    prepare_s = round(time.time() - t1, 1)
    audio_s = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.audio],
                                   capture_output=True, text=True).stdout.strip() or 0)
    frames = round(audio_s * 25)
    rows = []
    for b in [int(x) for x in a.batches.split(",")]:
        av.batch_size = b
        for i in range(1 + a.timed):                 # the first pass of each size is a warm-up and is not counted
            torch.cuda.synchronize()
            t = time.time()
            av.inference(a.audio, None, 25, True)
            torch.cuda.synchronize()
            dt = time.time() - t
            if i == 0:
                continue
            batches = -(-frames // b)
            rows.append({"batch": b, "secs": round(dt, 2), "frames": frames, "fps": round(frames / dt, 1),
                         "x_realtime": round(dt / audio_s, 2), "ms_per_batch": round(dt * 1000 / batches)})
    json.dump({"load_s": load_s, "prepare_s": prepare_s, "audio_s": round(audio_s, 2), "frames": frames, "rows": rows},
              open(a.out, "w"))


main()
"""


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
        return self._prepare_impl(avatar_id, video, consent)

    def _prepare_impl(self, avatar_id: str, video: bytes, consent: str) -> dict:
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
    def bench(self, audio: bytes, video: bytes) -> dict:
        """Steady-state speed: models loaded once, the same clip timed again and again (see _BENCH_SCRIPT)."""
        raw, wav = _tmp(video, ".mp4"), _tmp(audio, ".wav")
        src = f"/tmp/{uuid.uuid4().hex}_25.mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-r", "25", src], check=True)
        with open(f"{MUSE_DIR}/scripts/hoola_bench.py", "w") as f:
            f.write(_BENCH_SCRIPT)
        out = f"/tmp/{uuid.uuid4().hex}.json"
        r = subprocess.run(["python", "-m", "scripts.hoola_bench", "--video", src, "--audio", wav, "--out", out],
                           cwd=MUSE_DIR, stdin=subprocess.DEVNULL, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError("bench failed: " + (r.stderr or r.stdout)[-1500:])
        with open(out) as f:
            data = json.load(f)
        data["gpu"], data["musetalk_commit"] = GPU, self.commit
        return data

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
# ---------------------------------------------------------------- live face (warm, in-process, streams frames)
@app.cls(gpu=GPU, image=face_image, volumes={MODELS_DIR: volume}, secrets=[secret], scaledown_window=IDLE, timeout=600,
         cpu=4,                     # the CPU half of every frame (blend + JPEG) needs real cores, not Modal's 0.125 default
         min_containers=WARM, max_containers=4)          # ONE student per container (input concurrency stays off): measured, a second student on the same card
                                    # hangs the GPU call AND could never be smooth (~43 fps total < 2 x 25), so Modal adds a card
class Live:
    """The face the way a live teacher needs it: every model loaded ONCE when the container starts, prepared faces kept in
    memory, and `stream` hands back JPEG frames batch by batch as they are made (the lab's Face class starts a new process
    per call). Lab-only until a consented face exists; uses MuseTalk's own Avatar class so the maths is unchanged."""

    @modal.enter()
    def start(self):
        import sys
        import threading
        from types import SimpleNamespace

        import torch
        from transformers import WhisperModel
        for k in ("musetalk", "sd_vae", "whisper_tiny", "dwpose", "face_parse_bisenet"):
            registry.check(k, "lab")
        for name, sub in (("models", "musetalk_models"), ("results", "musetalk_results")):
            target = f"{MODELS_DIR}/{sub}"
            os.makedirs(target, exist_ok=True)
            link = f"{MUSE_DIR}/{name}"
            if os.path.islink(link):
                os.unlink(link)
            if not os.path.exists(link):
                os.symlink(target, link)
        if _fetch_muse_weights(f"{MUSE_DIR}/models"):
            volume.commit()
        os.chdir(MUSE_DIR)
        sys.path.insert(0, MUSE_DIR)
        from musetalk.utils.audio_processor import AudioProcessor
        from musetalk.utils.face_parsing import FaceParsing
        from musetalk.utils.utils import load_all_model
        from scripts import realtime_inference as rt
        t = time.time()
        rt.args = SimpleNamespace(version="v15", extra_margin=10, parsing_mode="jaw", skip_save_images=True,
                                  audio_padding_length_left=2, audio_padding_length_right=2)
        device = torch.device("cuda:0")
        vae, unet, pe = load_all_model(unet_model_path="models/musetalkV15/unet.pth", vae_type="sd-vae",
                                       unet_config="models/musetalkV15/musetalk.json", device=device)
        rt.timesteps = torch.tensor([0], device=device)
        pe = pe.half().to(device)
        vae.vae = vae.vae.half().to(device)
        unet.model = unet.model.half().to(device)
        rt.audio_processor = AudioProcessor(feature_extractor_path="models/whisper")
        rt.weight_dtype = unet.model.dtype
        whisper = WhisperModel.from_pretrained("models/whisper").to(device=device, dtype=rt.weight_dtype).eval()
        whisper.requires_grad_(False)
        rt.fp = FaceParsing(left_cheek_width=90, right_cheek_width=90)
        rt.device, rt.vae, rt.unet, rt.pe, rt.whisper = device, vae, unet, pe, whisper
        import faulthandler

        import cv2
        from concurrent.futures import ThreadPoolExecutor
        cv2.setNumThreads(1)       # we run our own threads; OpenCV's inner pool on top of them is a classic stall / oversubscription
        faulthandler.enable()
        faulthandler.dump_traceback_later(240, repeat=True)   # a hang must show WHERE every thread is stuck, in the logs
        self.pool = ThreadPoolExecutor(max_workers=6)      # CPU half of the frames, shared by every stream
        self.rt, self.torch = rt, torch
        self.avatars: dict = {}
        self.lock = threading.Lock()
        self.load_s = round(time.time() - t, 1)
        self.commit = open(f"{MUSE_DIR}/COMMIT").read().strip()[:12]

    @modal.method()
    def prepare(self, avatar_id: str, video: bytes, consent: str) -> dict:
        return self._prepare_impl(avatar_id, video, consent)

    def _prepare_impl(self, avatar_id: str, video: bytes, consent: str) -> dict:
        """Shared by prepare (a recorded clip) and prepare_photo (a still made into a clip): same consent rules."""
        if not AVATAR_ID.match(avatar_id or ""):
            raise ValueError("avatar_id: lower-case letters, digits, - and _ (max 40)")
        if not CONSENT.match(consent or ""):
            raise ValueError("consent must be 'ai_generated' or 'signed:<record id>' - no face without it")
        if not video or len(video) > MAX_FACE_VIDEO:
            raise ValueError("reference video missing or over 30 MB")
        with self.lock:
            if avatar_id in self.avatars:
                return {"avatar_id": avatar_id, "prepare_s": 0.0, "cached": True, "load_s": self.load_s}
            raw = _tmp(video, ".mp4")
            src = f"/tmp/{uuid.uuid4().hex}_25.mp4"
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-r", "25", src], check=True)
            shutil.rmtree(f"{MUSE_DIR}/results/v15/avatars/{avatar_id}", ignore_errors=True)   # the script would ask y/n
            t = time.time()
            self.avatars[avatar_id] = self.rt.Avatar(avatar_id=avatar_id, video_path=src, bbox_shift=0,
                                                     batch_size=8, preparation=True)
            volume.commit()      # results/ is the volume: any container that starts later can load this face in seconds
            return {"avatar_id": avatar_id, "prepare_s": round(time.time() - t, 1), "cached": False, "load_s": self.load_s}

    def _avatar(self, avatar_id: str):
        """The prepared face: from memory, else from the volume (a fresh container for a second student)."""
        av = self.avatars.get(avatar_id)
        if av is not None:
            return av
        with self.lock:
            av = self.avatars.get(avatar_id)
            if av is None:
                try:
                    volume.reload()
                except Exception:
                    pass
                if not AVATAR_ID.match(avatar_id or "") or not os.path.exists(
                        f"{MUSE_DIR}/results/v15/avatars/{avatar_id}/latents.pt"):
                    raise ValueError("unknown avatar (prepare it first, with consent)")
                av = self.rt.Avatar(avatar_id=avatar_id, video_path="", bbox_shift=0, batch_size=8, preparation=False)
                self.avatars[avatar_id] = av
        return av

    @modal.method()
    def stream(self, avatar_id: str, audio: bytes, batch: int = 8, loops: int = 1):
        yield from self._frames(avatar_id, audio, batch, loops)

    @modal.method()
    def prepare_photo(self, avatar_id: str, photo: bytes, consent: str) -> dict:
        """Photo avatar: one still picture becomes a 6 s 25 fps clip and is prepared like a recorded face. The mouth
        moves, the head does not (MuseTalk only repaints the mouth area)."""
        if not photo or len(photo) > 10 * 1024 * 1024:
            raise ValueError("photo missing or over 10 MB")
        src = _tmp(photo, ".img")
        out = f"/tmp/{uuid.uuid4().hex}_photo.mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", src, "-t", "6", "-r", "25",
                        "-vf", "scale='min(768,iw)':-2,pad=ceil(iw/2)*2:ceil(ih/2)*2,format=yuv420p",
                        "-c:v", "libx264", out], check=True)
        with open(out, "rb") as f:
            video = f.read()
        return self._prepare_impl(avatar_id, video, consent)

    @modal.method()
    def render(self, avatar_id: str, audio: bytes) -> bytes:
        """Not live: the whole speech as one MP4 (picture from the face, sound from `audio`)."""
        d = f"/tmp/{uuid.uuid4().hex}"
        os.makedirs(d)
        n = 0
        for b in self._frames(avatar_id, audio, 8, 1):
            for jpg in b["frames"]:
                with open(f"{d}/{n:06d}.jpg", "wb") as f:
                    f.write(jpg)
                n += 1
        if not n:
            raise ValueError("no pictures were made")
        wav = _tmp(audio, ".wav")
        out = f"{d}.mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", "25", "-i", f"{d}/%06d.jpg", "-i", wav,
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", out], check=True)
        with open(out, "rb") as f:
            data = f.read()
        shutil.rmtree(d, ignore_errors=True)
        return data

    @modal.method()
    def forget(self, avatar_id: str) -> dict:
        if not AVATAR_ID.match(avatar_id or ""):
            raise ValueError("bad avatar_id")
        with self.lock:
            self.avatars.pop(avatar_id, None)
        shutil.rmtree(f"{MUSE_DIR}/results/v15/avatars/{avatar_id}", ignore_errors=True)
        volume.commit()
        return {"forgotten": avatar_id}

    def _frames(self, avatar_id: str, audio: bytes, batch: int = 8, loops: int = 1):
        """Generator: yields {first, frames:[jpeg bytes], ready_s, audio_prep_s}. `ready_s` = seconds since this call began
        when that batch was finished; the caller turns it into stalls against a 25 fps playhead."""
        import copy

        import cv2
        import numpy as np
        from musetalk.utils.blending import get_image_blending
        from musetalk.utils.utils import datagen
        av = self._avatar(avatar_id)
        if not audio or len(audio) > MAX_SPEAK_AUDIO:
            raise ValueError("audio missing or over 8 MB")
        if not 1 <= int(batch) <= 32 or not 1 <= int(loops) <= 8:
            raise ValueError("batch 1-32, loops 1-8")
        rt, torch = self.rt, self.torch
        wav = _tmp(audio, ".wav")
        if int(loops) > 1:   # a longer clip to show sustained speed (the same speech repeated)
            long_wav = f"/tmp/{uuid.uuid4().hex}.wav"
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-stream_loop", str(int(loops) - 1), "-i", wav, "-c", "copy", long_wav],
                           check=True)
            wav = long_wav
        t0 = time.time()
        n = len(av.coord_list_cycle)
        idx = 0
        with torch.no_grad():
            feats, length = rt.audio_processor.get_audio_feature(wav, weight_dtype=rt.weight_dtype)
            chunks = rt.audio_processor.get_whisper_chunk(feats, rt.device, rt.weight_dtype, rt.whisper, length, fps=25,
                                                          audio_padding_length_left=2, audio_padding_length_right=2)
            prep = round(time.time() - t0, 2)
            def finish(res, i):
                """The CPU half of one frame: put the new mouth back into the full picture, then JPEG it."""
                x1, y1, x2, y2 = av.coord_list_cycle[i % n]
                res = cv2.resize(res.astype(np.uint8), (x2 - x1, y2 - y1))
                frame = get_image_blending(copy.deepcopy(av.frame_list_cycle[i % len(av.frame_list_cycle)]), res,
                                           [x1, y1, x2, y2], av.mask_list_cycle[i % len(av.mask_list_cycle)],
                                           av.mask_coords_list_cycle[i % len(av.mask_coords_list_cycle)])
                return cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])[1].tobytes()

            def out_of(pend):
                return {"first": pend[0], "frames": [f.result() for f in pend[1]], "ready_s": round(time.time() - t0, 3),
                        "audio_prep_s": prep}

            pending = None      # the previous batch: its CPU work runs on the pool while the GPU makes the next one
            for wb, lb in datagen(chunks, av.input_latent_list_cycle, int(batch)):
                af = rt.pe(wb.to(rt.device))
                lb = lb.to(device=rt.device, dtype=rt.unet.model.dtype)
                pred = rt.unet.model(lb, rt.timesteps, encoder_hidden_states=af).sample.to(device=rt.device, dtype=rt.vae.vae.dtype)
                recon = list(rt.vae.decode_latents(pred))
                cur = (idx, [self.pool.submit(finish, r, idx + k) for k, r in enumerate(recon)])
                idx += len(recon)
                if pending is not None:
                    yield out_of(pending)
                pending = cur
            if pending is not None:
                yield out_of(pending)


@app.function(image=web_image, secrets=[secret], timeout=1800)
@modal.asgi_app()
def web():
    import hmac

    from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket
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

    BYTES_IN = {"photo": 10 * 1024 * 1024, "wav": MAX_SPEAK_AUDIO, "media": MAX_FACE_VIDEO, "video": MAX_FACE_VIDEO}

    @api.post("/studio/{op}", dependencies=[Depends(key)])
    def studio_start(op: str, body: dict):
        """Start a Studio job (video / photo_face / voice_save / transcribe / dub / podcast / personalised). Returns a job id;
        the work takes seconds to minutes, so the caller polls GET /studio/job/<id>."""
        if op not in STUDIO_OPS:
            raise HTTPException(404, "unknown studio op")
        p = dict(body)
        for k, cap in BYTES_IN.items():
            if k in p:
                p[k] = b64(p[k], cap, k)
        fc = studio_job.spawn(op, p)
        return {"job": fc.object_id}

    @api.get("/studio/job/{job_id}", dependencies=[Depends(key)])
    def studio_poll(job_id: str):
        import modal as _m
        try:
            fc = _m.FunctionCall.from_id(job_id)
            r = fc.get(timeout=0)
        except TimeoutError:
            return {"state": "running"}
        except ValueError as e:                         # our own checks (consent, size, text length): safe and useful to show
            return {"state": "failed", "error": str(e)[:300]}
        except Exception as e:
            print("studio job:", type(e).__name__, str(e)[:300], flush=True)
            return {"state": "failed", "error": "the job failed - check the engine log"}
        files = {k: base64.b64encode(v if isinstance(v, bytes) else str(v).encode()).decode() for k, v in (r.get("files") or {}).items()}
        return {"state": "done", "info": r.get("info") or {}, "files": files}

    async def live_socket(ws):
        """One student, one live talk. The browser sends ONE json line {key, avatar_id, text, lang} (the key travels
        in the message, never in the address), then receives: json status lines, and binary frames
        [type u8][chunk u16][index u32][payload]: type 2 = a WAV chunk, type 1 = a JPEG picture of that chunk (25 fps).
        Voice for every chunk starts at once on the warm voice containers; the face is made chunk by chunk."""
        import asyncio
        import struct

        await ws.accept()
        gone = False

        async def say(**m):
            nonlocal gone
            if not gone:
                try:
                    await ws.send_text(json.dumps(m))
                except Exception:
                    gone = True

        async def push(kind: int, k: int, i: int, data: bytes):
            nonlocal gone
            if not gone:
                try:
                    await ws.send_bytes(struct.pack(">BHI", kind, k, i) + data)
                except Exception:
                    gone = True

        tasks: list = []
        try:
            hello = json.loads(await asyncio.wait_for(ws.receive_text(), 15))
            want = os.environ.get("ENGINE_KEY", "")
            avatar = str(hello.get("avatar_id") or "")
            ok = bool(want) and (hmac.compare_digest(str(hello.get("key") or ""), want)
                                 or _ticket_ok(str(hello.get("ticket") or ""), avatar, want))
            if not ok:
                await say(type="error", msg="locked")
                return
            text = str(hello.get("text") or "").strip()
            if not AVATAR_ID.match(avatar) or not text or len(text) > MAX_TEXT:
                await say(type="error", msg=f"avatar_id or text (1-{MAX_TEXT} characters) is not valid")
                return
            chunks = split_speech(text)
            lang = str(hello.get("lang") or "hi")[:5]
            await say(type="start", fps=25, chunks=len(chunks))
            voice, face = Chatterbox(), Live()
            tasks = [asyncio.create_task(voice.speak.remote.aio(c, lang)) for c in chunks]
            for k, t in enumerate(tasks):
                r = await asyncio.wait_for(t, 180)
                await push(2, k, 0, r["wav"])
                n = 0
                # The stream is ALWAYS read to its end, even if the student left: cancelling a Modal call restarts its
                # container (a cold start for the next student). A gone student just stops being sent to.
                async for b in face.stream.remote_gen.aio(avatar, r["wav"], 8, 1):
                    for jpg in b["frames"]:
                        await push(1, k, n, jpg)
                        n += 1
                await say(type="chunk_done", id=k, frames=n)
            await say(type="end")
        except Exception as e:                          # never show internals to the browser
            print("live socket:", type(e).__name__, str(e)[:300], flush=True)
            await say(type="error", msg="the live talk stopped - try again")
        finally:
            for t in tasks:                              # voice calls are NOT cancelled (same restart rule): let them finish
                if not t.done():
                    t.add_done_callback(lambda f: f.exception())
            try:
                await ws.close()
            except Exception:
                pass

    live_socket.__annotations__ = {"ws": WebSocket}      # this file uses postponed annotations: FastAPI could not find a name imported inside web()
    api.websocket("/live")(live_socket)

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


@app.local_entrypoint()
def smoke_face():
    """The face alone: prepare MuseTalk's sample face, then render it speaking MuseTalk's sample audio. The first start
    of this image is the slow one (big image + ~5 GB of weights), so the waits are long; the report is written first."""
    os.makedirs("lab_out", exist_ok=True)
    rows: list[str] = []

    def note(row: str) -> None:
        rows.append(row)
        print(row, flush=True)
        with open("lab_out/REPORT_face.txt", "w") as f:
            f.write(f"GPU {GPU}\n" + "\n".join(rows) + "\n")

    try:
        sample = _call("face prepare", Face().prepare, "lab-sample", _sample_face.remote(), "ai_generated", wait=2700)
        note(f"face prepare  OK  {sample['prepare_s']}s  (MuseTalk {sample['musetalk_commit']})")
        r = _call("face speak", Face().speak, "lab-sample", _sample_audio.remote(), wait=1500)
        with open("lab_out/face_sample.mp4", "wb") as f:
            f.write(r["mp4"])
        note(f"face speak    OK  render {r['render_s']}s for {r['audio_s']}s audio = {r['x_realtime']}x real time")
        Face().forget.remote("lab-sample")
    except Exception as e:
        note(f"face          FAILED: {type(e).__name__} {str(e)[:300]}")


@app.local_entrypoint()
def bench_face():
    """How fast is the face once it is warm? One run, models loaded once, three batch sizes. Real time needs
    x_realtime <= 1.0 (>= 25 frames a second); ms_per_batch is the wait before the first frames of a live answer."""
    os.makedirs("lab_out", exist_ok=True)
    try:
        d = _call("face bench", Face().bench, _sample_audio.remote(), _sample_face.remote(), wait=3000)
        # GPU comes from THIS side (the runner holds HOOLA_LAB_GPU); inside the container it falls back to L4, so d['gpu'] lies
        lines = [f"GPU {GPU}  (MuseTalk {d['musetalk_commit']})",
                 f"models loaded once: {d['load_s']}s   face prepared: {d['prepare_s']}s   clip: {d['audio_s']}s = {d['frames']} frames",
                 "batch  secs  frames/s  x_realtime  ms_per_batch"]
        lines += [f"{r['batch']:>5}  {r['secs']:>4}  {r['fps']:>8}  {r['x_realtime']:>10}  {r['ms_per_batch']:>12}" for r in d["rows"]]
        best = min(d["rows"], key=lambda r: r["x_realtime"]) if d["rows"] else None
        if best:
            ok = best["x_realtime"] <= 1.0
            lines.append(f"best: batch {best['batch']} at {best['x_realtime']}x real time -> "
                         + ("LIVE-CAPABLE on this GPU (>= 25 fps)" if ok else "NOT live on this GPU: slower than the speech"))
        text = "\n".join(lines)
    except Exception as e:
        text = f"bench FAILED: {type(e).__name__} {str(e)[:600]}"
    print(text, flush=True)
    with open("lab_out/REPORT_bench.txt", "w") as f:
        f.write(text + "\n")


def _playback(batches: list) -> dict:
    """Replay one stream's batches against a 25 fps playhead: playback starts when the first batch is ready, and every time
    the next batch is not ready when the playhead needs it, the picture freezes (a stall) until it is."""
    if not batches:
        return {"first_s": None, "stall_s": None, "stalls": 0, "fps": 0.0}
    t = batches[0][0]
    stall, stalls = 0.0, 0
    for k, (ready, frames) in enumerate(batches):
        if k and ready > t:
            stall += ready - t
            stalls += 1
            t = ready
        t += frames / 25.0
    total = sum(f for _, f in batches)
    return {"first_s": round(batches[0][0], 2), "stall_s": round(stall, 2), "stalls": stalls,
            "fps": round(total / batches[-1][0], 1) if batches[-1][0] else 0.0}


@app.local_entrypoint()
def bench_streams():
    """What happens when 1, 2, 3 students arrive at once? Each is one stream of the same face; Modal gives each its own GPU
    container (the first is warm, the others are cold starts). A stream is smooth when its pictures are ready before the
    25 fps playhead needs them (stall ~ 0); first_batch_s shows how long a student waits when no card is free."""
    import threading
    os.makedirs("lab_out", exist_ok=True)
    lines = [f"GPU {GPU}  one student per container, batch 8, 24 s of speech per stream (the 8 s sample, 3 times)"]

    def note(text: str) -> None:
        lines.append(text)
        print(text, flush=True)
        with open("lab_out/REPORT_streams.txt", "w") as f:
            f.write("\n".join(lines) + "\n")

    try:
        live = Live()
        p = _call("live prepare", live.prepare, "lab-live", _sample_face.remote(), "ai_generated", wait=2700)
        audio = _sample_audio.remote()
        note(f"models loaded once: {p['load_s']}s   face prepared: {p['prepare_s']}s")
        _ = list(live.stream.remote_gen("lab-live", audio, 8, 1))                      # warm-up, not counted
        note("students  first_batch_s(best/worst)  stall_s(worst)  stalls(worst)  fps/student(worst)  smooth?")
        smooth_max = 0
        for n in (1, 2, 3):
            res: list = [None] * n

            def one(i: int) -> None:
                t = time.time()
                got, first_wall = [], None
                for b in live.stream.remote_gen("lab-live", audio, 8, 3):
                    if first_wall is None:
                        first_wall = round(time.time() - t, 2)
                    got.append((b["ready_s"], len(b["frames"])))
                r = _playback(got)
                r["first_wall"] = first_wall
                res[i] = r

            th = [threading.Thread(target=one, args=(i,), daemon=True) for i in range(n)]
            [x.start() for x in th]
            deadline = time.time() + 420      # cold starts of the extra containers take minutes; a hang must still cost only minutes
            [x.join(max(0.0, deadline - time.time())) for x in th]
            ok = [r for r in res if r]
            if len(ok) < n:
                note(f"{n:>7}  FAILED: only {len(ok)} of {n} streams finished within 420 s - stopping here")
                break
            worst_first = max(r["first_wall"] for r in ok)
            best_first = min(r["first_wall"] for r in ok)
            worst_stall = max(r["stall_s"] for r in ok)
            worst_stalls = max(r["stalls"] for r in ok)
            worst_fps = min(r["fps"] for r in ok)
            smooth = worst_stall <= 0.25
            smooth_max = n if smooth and smooth_max == n - 1 else smooth_max
            note(f"{n:>8}  {str(best_first) + ' / ' + str(worst_first):>24}  {worst_stall:>14}  {worst_stalls:>13}  {worst_fps:>18}  {'yes' if smooth else 'NO'}")
        note(f"RESULT: {smooth_max} simultaneous students all smooth, one {GPU} each")
    except Exception as e:
        note(f"streams FAILED: {type(e).__name__} {str(e)[:500]}")


def _ticket_ok(ticket: str, avatar: str, key: str) -> bool:
    """A pass made by the Hoola server (server/app/interactive/lab.py make_ticket): '<expires>.<avatar>.<hmac>' for ONE
    avatar, valid for minutes. Same maths on both sides, so the browser never needs the key itself."""
    import hashlib
    import hmac
    try:
        exp, who, sig = ticket.split(".", 2)
        if who != avatar or int(exp) < time.time():
            return False
        good = hmac.new(key.encode(), f"live|{exp}|{who}".encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, good)
    except Exception:
        return False


def split_speech(text: str, first_words: int = 5) -> list:
    """Cut a teacher's answer so speech starts early AND never runs dry: a first chunk of about five words (about
    2 s of speech, ending at a comma / full stop when one is near), then chunks that GROW (~8, ~16, ~32 words),
    each cut at a natural pause. Measured: voice time ~ 0.75 x the speech it makes, so every chunk must speak longer
    than the next one takes to make; a chunk of 4-5 words (1.5 s of speech) left a 1.2 s gap. Never fewer than 3 words
    in a chunk: a one-word line made the voice ramble for 12 s."""
    import re
    words = " ".join(text.split()).split(" ")
    if not words or words == [""]:
        return []
    stop = re.compile(r"[,;:।.?!]$")

    def cut_at(start: int, target: int) -> int:
        end = min(len(words), start + target)
        if end >= len(words):
            return len(words)
        lo, hi = start + max(3, int(target * 0.6)), min(len(words), start + int(target * 1.4) + 1)
        best = None
        for i in range(lo, hi):                                  # the pause closest to the target wins
            if stop.search(words[i - 1]) and (best is None or abs(i - end) < abs(best - end)):
                best = i
        cut = best or end
        if len(words) - cut < 3:                                 # no stub left over at the end
            cut = len(words)
        return cut

    out, i, target = [], 0, max(3, first_words)
    while i < len(words):
        j = cut_at(i, target)
        out.append(" ".join(words[i:j]))
        i, target = j, min(target * 2, 40)
    return out


def _wav_seconds(wav: bytes) -> float:
    """Length of a WAV in seconds, read from its header (no audio library needed on the runner)."""
    i = wav.find(b"data")
    if i < 0 or len(wav) < 36:
        return 0.0
    sr = int.from_bytes(wav[24:28], "little")
    align = int.from_bytes(wav[32:34], "little") or 2
    size = int.from_bytes(wav[i + 4:i + 8], "little")
    size = min(size, len(wav) - i - 8)
    return size / align / sr if sr else 0.0


@app.local_entrypoint()
def bench_e2e():
    """Voice + face together: from 'the teacher decides to speak' to 'the first picture exists'. Two containers
    (Chatterbox voice, then MuseTalk face), so this includes the hand-over of the audio between them."""
    os.makedirs("lab_out", exist_ok=True)
    lines = [f"GPU {GPU}  Hindi teacher lines: text -> Chatterbox voice -> MuseTalk face (warm, first 4 frames)"]

    def note(text: str) -> None:
        lines.append(text)
        print(text, flush=True)
        with open("lab_out/REPORT_e2e.txt", "w") as f:
            f.write("\n".join(lines) + "\n")

    cases = [
        ("short greeting", "नमस्ते आरव, आज हम गति के बारे में सीखेंगे।"),
        ("one sentence", "गति का मतलब है कि कोई चीज़ समय के साथ अपनी जगह कितनी तेज़ी से बदलती है।"),
        ("long sentence", "अगर एक गाड़ी दो घंटे में एक सौ बीस किलोमीटर जाती है, तो उसकी औसत चाल साठ किलोमीटर प्रति घंटा होगी।"),
        ("first clause only", "अगर एक गाड़ी दो घंटे में एक सौ बीस किलोमीटर जाती है,"),
    ]
    try:
        voice, live = Chatterbox(), Live()
        p = _call("live prepare", live.prepare, "lab-live", _sample_face.remote(), "ai_generated", wait=2700)
        note(f"face prepared: {p['prepare_s']}s   (warm-up below is not counted)")
        w = _call("voice warm-up", voice.speak, "नमस्ते।", "hi", wait=900)
        _ = list(live.stream.remote_gen("lab-live", w["wav"], 4, 1))
        _call("voice warm-up 2", voice.speak, cases[1][1], "hi", wait=900)      # a second, longer line so no row below is a first-use row
        note("case               audio_s  tts_s  (gpu_s)  tts/audio  face_first_s  e2e_first_frame_s")
        e2e_all, rtf_all = [], []
        for name, text in cases:
            t0 = time.time()
            r = _call(f"voice: {name}", voice.speak, text, "hi", wait=300)
            t_tts = time.time() - t0
            audio_s = _wav_seconds(r["wav"])
            first, e2e = None, None
            for b in live.stream.remote_gen("lab-live", r["wav"], 4, 1):      # drain it ALL: cancelling a call makes Modal restart the container (= a cold start for the next row)
                if first is None:
                    first, e2e = b["ready_s"], time.time() - t0
            rtf = round(t_tts / audio_s, 2) if audio_s else 0
            e2e_all.append(e2e)
            rtf_all.append(rtf)
            note(f"{name:<18} {audio_s:>7.1f} {t_tts:>6.1f} {r['synth_s']:>8} {rtf:>10} {str(first):>13} {e2e:>18.1f}")
        def keep(name: str, wav: bytes) -> None:          # the audio goes into the artifact so a person can LISTEN to it
            with open(f"lab_out/e2e_{name}.wav", "wb") as f:
                f.write(wav)

        # A line of one word used to ramble for 12 s; the voice now makes it again when audio runs far past the words.
        tiny = _call("voice: one word", voice.speak, "हाँ, ठीक है।", "hi", wait=300)
        note(f"short-line probe: gpu {tiny['synth_s']}s for {_wav_seconds(tiny['wav']):.1f}s of audio, tries {tiny.get('tries')}, runaway {tiny.get('runaway')}")
        keep("shortline", tiny["wav"])
        # The real answer path: first chunk ~7 words, then chunks that grow. Voice runs ahead of playback.
        long_text = " ".join(c[1] for c in (cases[1], cases[2])) + " अब आप बताइए कि अगर वही गाड़ी तीन घंटे चले, तो कितने किलोमीटर जाएगी?"
        chunks = split_speech(long_text)
        note(f"chunked answer: {len(chunks)} chunks of {[len(c.split()) for c in chunks]} words")
        import threading
        t0 = time.time()
        done: dict = {}

        def make(i: int, c: str) -> None:                  # every chunk is asked for at once; free voice containers pick them up in order
            done[i] = (_call(f"voice: chunk {i}", voice.speak, c, "hi", wait=300), time.time() - t0)

        th = []
        for i, c in enumerate(chunks, 1):
            x = threading.Thread(target=make, args=(i, c), daemon=True)
            x.start()
            th.append(x)
            time.sleep(0.15)                               # keep the order: chunk 1 first
        th[0].join(300)
        r, ready = done[1]
        keep("chunk1", r["wav"])
        chunk_e2e = None
        for b in live.stream.remote_gen("lab-live", r["wav"], 4, 1):
            if chunk_e2e is None:
                chunk_e2e = time.time() - t0
        play_end = chunk_e2e + _wav_seconds(r["wav"])     # chunk 1 starts playing at its first picture
        note(f"chunk 1 ({len(chunks[0].split())} words): voice ready at {ready:.1f}s, first picture {chunk_e2e:.1f}s, speaks {_wav_seconds(r['wav']):.1f}s, tries {r.get('tries')}")
        gaps = 0.0
        for i, c in enumerate(chunks[1:], 2):
            th[i - 1].join(300)
            r, ready = done[i]
            keep(f"chunk{i}", r["wav"])
            gap = max(0.0, ready - play_end)
            gaps += gap
            play_end = max(ready, play_end) + _wav_seconds(r["wav"])
            note(f"chunk {i} ({len(c.split())} words): ready at {ready:.1f}s, speaks {_wav_seconds(r['wav']):.1f}s, tries {r.get('tries')}, wait before it: {gap:.1f}s")
        e2e_all.append(chunk_e2e)
        note(f"CHUNKED: first picture after {chunk_e2e:.1f} s; total waiting between chunks {gaps:.1f} s -> " + ("no gaps" if gaps < 0.3 else "audible gaps"))
        best, worst = min(e2e_all), max(e2e_all)
        word = "conversational (<=2 s)" if worst <= 2 else "acceptable (<=4 s)" if worst <= 4 else "slow (>4 s)"
        note(f"RESULT: first picture after {best:.1f}-{worst:.1f} s -> {word}")
        note("Voice keeps up with real time: " + ("yes, a long answer can be spoken sentence by sentence without gaps"
             if max(rtf_all) < 1 else "NO - voice is slower than speech, long answers need the first clause sent early"))
    except Exception as e:
        note(f"e2e FAILED: {type(e).__name__} {str(e)[:500]}")


@app.function(image=face_image, timeout=300)
def _sample_audio() -> bytes:
    """MuseTalk's own demo speech clip (MIT repo) - lets the face be tested without running a voice model first."""
    with open(f"{MUSE_DIR}/data/audio/yongen.wav", "rb") as f:
        return f.read()


@app.function(image=face_image, timeout=300)
def _sample_face() -> bytes:
    """MuseTalk's own demo clip (shipped in its MIT repo) - a lab stand-in until our consented / AI-made face exists."""
    with open(f"{MUSE_DIR}/data/video/yongen.mp4", "rb") as f:
        return f.read()


# ================================================================ HOOLA STUDIO - the HeyGen feature set on our own engine
MAX_VIDEO_TEXT = 1800          # about 3 minutes of speech; longer scripts are cut into several videos by the caller
MAX_DUB_VIDEO = MAX_FACE_VIDEO
STUDIO_OPS = ("video", "photo_face", "voice_save", "transcribe", "dub", "podcast", "personalised")


def _wav_concat(wavs: list, gap_s: float = 0.0) -> bytes:
    """Join WAV files with the same format into one (stdlib only, so the small studio container can do it)."""
    import io
    import wave
    out_params, frames = None, []
    for w in wavs:
        with wave.open(io.BytesIO(w), "rb") as r:
            params = (r.getnchannels(), r.getsampwidth(), r.getframerate())
            if out_params is None:
                out_params = params
            elif params != out_params:
                raise ValueError("voice chunks do not share one audio format")
            frames.append(r.readframes(r.getnframes()))
    if out_params is None:
        raise ValueError("nothing to join")
    ch, width, rate = out_params
    gap = b"\0" * (int(gap_s * rate) * ch * width)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as o:
        o.setnchannels(ch)
        o.setsampwidth(width)
        o.setframerate(rate)
        o.writeframes(gap.join(frames))
    return buf.getvalue()


def _vtt(cues: list) -> str:
    """WebVTT captions from [(start_s, end_s, text)]."""
    def t(x: float) -> str:
        h, rem = divmod(max(0.0, x), 3600)
        m, sec = divmod(rem, 60)
        return f"{int(h):02d}:{int(m):02d}:{sec:06.3f}"
    lines = ["WEBVTT", ""]
    for i, (a, b, text) in enumerate(cues, 1):
        lines += [str(i), f"{t(a)} --> {t(b)}", text.strip(), ""]
    return "\n".join(lines)


def _mp4_concat(clips: list) -> bytes:
    """Cut several MP4 clips together (re-encoded once so mixed sources always join)."""
    d = f"/tmp/{uuid.uuid4().hex}"
    os.makedirs(d)
    names = []
    for i, c in enumerate(clips):
        n = f"{d}/c{i:03d}.mp4"
        with open(n, "wb") as f:
            f.write(c)
        names.append(n)
    with open(f"{d}/list.txt", "w") as f:
        f.write("".join(f"file '{n}'\n" for n in names))
    out = f"{d}/out.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", f"{d}/list.txt",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", out], check=True)
    with open(out, "rb") as f:
        data = f.read()
    shutil.rmtree(d, ignore_errors=True)
    return data


@app.cls(image=hear_image, volumes={MODELS_DIR: volume}, secrets=[secret], scaledown_window=IDLE, timeout=900, cpu=4, memory=4096)
class Hear:
    """Speech to text (faster-whisper small, MIT code + MIT weights, CPU int8): what was said, in which language, and when."""

    @modal.enter()
    def load(self):
        from faster_whisper import WhisperModel
        t = time.time()
        self.model = WhisperModel("small", device="cpu", compute_type="int8", download_root=f"{MODELS_DIR}/whisper_small")
        self.load_s = round(time.time() - t, 1)

    @modal.method()
    def transcribe(self, media: bytes, lang: str = "") -> dict:
        if not media or len(media) > MAX_DUB_VIDEO:
            raise ValueError("media missing or over 30 MB")
        src = _tmp(media, ".bin")
        wav = f"/tmp/{uuid.uuid4().hex}_16k.wav"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
        segs, info = self.model.transcribe(wav, language=(lang or None), word_timestamps=True, vad_filter=True)
        out = []
        for sg in segs:
            # float(): faster-whisper hands back numpy floats, and the studio image that receives this has no numpy
            out.append({"start": round(float(sg.start), 2), "end": round(float(sg.end), 2), "text": str(sg.text).strip(),
                        "words": [{"w": str(w.word).strip(), "start": round(float(w.start), 2), "end": round(float(w.end), 2)}
                                  for w in (sg.words or [])]})
        return {"language": str(info.language), "language_probability": round(float(info.language_probability), 2),
                "duration": round(float(info.duration), 2), "segments": out, "load_s": self.load_s}


def _speak_chunks(text: str, lang: str, voice_id: str, first_words: int = 14) -> tuple:
    """Chunk the text, make every chunk's voice at once on the voice containers, return (joined wav, cues, seconds)."""
    chunks = split_speech(text, first_words=first_words)
    if not chunks:
        raise ValueError("nothing to say")
    voice = Chatterbox()
    calls = [voice.speak.spawn(c, lang, None, voice_id) for c in chunks]
    wavs = [c.get(timeout=300)["wav"] for c in calls]
    cues, t = [], 0.0
    for c, w in zip(chunks, wavs):
        d = _wav_seconds(w)
        cues.append((t, t + d, c))
        t += d
    return _wav_concat(wavs), cues, t


def _has_audio(path: str) -> bool:
    """Does this media file carry a sound track? (ffprobe ships with ffmpeg)"""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    return bool(r.stdout.strip())


@app.function(image=studio_image, secrets=[secret], timeout=1800, max_containers=8)
def studio_job(op: str, p: dict) -> dict:
    """One HeyGen-style job. Every op is data in, data out ({files: {name: bytes}, info: {...}}), key-locked at the door
    (web()), consent-checked here. Nothing is stored except a prepared face / saved voice the caller asked for."""
    if op not in STUDIO_OPS:
        raise ValueError("unknown studio op")
    lang = str(p.get("lang") or "hi")[:5]
    voice_id = str(p.get("voice_id") or "")
    t0 = time.time()
    face = Live()
    if op == "photo_face":
        r = face.prepare_photo.remote(str(p.get("avatar_id") or ""), p.get("photo") or b"", str(p.get("consent") or ""))
        return {"files": {}, "info": r}
    if op == "voice_save":
        r = Chatterbox().save_voice.remote(str(p.get("voice_id") or ""), p.get("wav") or b"", str(p.get("consent") or ""))
        return {"files": {}, "info": r}
    if op == "transcribe":
        return {"files": {}, "info": Hear().transcribe.remote(p.get("media") or b"", str(p.get("lang") or ""))}
    if op == "video":
        text = str(p.get("text") or "").strip()
        if not text or len(text) > MAX_VIDEO_TEXT:
            raise ValueError(f"text: 1-{MAX_VIDEO_TEXT} characters")
        avatar = str(p.get("avatar_id") or "")
        wav, cues, secs = _speak_chunks(text, lang, voice_id)
        mp4 = face.render.remote(avatar, wav)
        return {"files": {"video.mp4": mp4, "captions.vtt": _vtt(cues).encode()},
                "info": {"seconds": round(secs, 1), "chunks": len(cues), "made_s": round(time.time() - t0, 1)}}
    if op == "dub":
        # Video Translate: the same person, the same voice, new words. The caller translated the text (its own brain);
        # here: voice from the speaker's own sound -> lip-sync onto their own video.
        consent = str(p.get("consent") or "")
        if not re.match(r"^signed:[A-Za-z0-9_-]{4,64}$", consent):
            raise ValueError("dubbing a real person needs consent 'signed:<record id>'")
        video = p.get("video") or b""
        text = str(p.get("text") or "").strip()
        if not video or len(video) > MAX_DUB_VIDEO:
            raise ValueError("video missing or over 30 MB")
        if not text or len(text) > MAX_VIDEO_TEXT:
            raise ValueError(f"text: 1-{MAX_VIDEO_TEXT} characters")
        tmp_id = "dub-" + uuid.uuid4().hex[:10]
        src = _tmp(video, ".mp4")
        if not _has_audio(src):
            raise ValueError("this video has no sound, so there is no voice to copy - send a video where the person speaks")
        sample = f"/tmp/{uuid.uuid4().hex}_ref.wav"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "24000", "-t", "20", sample], check=True)
        with open(sample, "rb") as f:
            Chatterbox().save_voice.remote(tmp_id, f.read(), consent)
        try:
            face.prepare.remote(tmp_id, video, "ai_generated" if p.get("consent_face_ai") else consent)
            wav, cues, secs = _speak_chunks(text, lang, tmp_id)
            mp4 = face.render.remote(tmp_id, wav)
        finally:
            for fn in (lambda: face.forget.remote(tmp_id), lambda: Chatterbox().delete_voice.remote(tmp_id)):
                try:
                    fn()
                except Exception:
                    pass
        return {"files": {"video.mp4": mp4, "captions.vtt": _vtt(cues).encode()},
                "info": {"seconds": round(secs, 1), "made_s": round(time.time() - t0, 1)}}
    if op == "podcast":
        lines = p.get("lines") or []
        hosts = p.get("hosts") or {}
        if not 1 <= len(lines) <= 24 or not all(k in hosts for k in ("a", "b")):
            raise ValueError("podcast: 1-24 lines and two hosts (a, b)")
        clips, cues, t = [], [], 0.0
        for ln in lines:
            h = hosts[str(ln.get("host") or "a")]
            text = str(ln.get("text") or "").strip()
            if not text or len(text) > 500:
                raise ValueError("each line: 1-500 characters")
            wav, _, secs = _speak_chunks(text, lang, str(h.get("voice_id") or ""))
            clips.append(face.render.remote(str(h.get("avatar_id") or ""), wav))
            cues.append((t, t + secs, text))
            t += secs
        return {"files": {"video.mp4": _mp4_concat(clips), "captions.vtt": _vtt(cues).encode()},
                "info": {"seconds": round(t, 1), "lines": len(lines), "made_s": round(time.time() - t0, 1)}}
    if op == "personalised":
        template = str(p.get("template") or "")
        names = [str(n).strip() for n in (p.get("names") or []) if str(n).strip()]
        if "{name}" not in template or not 1 <= len(names) <= 20 or len(template) > 400:
            raise ValueError("personalised: a template with {name} (max 400 chars) and 1-20 names")
        avatar = str(p.get("avatar_id") or "")
        wavs = []
        for n in names:
            wav, _, _ = _speak_chunks(template.replace("{name}", n), lang, voice_id)
            wavs.append(wav)
        calls = [face.render.spawn(avatar, w) for w in wavs]
        files = {f"video_{i + 1:02d}.mp4": c.get(timeout=600) for i, c in enumerate(calls)}
        return {"files": files, "info": {"names": names, "made_s": round(time.time() - t0, 1)}}
    raise ValueError("unknown studio op")



@app.function(image=face_image, timeout=300)
def _sample_photo() -> bytes:
    """One still picture from MuseTalk's sample clip - stands in for a photo until a real one is given."""
    out = "/tmp/sample_photo.jpg"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", f"{MUSE_DIR}/data/video/yongen.mp4", "-vframes", "1", out], check=True)
    with open(out, "rb") as f:
        return f.read()


@app.function(image=face_image, timeout=300)
def _sample_talking() -> bytes:
    """MuseTalk's sample face with its sample speech laid under it - a stand-in for 'a video of a person speaking'."""
    out = "/tmp/sample_talking.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", f"{MUSE_DIR}/data/video/yongen.mp4", "-i", f"{MUSE_DIR}/data/audio/yongen.wav",
                    "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", out], check=True)
    with open(out, "rb") as f:
        return f.read()


@app.local_entrypoint()
def studio_card():
    """Every Studio feature once, on the GPU: text to video, photo avatar, my voice, transcribe, dub, podcast, one video many
    names. A row per feature (PASS / FAIL, seconds, size) in lab_out/REPORT_studio.txt, the videos beside it to WATCH."""
    os.makedirs("lab_out", exist_ok=True)
    lines = [f"GPU {GPU}  Hoola Studio card - every feature once (sample face and sample voice, lab consent tags)"]

    def note(text: str) -> None:
        lines.append(text)
        print(text, flush=True)
        with open("lab_out/REPORT_studio.txt", "w") as f:
            f.write("\n".join(lines) + "\n")

    results: dict = {}

    def run(name: str, op: str, payload: dict, save: dict | None = None) -> dict | None:
        t = time.time()
        call = None
        try:
            call = studio_job.spawn(op, payload)
            r = call.get(timeout=900)          # a feature that crash-loops at startup must cost 15 minutes, never the whole run
        except Exception as e:
            if call is not None:
                try:
                    call.cancel()
                except Exception:
                    pass
            note(f"{name:<22} FAIL  {type(e).__name__}: {str(e)[:300]}")
            results[name] = False
            return None
        for fn, out_name in (save or {}).items():
            if fn in r["files"]:
                with open(f"lab_out/{out_name}", "wb") as f:
                    f.write(r["files"][fn])
        sizes = ", ".join(f"{k} {len(v) / 1024:.1f} KB" for k, v in r["files"].items())
        note(f"{name:<22} PASS  {time.time() - t:5.1f}s  {sizes or '-'}  {json.dumps(r['info'], ensure_ascii=False)[:200]}")
        results[name] = True
        return r

    consent = "signed:labtest0001"          # the lab uses MuseTalk's sample speaker; a real person's consent record is never faked
    text = "नमस्ते, मैं आपकी शिक्षक हूँ। आज हम गति के बारे में सीखेंगे। गति का मतलब है कि कोई चीज़ समय के साथ अपनी जगह कितनी तेज़ी से बदलती है।"
    try:
        live = Live()
        p = _call("live prepare", live.prepare, "lab-live", _sample_face.remote(), "ai_generated", wait=2700)
        note(f"sample face prepared: {p['prepare_s']}s")
    except Exception as e:
        note(f"face prepare FAILED: {type(e).__name__} {str(e)[:300]}")
        return
    run("1 text to video", "video", {"avatar_id": "lab-live", "text": text, "lang": "hi"},
        {"video.mp4": "studio_1_text_to_video.mp4", "captions.vtt": "studio_1_captions.vtt"})
    run("2 photo avatar", "photo_face", {"avatar_id": "lab-photo", "photo": _sample_photo.remote(), "consent": "ai_generated"})
    run("2b photo -> video", "video", {"avatar_id": "lab-photo", "text": "यह एक तस्वीर से बना वीडियो है।", "lang": "hi"},
        {"video.mp4": "studio_2_photo_avatar.mp4"})
    audio = _sample_audio.remote()
    run("3 my voice (save)", "voice_save", {"voice_id": "lab-voice", "wav": audio, "consent": consent})
    run("3b my voice -> video", "video", {"avatar_id": "lab-live", "voice_id": "lab-voice", "text": "यह मेरी अपनी आवाज़ में बोला गया वाक्य है।", "lang": "hi"},
        {"video.mp4": "studio_3_my_voice.mp4"})
    try:
        studio_job.spawn("voice_save", {"voice_id": "lab-bad", "wav": audio, "consent": "ai_generated"}).get(timeout=300)
        note("3c no-consent clone     FAIL  a voice was saved WITHOUT a consent record")
        results["3c refused"] = False
    except Exception as e:
        note(f"3c no-consent clone     PASS  refused: {str(e)[:120]}")
        results["3c refused"] = True
    r = run("4 transcribe", "transcribe", {"media": audio, "lang": ""})
    if r:
        note(f"   heard: language {r['info']['language']} ({r['info']['language_probability']}), {len(r['info']['segments'])} segments: "
             + " ".join(sg["text"] for sg in r["info"]["segments"])[:200])
    run("5 dub (video translate)", "dub", {"video": _sample_talking.remote(), "text": "यह वही व्यक्ति है, अब हिंदी में बोल रहा है।", "lang": "hi", "consent": consent},
        {"video.mp4": "studio_5_dub.mp4"})
    run("6 podcast (2 hosts)", "podcast", {"lang": "hi", "hosts": {"a": {"avatar_id": "lab-live", "voice_id": ""}, "b": {"avatar_id": "lab-photo", "voice_id": "lab-voice"}},
        "lines": [{"host": "a", "text": "आज हम बात करेंगे गति की।"}, {"host": "b", "text": "गति यानी चाल और दिशा, है न?"}, {"host": "a", "text": "बिल्कुल सही।"}]},
        {"video.mp4": "studio_6_podcast.mp4", "captions.vtt": "studio_6_captions.vtt"})
    run("7 one video, many names", "personalised", {"avatar_id": "lab-live", "lang": "hi", "template": "नमस्ते {name}, आपकी कक्षा कल सुबह दस बजे है।", "names": ["आरव", "सिया"]},
        {"video_01.mp4": "studio_7_aarav.mp4", "video_02.mp4": "studio_7_siya.mp4"})
    ok = sum(1 for v in results.values() if v)
    note(f"RESULT: {ok} of {len(results)} features passed")
    if ok < len(results):
        note("FAILED: " + ", ".join(k for k, v in results.items() if not v))
