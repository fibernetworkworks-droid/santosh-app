"""Voice fingerprints with two free speaker-recognition models, run on the CPU by sherpa-onnx (Apache-2.0):

  * CAM++ (3D-Speaker, Apache-2.0, trained on Chinese + English speakers)    ~35 ms for 3 s of speech
  * TitaNet-small (NVIDIA NeMo, CC-BY-4.0)                                   ~30 ms for 3 s of speech

A fingerprint is a short list of numbers per model; two recordings of the same person point the same way.
The score of a person is the average similarity over both models (more robust than either alone).
"""
from __future__ import annotations

import logging
import threading
from array import array
from pathlib import Path

from ..config import get_settings

log = logging.getLogger("santosh.voiceid")

RATE = 16000
MODELS = {
    "campplus": "3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced.onnx",
    "titanet": "nemo_en_titanet_small.onnx",
}
RELEASE = "https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/"

_lock = threading.Lock()
_extractors: dict | None = None
_error = ""


def available() -> bool:
    try:
        import numpy  # noqa: F401
        import sherpa_onnx  # noqa: F401
    except ImportError:
        return False
    d = Path(get_settings().voiceid_models_dir)
    return all((d / f).exists() for f in MODELS.values())


def status() -> dict:
    return {"available": available(), "error": _error, "models": list(MODELS)}


def _load() -> dict:
    global _extractors, _error
    with _lock:
        if _extractors is None:
            import sherpa_onnx
            d = Path(get_settings().voiceid_models_dir)
            ex = {}
            for name, f in MODELS.items():
                cfg = sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(d / f), num_threads=2)
                if not cfg.validate():
                    _error = f"model {f} could not be loaded"
                    raise RuntimeError(_error)
                ex[name] = sherpa_onnx.SpeakerEmbeddingExtractor(cfg)
            _extractors = ex
        return _extractors


def speech_only(pcm: bytes, rate: int = RATE) -> bytes:
    """Keep the 30 ms frames that have voice in them (drops pauses and silence the phone sent while Hoola spoke)."""
    a = array("h")
    a.frombytes(pcm[: len(pcm) // 2 * 2])
    n = rate * 30 // 1000
    frames = [a[i:i + n] for i in range(0, len(a) - n + 1, n)]
    if not frames:
        return b""
    levels = [(sum(x * x for x in f[::3]) / len(f[::3])) ** 0.5 for f in frames]
    loud = sorted(levels)
    floor = loud[len(loud) // 10]
    cut = max(300.0, floor * 2.5)
    keep = array("h")
    for f, lv in zip(frames, levels):
        if lv > cut:
            keep.extend(f)
    return keep.tobytes()


def embed(pcm: bytes) -> dict[str, list[float]]:
    """Fingerprint of 16 kHz mono PCM16 speech: {model: unit vector}."""
    import numpy as np
    x = np.frombuffer(pcm[: len(pcm) // 2 * 2], dtype="<i2").astype(np.float32) / 32768.0
    out = {}
    for name, ex in _load().items():
        s = ex.create_stream()
        s.accept_waveform(RATE, x)
        s.input_finished()
        v = np.asarray(ex.compute(s), dtype=np.float32)
        out[name] = (v / (np.linalg.norm(v) + 1e-9)).tolist()
    return out


def enrol_print(pcm: bytes) -> dict[str, list[float]]:
    """Fingerprint of an enrolment: the average of 3 s pieces of the speech (steadier than one long piece)."""
    import numpy as np
    sp = speech_only(pcm)
    win, hop = RATE * 3 * 2, RATE * 3 // 2 * 2
    pieces = [sp[i:i + win] for i in range(0, max(1, len(sp) - win + 1), hop)] or [sp]
    acc: dict[str, list] = {}
    for p in pieces:
        for k, v in embed(p).items():
            acc.setdefault(k, []).append(v)
    out = {}
    for k, vs in acc.items():
        m = np.mean(np.asarray(vs, dtype=np.float32), axis=0)
        out[k] = (m / (np.linalg.norm(m) + 1e-9)).tolist()
    return out


def score(a: dict[str, list[float]], b: dict[str, list[float]]) -> float:
    """Average cosine similarity over the models both fingerprints have."""
    common = [k for k in a if k in b]
    if not common:
        return 0.0
    tot = 0.0
    for k in common:
        x, y = a[k], b[k]
        tot += sum(p * q for p, q in zip(x, y)) / ((sum(p * p for p in x) ** 0.5) * (sum(q * q for q in y) ** 0.5) + 1e-9)
    return tot / len(common)
