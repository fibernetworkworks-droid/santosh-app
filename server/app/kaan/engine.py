"""The transcription engine: openai-whisper behind one hand-built interface.

Facts below are from the repository read of openai/whisper (v20250625, MIT), not invented:
- audio = 16 kHz mono float32 via ffmpeg (whisper.load_audio); 30 s chunks, 3000 mel frames, each token 20 ms
- decode quality guards are the engine's own defaults, passed explicitly here so they are visible and
  testable: temperature fallback 0.0 -> 1.0, a window fails when compression_ratio > 2.4 or
  avg_logprob < -1.0, silent windows are skipped when no_speech_prob > 0.6
- word_timestamps=True runs the DTW alignment against the alignment heads and yields per-word timings
- model zoo (params): tiny 39M, base 74M, small 244M, medium 769M, turbo 809M (~8x faster than large,
  NO translate task), large-v3 1550M (128 mel bins)

LAZY + INERT: `import whisper` lives inside _load(). If the package or ffmpeg is missing, available()
says so in one line and transcribe raises KaanError with the install line - never a stack trace to her.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Callable

log = logging.getLogger(__name__)

MODEL_LADDER: tuple[dict[str, Any], ...] = (
    {"name": "tiny", "params": "39M", "note": "fastest, draft quality"},
    {"name": "base", "params": "74M", "note": "fast, rough"},
    {"name": "small", "params": "244M", "note": "the daily default on CPU"},
    {"name": "medium", "params": "769M", "note": "slower, better accents"},
    {"name": "turbo", "params": "809M", "note": "~8x faster than large; NO translate task"},
    {"name": "large-v3", "params": "1550M", "note": "best accuracy; 128 mel; the local translate path"},
)
TRANSLATE_CAPABLE = frozenset({"tiny", "base", "small", "medium", "large-v3"})   # turbo cannot translate

# the engine's own published guards, passed explicitly (from the repo read, not guessed)
TEMPERATURES = tuple(round(0.2 * i, 2) for i in range(6))    # (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
COMPRESSION_RATIO_THRESHOLD = 2.4
LOGPROB_THRESHOLD = -1.0
NO_SPEECH_THRESHOLD = 0.6

DEFAULT_MODEL_ENV = "KAAN_MODEL"


def default_model() -> str:
    return (os.environ.get(DEFAULT_MODEL_ENV, "").strip() or "small").lower()


class KaanError(Exception):
    """One honest line for her; never a raw traceback."""


def _model_dir() -> str:
    return os.environ.get("KAAN_MODELS_DIR", "").strip()


def _load(model: str):
    """The ONLY place whisper is imported (port law + inertness law)."""
    import whisper  # openai-whisper (MIT) - a dependency, never vendored

    return whisper.load_model(model, download_root=_model_dir() or None)


_AVAIL: dict[str, tuple[bool, str]] = {}


def available(refresh: bool = False) -> tuple[bool, str]:
    """(ok, line). ok=False carries the one-line reason: package missing, or ffmpeg missing.
    Result is cached; tests pass refresh=True after installing."""
    if not refresh and _AVAIL:
        return _AVAIL["ok"]
    try:
        import whisper  # noqa: F401
        ok_pkg = True
        why_pkg = ""
    except Exception as e:                                   # pragma: no cover - env-specific
        ok_pkg, why_pkg = False, f"the openai-whisper package is missing ({type(e).__name__}) - run `pip install openai-whisper` on the server."
    ok_ff, why_ff = _ffmpeg_ok()
    if not ok_pkg:
        out = (False, why_pkg)
    elif not ok_ff:
        out = (False, why_ff)
    else:
        out = (True, "engine ready")
    _AVAIL["ok"] = out
    return out


def _ffmpeg_ok() -> tuple[bool, str]:
    import shutil
    if shutil.which("ffmpeg"):
        return True, ""
    return False, "ffmpeg was not found on the server - it is needed to decode audio (apt install ffmpeg)."


def transcribe(path: str, *, model: str = "", language: str = "", task: str = "transcribe",
               word_timestamps: bool = True, initial_prompt: str = "") -> dict[str, Any]:
    """One call into the real engine. Returns a plain dict; raises KaanError with an honest line.
    Engine-injectable: tests swap engine._load for a fake (the voice_openai `connect` swap pattern).
    W3: initial_prompt carries the tenant vocabulary hint (soft - whisper may not honor it)."""
    model = (model or default_model()).lower()
    if model not in {m["name"] for m in MODEL_LADDER}:
        raise KaanError(f"unknown model '{model}'. Ladder: {', '.join(m['name'] for m in MODEL_LADDER)}.")
    if task == "translate" and model not in TRANSLATE_CAPABLE:
        raise KaanError(f"model '{model}' cannot translate (turbo cannot) - use 'large-v3' or 'medium'.")
    if not os.path.exists(path):
        raise KaanError("the audio file was not found on the server.")
    ok, why = available()
    if not ok:
        raise KaanError(why)
    try:
        import whisper
        w = _load(model)
        result = w.transcribe(
            path,
            language=language or None,
            task=task,
            word_timestamps=word_timestamps,
            initial_prompt=initial_prompt or None,
            temperature=TEMPERATURES,
            compression_ratio_threshold=COMPRESSION_RATIO_THRESHOLD,
            logprob_threshold=LOGPROB_THRESHOLD,
            no_speech_threshold=NO_SPEECH_THRESHOLD,
            fp16=False,                                   # CPU truth on the VPS
        )
    except KaanError:
        raise
    except Exception as e:
        log.exception("kaan: engine transcribe failed")
        raise KaanError(f"the engine could not transcribe ({type(e).__name__}: {str(e)[:120]}).") from e
    segments = []
    for s in result.get("segments", []) or []:
        seg = {"start": round(float(s.get("start", 0.0)), 3), "end": round(float(s.get("end", 0.0)), 3),
               "text": (s.get("text") or "").strip()}
        if word_timestamps and s.get("words"):
            seg["words"] = [{"word": w.get("word", ""), "start": round(float(w.get("start", 0.0)), 3),
                             "end": round(float(w.get("end", 0.0)), 3)} for w in s["words"]]
        segments.append(seg)
    return {
        "text": (result.get("text") or "").strip(),
        "language": result.get("language", "") or language or "",
        "segments": segments,
        "model": model,
        "task": task,
    }


def fake_engine(text: str, language: str = "hi") -> Callable[..., dict[str, Any]]:
    """A scripted engine for tests and the CI lane (zero network, zero torch).
    Returns a transcribe()-shaped callable with the same guards (model ladder, translate cap, file check)."""
    def _fake(path: str, *, model: str = "", language: str = "", task: str = "transcribe",
              word_timestamps: bool = True, initial_prompt: str = "", **_k) -> dict[str, Any]:
        model = (model or default_model()).lower()
        if model not in {m["name"] for m in MODEL_LADDER}:
            raise KaanError(f"unknown model '{model}'. Ladder: {', '.join(m['name'] for m in MODEL_LADDER)}.")
        if task == "translate" and model not in TRANSLATE_CAPABLE:
            raise KaanError(f"model '{model}' cannot translate (turbo cannot) - use 'large-v3' or 'medium'.")
        if not os.path.exists(path):
            raise KaanError("the audio file was not found on the server.")
        words = []
        t = 0.0
        for w in text.split():
            words.append({"word": w, "start": round(t, 3), "end": round(t + 0.32, 3)})
            t += 0.32
        seg = {"start": 0.0, "end": round(t, 3), "text": text}
        if word_timestamps:
            seg["words"] = words
        return {"text": text, "language": language or "hi", "segments": [seg], "model": model, "task": task}
    return _fake
