"""Santosh Wake: train our own "Hey Santosh" wake-word model (no Picovoice, no licence fees).

How it works (same design as the open-source openWakeWord project, Apache-2.0):
  audio (16 kHz) -> melspectrogram.onnx -> embedding_model.onnx (Google speech_embedding, 96 numbers per 80 ms)
  -> our small classifier over the last 16 embeddings (1.28 s) -> score 0..1.
The two feature models are shared and pre-trained; we only train the small classifier, so training needs no GPU and
no recorded data: positive clips are synthesised with Piper TTS in many voices (English + Indian voices), negatives
are real speech (LibriSpeech), confusable phrases ("Santosh", "Hey Sandesh", "Hey Satish"...) and noise.

    python wakeword/train.py --work /tmp/wake --out tool/android/assets/wake
Outputs hey_santosh.onnx (input [1,16,96] -> score [1,1]) and metrics.json.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import tarfile
import time
import urllib.request
from pathlib import Path

import numpy as np
import onnxruntime as ort
from scipy.signal import fftconvolve, resample_poly

SR = 16000
CLIP = int(2.5 * SR)          # every training window is 2.5 s; the wake word ends in the last 0.35 s
N_EMB = 16                    # classifier sees the last 16 embeddings (1.28 s)
FEATURE_MODELS = {
    "melspectrogram.onnx": "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/melspectrogram.onnx",
    "embedding_model.onnx": "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/embedding_model.onnx",
}
HF = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
# (path under piper-voices, script for the phrase, split). Held-out voices measure how well it generalises.
VOICES = [
    ("en/en_US/libritts_r/medium/en_US-libritts_r-medium", "latin", "multi"),
    ("en/en_US/arctic/medium/en_US-arctic-medium", "latin", "multi"),
    ("en/en_US/lessac/medium/en_US-lessac-medium", "latin", "train"),
    ("en/en_US/amy/medium/en_US-amy-medium", "latin", "train"),
    ("en/en_US/ryan/medium/en_US-ryan-medium", "latin", "train"),
    ("en/en_US/joe/medium/en_US-joe-medium", "latin", "train"),
    ("en/en_US/kristin/medium/en_US-kristin-medium", "latin", "train"),
    ("en/en_US/hfc_male/medium/en_US-hfc_male-medium", "latin", "train"),
    ("en/en_US/hfc_female/medium/en_US-hfc_female-medium", "latin", "test"),
    ("en/en_GB/alan/medium/en_GB-alan-medium", "latin", "train"),
    ("en/en_GB/northern_english_male/medium/en_GB-northern_english_male-medium", "latin", "train"),
    ("en/en_GB/jenny_dioco/medium/en_GB-jenny_dioco-medium", "latin", "test"),
    ("en/en_GB/semaine/medium/en_GB-semaine-medium", "latin", "multi"),
    ("hi/hi_IN/pratham/medium/hi_IN-pratham-medium", "deva", "train"),
    ("hi/hi_IN/priyamvada/medium/hi_IN-priyamvada-medium", "deva", "train"),
    ("hi/hi_IN/rohan/medium/hi_IN-rohan-medium", "deva", "test"),
    ("ml/ml_IN/meera/medium/ml_IN-meera-medium", "latin", "train"),
    ("ml/ml_IN/arjun/medium/ml_IN-arjun-medium", "latin", "train"),
    ("te/te_IN/maya/medium/te_IN-maya-medium", "latin", "train"),
    ("ne/ne_NP/google/medium/ne_NP-google-medium", "deva", "train"),
]
POS = {"latin": ["hey santosh", "hey santosh!", "hey, santosh.", "hey santosh?", "hay santosh", "hey santhosh",
                 "hey santosh,"],
       "deva": ["हे संतोष", "हे संतोष!", "हे, संतोष।", "हे संतोष?"]}
CONFUSABLE = {"latin": ["santosh", "santosh ji", "hey sandesh", "hey satish", "hey sanjay", "hey santa", "hey sentosa",
                        "hey santoor", "hey sun", "hey sunny", "hey toast", "hey boss", "hey google", "hey siri",
                        "okay google", "hello", "hey there", "hey sir", "santosh kumar", "hey suresh", "hey subhash",
                        "hey sonu", "hey santro", "has to", "hey Sanjeev", "the hostess", "hey son", "Santoshi Maa"],
              "deva": ["संतोष", "संतोष जी", "हे संदेश", "हे सतीश", "हे संजय", "हे भगवान", "हे सुरेश", "संतोषी माता",
                       "हाँ संतोष ने कहा", "अरे सुनो", "हे सोनू", "संतोष कुमार"]}
SENTENCES = {"latin": [
    "please send me the invoice by tomorrow", "what is the balance in the account", "call me after the meeting",
    "the delivery will reach in two days", "can you check the stock of cement", "I will pay the electricity bill tonight",
    "let us go to the market in the evening", "the weather is very hot today", "my phone battery is low",
    "kal subah meeting hai", "bhai payment kab aayega", "order confirm kar do", "aaj bahut kaam hai",
    "Sharma ji ka bill bhej do", "gaadi kitne baje aayegi", "chai pi lo pehle", "mummy ko phone karo",
    "network nahi aa raha", "GST return file karna hai", "Tally mein entry baaki hai"],
    "deva": ["कल सुबह मीटिंग है", "भाई पेमेंट कब आएगा", "ऑर्डर कन्फर्म कर दो", "आज बहुत काम है", "शर्मा जी का बिल भेज दो",
             "गाड़ी कितने बजे आएगी", "पहले चाय पी लो", "नेटवर्क नहीं आ रहा", "जीएसटी रिटर्न फाइल करना है",
             "टैली में एंट्री बाकी है", "बिजली का बिल भरना है", "दुकान कितने बजे खुलेगी", "मेरा फोन कहाँ है",
             "संतोष ने फाइल भेजी थी", "हम कल पुणे जाएंगे"]}
LIBRISPEECH = {"dev-clean": "https://www.openslr.org/resources/12/dev-clean.tar.gz",
               "test-clean": "https://www.openslr.org/resources/12/test-clean.tar.gz"}


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def fetch(url: str, dest: Path) -> Path | None:
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=120) as r, open(str(dest) + ".part", "wb") as f:
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                f.write(b)
        os.replace(str(dest) + ".part", dest)
        return dest
    except Exception as e:  # a missing voice is skipped, not fatal
        log("  skip", url, type(e).__name__, e)
        return None


# ---------------------------------------------------------------- features (exactly what the phone computes)
class Features:
    def __init__(self, mel_path: Path, emb_path: Path):
        so = ort.SessionOptions()
        so.inter_op_num_threads = so.intra_op_num_threads = max(1, os.cpu_count() or 1)
        self.mel = ort.InferenceSession(str(mel_path), so, providers=["CPUExecutionProvider"])
        self.emb = ort.InferenceSession(str(emb_path), so, providers=["CPUExecutionProvider"])

    def melspec(self, x: np.ndarray) -> np.ndarray:
        out = self.mel.run(None, {"input": x.astype(np.float32)[None, :]})[0]
        return np.squeeze(out) / 10.0 + 2.0          # [frames, 32]

    def embeddings(self, x: np.ndarray) -> np.ndarray:
        spec = self.melspec(x)
        wins = [spec[i:i + 76] for i in range(0, spec.shape[0], 8) if spec[i:i + 76].shape[0] == 76]
        if not wins:
            return np.zeros((0, 96), np.float32)
        batch = np.asarray(wins, np.float32)[..., None]
        out = []
        for i in range(0, len(batch), 64):
            out.append(self.emb.run(None, {"input_1": batch[i:i + 64]})[0].reshape(-1, 96))
        return np.concatenate(out).astype(np.float32)

    def last16(self, clip: np.ndarray) -> np.ndarray:
        e = self.embeddings(clip)
        if e.shape[0] < N_EMB:
            raise ValueError(f"clip too short: {e.shape}")
        return e[-N_EMB:]


# ---------------------------------------------------------------- audio helpers
def to16k(audio: np.ndarray, sr: int) -> np.ndarray:
    x = audio.astype(np.float32)
    if sr == SR:
        return x
    g = math.gcd(SR, sr)
    return resample_poly(x, SR // g, sr // g).astype(np.float32)


def trim(x: np.ndarray, thr: float = 0.02) -> np.ndarray:
    a = np.abs(x) / (np.abs(x).max() + 1e-9)
    idx = np.where(a > thr)[0]
    return x if len(idx) == 0 else x[max(0, idx[0] - 800): idx[-1] + 800]


def colored_noise(n: int, kind: str, rng: np.random.Generator) -> np.ndarray:
    w = rng.standard_normal(n)
    if kind == "white":
        return w
    f = np.fft.rfft(w)
    freqs = np.arange(len(f)) + 1.0
    f /= np.sqrt(freqs) if kind == "pink" else freqs
    out = np.fft.irfft(f, n)
    return out / (np.std(out) + 1e-9)


def rir(rng: np.random.Generator) -> np.ndarray:
    rt60 = rng.uniform(0.15, 0.6)
    n = int(rt60 * SR)
    t = np.arange(n) / SR
    h = rng.standard_normal(n) * np.exp(-6.9 * t / rt60)
    h[0] = 1.0
    return h / np.sqrt(np.sum(h ** 2))


def mix_at_snr(sig: np.ndarray, noise: np.ndarray, snr_db: float) -> np.ndarray:
    ps, pn = np.mean(sig ** 2) + 1e-9, np.mean(noise ** 2) + 1e-9
    return sig + noise * np.sqrt(ps / (pn * 10 ** (snr_db / 10)))


def finish(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    peak = np.abs(x).max() + 1e-9
    level = 10 ** (rng.uniform(-24, -2) / 20) * 32767
    return np.clip(x / peak * level, -32768, 32767).astype(np.int16)


class Augmenter:
    def __init__(self, background: list[np.ndarray], rng: np.random.Generator):
        self.bg, self.rng = background, rng

    def background(self, n: int) -> np.ndarray:
        r = self.rng
        k = r.random()
        if k < 0.45 and self.bg:
            src = self.bg[r.integers(len(self.bg))]
            if len(src) > n:
                s = r.integers(0, len(src) - n)
                return src[s:s + n].astype(np.float32)
        kind = ["white", "pink", "brown"][r.integers(3)]
        noise = colored_noise(n, kind, r)
        if r.random() < 0.2:   # mains hum / fan
            t = np.arange(n) / SR
            noise += 0.5 * np.sin(2 * np.pi * 50 * t) + 0.25 * np.sin(2 * np.pi * 100 * t)
        return noise

    def place(self, word: np.ndarray, end_from_tail: float) -> np.ndarray:
        """Put the word into a 2.5 s window so it ends `end_from_tail` seconds before the end."""
        out = np.zeros(CLIP, np.float32)
        end = CLIP - int(end_from_tail * SR)
        start = max(0, end - len(word))
        seg = word[-(end - start):]
        out[start:end] = seg
        return out

    def positive(self, word: np.ndarray) -> np.ndarray:
        r = self.rng
        x = self.place(trim(word), r.uniform(0.02, 0.35))
        if r.random() < 0.4:
            x = fftconvolve(x, rir(r))[:CLIP]
        if r.random() < 0.9:
            x = mix_at_snr(x, self.background(CLIP), r.uniform(3, 25))
        return finish(x, r)

    def negative(self, sig: np.ndarray | None) -> np.ndarray:
        r = self.rng
        if sig is None:
            x = self.background(CLIP) * r.uniform(0.01, 1.0)
        else:
            sig = trim(sig) if len(sig) < CLIP else sig
            if len(sig) >= CLIP:
                s = r.integers(0, len(sig) - CLIP + 1)
                x = sig[s:s + CLIP].astype(np.float32)
            else:
                x = self.place(sig, r.uniform(0.0, 0.8))
            if r.random() < 0.3:
                x = fftconvolve(x, rir(r))[:CLIP]
            if r.random() < 0.7:
                x = mix_at_snr(x, self.background(CLIP), r.uniform(5, 30))
        return finish(x, r)


# ---------------------------------------------------------------- data
def load_voices(work: Path):
    from piper import PiperVoice
    voices = []
    for path, script, split in VOICES:
        m = fetch(HF + path + ".onnx", work / "voices" / (Path(path).name + ".onnx"))
        c = fetch(HF + path + ".onnx.json", work / "voices" / (Path(path).name + ".onnx.json"))
        if not (m and c):
            continue
        try:
            v = PiperVoice.load(str(m), config_path=str(c))
        except Exception as e:
            log("  voice failed", path, e)
            continue
        voices.append((Path(path).name, v, script, split))
        log("  voice", Path(path).name, "speakers", v.config.num_speakers)
    return voices


def speak(voice, text: str, rng: np.random.Generator, speaker: int | None) -> np.ndarray:
    from piper import SynthesisConfig
    cfg = SynthesisConfig(speaker_id=speaker, length_scale=float(rng.uniform(0.75, 1.35)),
                          noise_scale=float(rng.uniform(0.4, 0.9)), noise_w_scale=float(rng.uniform(0.5, 1.0)))
    chunks = [c.audio_int16_array for c in voice.synthesize(text, syn_config=cfg)]
    if not chunks:
        return np.zeros(0, np.float32)
    return to16k(np.concatenate(chunks), voice.config.sample_rate)


def tts_clips(voices, rng, per_voice: int, texts_of, held_out_frac: float = 0.15):
    """Returns (train, test) lists of float audio; multi-speaker voices hold out some speakers."""
    train, test = [], []
    for name, v, script, split in voices:
        texts = texts_of(script)
        n = per_voice * (6 if split == "multi" else 1)
        nspk = v.config.num_speakers
        held = set(rng.choice(nspk, max(1, int(nspk * held_out_frac)), replace=False).tolist()) if nspk > 1 else set()
        for i in range(n):
            spk = int(rng.integers(nspk)) if nspk > 1 else None
            try:
                a = speak(v, texts[int(rng.integers(len(texts)))], rng, spk)
            except Exception as e:
                log("  tts error", name, e)
                continue
            if len(a) < 1600:
                continue
            is_test = split == "test" or (spk is not None and spk in held)
            (test if is_test else train).append(a)
    return train, test


def librispeech(work: Path, name: str, limit_files: int) -> list[np.ndarray]:
    import soundfile as sf
    tgz = fetch(LIBRISPEECH[name], work / f"{name}.tar.gz")
    if not tgz:
        return []
    out_dir = work / name
    if not out_dir.exists():
        with tarfile.open(tgz) as t:
            t.extractall(out_dir)
    files = sorted(out_dir.rglob("*.flac"))[:limit_files]
    audio = []
    for f in files:
        a, sr = sf.read(f, dtype="int16")
        audio.append(np.clip(to16k(a, sr), -32768, 32767).astype(np.int16))   # int16 keeps memory low
    log(f"  {name}: {len(audio)} files, {sum(len(a) for a in audio) / SR / 3600:.2f} h")
    return audio


# ---------------------------------------------------------------- model (plain numpy: no torch needed)
class MLP:
    """1536 -> 128 -> 128 -> 1 with ReLU and a sigmoid; inputs are standardised inside the model."""

    def __init__(self, mean: np.ndarray, std: np.ndarray, rng: np.random.Generator, h: int = 128):
        d = N_EMB * 96
        self.mean, self.std = mean.astype(np.float32), std.astype(np.float32)
        he = lambda i, o: (rng.standard_normal((i, o)) * np.sqrt(2.0 / i)).astype(np.float32)
        self.p = {"W1": he(d, h), "b1": np.zeros(h, np.float32), "W2": he(h, h), "b2": np.zeros(h, np.float32),
                  "W3": he(h, 1), "b3": np.zeros(1, np.float32)}

    def forward(self, X: np.ndarray, keep: bool = False):
        x = (X.reshape(len(X), -1) - self.mean) / self.std
        z1 = x @ self.p["W1"] + self.p["b1"]
        a1 = np.maximum(z1, 0)
        z2 = a1 @ self.p["W2"] + self.p["b2"]
        a2 = np.maximum(z2, 0)
        z3 = a2 @ self.p["W3"] + self.p["b3"]
        out = 1.0 / (1.0 + np.exp(-np.clip(z3, -30, 30)))
        if keep:
            self._cache = (x, z1, a1, z2, a2)
        return out[:, 0]

    def backward(self, p: np.ndarray, y: np.ndarray, w: np.ndarray) -> dict:
        x, z1, a1, z2, a2 = self._cache
        n = len(y)
        d3 = ((p - y) * w / n)[:, None]                     # d(weighted BCE)/d(logit)
        g = {"W3": a2.T @ d3, "b3": d3.sum(0)}
        d2 = (d3 @ self.p["W3"].T) * (z2 > 0)
        g["W2"], g["b2"] = a1.T @ d2, d2.sum(0)
        d1 = (d2 @ self.p["W2"].T) * (z1 > 0)
        g["W1"], g["b1"] = x.T @ d1, d1.sum(0)
        return g

    def __call__(self, X):
        return self.forward(X)


def train_model(Xp, Xn, epochs: int, seed: int = 0, neg_weight: float = 5.0):
    rng = np.random.default_rng(seed)
    allX = np.concatenate([Xp[:20000], Xn[:60000]]).reshape(-1, N_EMB * 96)
    model = MLP(allX.mean(0), allX.std(0) + 1e-3, rng)
    m = {k: np.zeros_like(v) for k, v in model.p.items()}
    v2 = {k: np.zeros_like(v) for k, v in model.p.items()}
    b1, b2, eps, wd = 0.9, 0.999, 1e-8, 1e-4
    bs = 256
    steps = max(50, (len(Xp) + len(Xn)) // bs)
    total, t = epochs * steps, 0
    for ep in range(epochs):
        tot = 0.0
        for _ in range(steps):
            t += 1
            lr = 2e-3 * 0.5 * (1 + np.cos(np.pi * t / total))  # cosine decay
            ip, ineg = rng.integers(len(Xp), size=bs // 2), rng.integers(len(Xn), size=bs // 2)
            X = np.concatenate([Xp[ip], Xn[ineg]])
            y = np.concatenate([np.ones(bs // 2), np.zeros(bs // 2)]).astype(np.float32)
            w = np.concatenate([np.ones(bs // 2), np.full(bs // 2, neg_weight)]).astype(np.float32)
            p = np.clip(model.forward(X, keep=True), 1e-6, 1 - 1e-6)
            tot += float(np.mean(-(y * np.log(p) + (1 - y) * np.log(1 - p)) * w))
            g = model.backward(p, y, w)
            for k in model.p:
                gk = g[k] + wd * model.p[k]
                m[k] = b1 * m[k] + (1 - b1) * gk
                v2[k] = b2 * v2[k] + (1 - b2) * gk * gk
                mh, vh = m[k] / (1 - b1 ** t), v2[k] / (1 - b2 ** t)
                model.p[k] -= (lr * mh / (np.sqrt(vh) + eps)).astype(np.float32)
        if ep % 5 == 0 or ep == epochs - 1:
            log(f"  epoch {ep + 1}/{epochs} loss {tot / steps:.4f}")
    return model


def scores(model, X) -> np.ndarray:
    out = [model(np.asarray(X[i:i + 2048], np.float32)) for i in range(0, len(X), 2048)]
    return np.concatenate(out) if out else np.zeros(0)


def stream_windows(emb: np.ndarray) -> np.ndarray:
    """Every 80 ms position of a long recording -> [n, 16, 96] (what the phone scores while listening)."""
    if len(emb) < N_EMB:
        return np.zeros((0, N_EMB, 96), np.float32)
    idx = np.arange(N_EMB)[None, :] + np.arange(len(emb) - N_EMB + 1)[:, None]
    return emb[idx]


def false_accepts(model, rec_windows: list[tuple[np.ndarray, float]], thr: float) -> tuple[int, float]:
    events, secs = 0, 0.0
    for w, dur in rec_windows:
        secs += dur
        if len(w) == 0:
            continue
        s = scores(model, w)
        last = -100
        for i, v in enumerate(s):
            if v >= thr and i - last > 12:   # ~1 s debounce, like the phone
                events += 1
                last = i
    return events, secs / 3600


def export_onnx(model: MLP, path: Path) -> None:
    """input [N,16,96] -> score [N,1]; standardisation is folded into the first layer."""
    import onnx
    from onnx import TensorProto, helper, numpy_helper
    W1 = model.p["W1"] / model.std[:, None]
    b1 = model.p["b1"] - (model.mean / model.std) @ model.p["W1"]
    inits = [numpy_helper.from_array(a.astype(np.float32), n) for n, a in
             (("W1", W1), ("b1", b1), ("W2", model.p["W2"]), ("b2", model.p["b2"]), ("W3", model.p["W3"]),
              ("b3", model.p["b3"]))]
    nodes = [helper.make_node("Flatten", ["input"], ["x"], axis=1),
             helper.make_node("Gemm", ["x", "W1", "b1"], ["z1"]), helper.make_node("Relu", ["z1"], ["a1"]),
             helper.make_node("Gemm", ["a1", "W2", "b2"], ["z2"]), helper.make_node("Relu", ["z2"], ["a2"]),
             helper.make_node("Gemm", ["a2", "W3", "b3"], ["z3"]), helper.make_node("Sigmoid", ["z3"], ["score"])]
    g = helper.make_graph(nodes, "hey_santosh",
                          [helper.make_tensor_value_info("input", TensorProto.FLOAT, ["batch", N_EMB, 96])],
                          [helper.make_tensor_value_info("score", TensorProto.FLOAT, ["batch", 1])], inits)
    m = helper.make_model(g, opset_imports=[helper.make_opsetid("", 13)], producer_name="santosh-wake")
    m.ir_version = 8
    onnx.checker.check_model(m)
    path.parent.mkdir(parents=True, exist_ok=True)
    onnx.save(m, str(path))


def _dry_patch(work: Path) -> None:
    """Swap downloads for stand-ins so the whole pipeline can be exercised offline."""
    work.mkdir(parents=True, exist_ok=True)
    g = globals()
    proj = np.random.default_rng(1).standard_normal((160, 96)).astype(np.float32) / 400

    class FakeFeatures:
        def __init__(self, *a):
            pass

        def embeddings(self, x):
            n = (len(x) - 1760) // 1280 + 1
            fr = np.asarray(x[: n * 1280], np.float32).reshape(n, 8, 160)
            return np.tanh(np.abs(fr).mean(1) @ proj).astype(np.float32)

        def last16(self, clip):
            e = self.embeddings(clip)
            return e[-N_EMB:]
    g["Features"] = FakeFeatures
    g["fetch"] = lambda url, dest: dest
    rng = np.random.default_rng(0)
    g["librispeech"] = lambda work, name, limit: [(rng.standard_normal(SR * 6) * 3000).astype(np.int16) for _ in range(8)]

    class V:
        class config:
            num_speakers = 3
            sample_rate = 22050
    g["load_voices"] = lambda work: [("fake-a", V(), "latin", "multi"), ("fake-b", V(), "deva", "test")]
    g["speak"] = lambda voice, text, rng, spk: (np.sin(np.arange(int(SR * 0.8)) * (0.05 + len(text) / 500))
                                                * 8000).astype(np.float32)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/tmp/santosh-wake")
    ap.add_argument("--out", default="tool/android/assets/wake")
    ap.add_argument("--per-voice", type=int, default=120)
    ap.add_argument("--librispeech-files", type=int, default=2700)
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--dry", action="store_true", help="plumbing test with stand-in models and synthetic audio")
    a = ap.parse_args()
    if a.dry:
        _dry_patch(Path(a.work))
    work, out = Path(a.work), Path(a.out)
    work.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    random.seed(a.seed)

    log("feature models")
    paths = {k: fetch(u, work / k) for k, u in FEATURE_MODELS.items()}
    feats = Features(paths["melspectrogram.onnx"], paths["embedding_model.onnx"])

    log("real speech (LibriSpeech)")
    dev = librispeech(work, "dev-clean", a.librispeech_files)
    test_rec = librispeech(work, "test-clean", 600)

    log("voices")
    voices = load_voices(work)
    if not voices:
        raise SystemExit("no TTS voices could be loaded")

    log("positives")
    pos_train, pos_test = tts_clips(voices, rng, a.per_voice, lambda s: POS[s])
    log(f"  {len(pos_train)} train / {len(pos_test)} held-out voices")
    log("confusable phrases and Indian sentences (negatives)")
    conf_train, conf_test = tts_clips(voices, rng, max(20, a.per_voice // 2), lambda s: CONFUSABLE[s])
    sent_train, _ = tts_clips(voices, rng, max(10, a.per_voice // 4), lambda s: SENTENCES[s])

    aug = Augmenter(dev[: len(dev) // 2], rng)
    log("features: positives")
    Xp = np.stack([feats.last16(aug.positive(c)) for c in pos_train for _ in range(3)])
    Xp_test = np.stack([feats.last16(aug.positive(c)) for c in pos_test])
    log("features: negatives")
    neg = [feats.last16(aug.negative(c)) for c in conf_train for _ in range(3)]
    neg += [feats.last16(aug.negative(c)) for c in sent_train for _ in range(2)]
    neg += [feats.last16(aug.negative(dev[int(rng.integers(len(dev)))])) for _ in range(12000)]
    neg += [feats.last16(aug.negative(None)) for _ in range(3000)]
    # the end of "hey santosh" cut short ("hey santo") must not fire
    neg += [feats.last16(aug.negative(c[: int(len(trim(c)) * rng.uniform(0.3, 0.7))])) for c in pos_train[:800]]
    Xn = np.stack(neg)
    Xc_test = np.stack([feats.last16(aug.negative(c)) for c in conf_test]) if conf_test else np.zeros((0, N_EMB, 96))
    log(f"  positives {Xp.shape[0]}, negatives {Xn.shape[0]}")

    log("train round 1")
    model = train_model(Xp, Xn, a.epochs, a.seed)
    log("hard negatives from real speech")
    hard = []
    for rec in dev[len(dev) // 2:]:
        w = stream_windows(feats.embeddings(rec.astype(np.int16).astype(np.float32)))
        if len(w):
            s = scores(model, w)
            hard.extend(w[s > 0.2])
    log(f"  {len(hard)} hard negatives")
    if hard:
        Xn = np.concatenate([Xn, np.asarray(hard, np.float32)])
        log("train round 2")
        model = train_model(Xp, Xn, a.epochs, a.seed + 1)

    log("evaluate")
    metrics: dict = {"positives_train": int(len(Xp)), "negatives_train": int(len(Xn)),
                     "voices": [v[0] for v in voices], "held_out_positive_clips": int(len(Xp_test))}
    sp = scores(model, Xp_test)
    sc = scores(model, Xc_test) if len(Xc_test) else np.zeros(0)
    rec_windows = [(stream_windows(feats.embeddings(r.astype(np.float32))), len(r) / SR) for r in test_rec]
    for thr in (0.3, 0.5, 0.7, 0.85):
        fa, hours = false_accepts(model, rec_windows, thr)
        metrics[f"thr_{thr}"] = {
            "recall_held_out_voices": round(float((sp >= thr).mean()), 4) if len(sp) else None,
            "confusable_false_rate": round(float((sc >= thr).mean()), 4) if len(sc) else None,
            "false_accepts_per_hour_librispeech_test": round(fa / max(hours, 1e-6), 3),
            "eval_hours": round(hours, 2)}
        log(f"  thr {thr}: {metrics[f'thr_{thr}']}")
    out.mkdir(parents=True, exist_ok=True)
    export_onnx(model, out / "hey_santosh.onnx")
    sess = ort.InferenceSession(str(out / "hey_santosh.onnx"))
    chk = sess.run(None, {"input": Xp_test[:4].astype(np.float32)})[0].ravel()
    assert np.allclose(chk, sp[:4], atol=1e-4), (chk, sp[:4])
    (out / "metrics.json").write_text(json.dumps(metrics, indent=1, ensure_ascii=False))
    log("saved", out / "hey_santosh.onnx")


if __name__ == "__main__":
    main()
