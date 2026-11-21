"""v0.999.90 HOOLA VOCAL GLOBAL - the ElevenLabs engine (premium voices, the languages Gemini lacks, voice changer, voice
out of music, sound effects from words, dubbing in the speakers' own voices).

Request shapes from ElevenLabs' own API reference (elevenlabs.io/docs, read 21 Nov 2026):
- POST /v1/text-to-speech/{voice_id}: text, model_id, language_code, voice_settings; `output_format` query.
- GET  /v2/voices: page_size up to 100, search, voice_type, gender, language. Returns voices[] with verified_languages.
- POST /v1/voice-changer/{voice_id}: multipart audio, model_id eleven_multilingual_sts_v2, remove_background_noise.
- POST /v1/audio-isolation: multipart audio.
- POST /v1/sound-generation: text, duration_seconds 0.5-30, loop, prompt_influence, model_id eleven_text_to_sound_v3.
- POST /v1/dubbing/project (multipart file, model_id dubbing_v2), POST /v1/dubbing/project/{id}/language
  {target_language}, then each language's outputs.lossless_audio (FLAC, a signed one-hour URL).
The key lives only in the VPS .env (ELEVENLABS_API_KEY) and is never shown. Every call is counted by usage.record at
ElevenLabs' per-minute API price (elevenlabs.io/pricing/api).

NOT VERIFIED: no call has been made from here (no key in this sandbox).
"""
from __future__ import annotations

import io
import logging
import re
import wave
from typing import Any

log = logging.getLogger("santosh.vocal.eleven")
BASE = "https://api.elevenlabs.io"
# USD per minute of sound, from elevenlabs.io/pricing/api (21 Nov 2026)
USD_MIN = {"tts": 0.08, "tts_fast": 0.04, "change": 0.12, "isolate": 0.12, "sfx": 0.12, "dub": 2.20}


class ElevenError(Exception):
    pass


def key() -> str:
    from ..config import get_settings
    return (getattr(get_settings(), "elevenlabs_api_key", "") or "").strip()


def ready() -> bool:
    return bool(key())


def _http(method: str, url: str, **kw):          # the one network seam (tests replace it)
    import httpx
    return httpx.request(method, url, timeout=kw.pop("timeout", 180), **kw)


def _call(method: str, path: str, **kw):
    if not ready():
        raise ElevenError("Premium voices need an ElevenLabs key on the server (ELEVENLABS_API_KEY in the VPS .env).")
    headers = {"xi-api-key": key(), **kw.pop("headers", {})}
    r = _http(method, BASE + path, headers=headers, **kw)
    if r.status_code >= 400:
        try:
            d = r.json().get("detail")
            msg = d.get("message") if isinstance(d, dict) else d
        except Exception:   # noqa: BLE001
            msg = r.text
        msg = re.sub(r"\s+", " ", str(msg or r.status_code))[:200]
        if r.status_code == 401:
            raise ElevenError("ElevenLabs refused the key on the server. Check ELEVENLABS_API_KEY.")
        if r.status_code in (402, 429):
            raise ElevenError(f"ElevenLabs says the account is out of credit or busy ({msg}).")
        raise ElevenError(f"ElevenLabs said: {msg}")
    return r


def _count(kind: str, seconds: float) -> None:
    try:
        from .. import usage
        usage.record(f"elevenlabs-{kind}", sec_out=max(seconds, 1.0), feature="create")
    except Exception:   # noqa: BLE001
        pass


def pcm_to_wav(pcm: bytes, rate: int = 24000) -> bytes:
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return b.getvalue()


# ---------------------------------------------------------------- speech
def tts(text: str, voice_id: str, model_id: str = "eleven_v4", lang: str = "", stability: float = 0.5,
        similarity: float = 0.75, style: float = 0.0, speed: float = 1.0) -> bytes:
    """Returns a WAV (24 kHz mono). eleven_v3 / v4 read [whispers] [laughs] in the text natively."""
    body: dict[str, Any] = {"text": text, "model_id": model_id,
                            "voice_settings": {"stability": stability, "similarity_boost": similarity, "style": style,
                                               "use_speaker_boost": True, "speed": speed}}
    if lang and "-" not in lang and len(lang) == 2 and model_id != "eleven_multilingual_v2":
        body["language_code"] = lang
    r = _call("POST", f"/v1/text-to-speech/{voice_id}", params={"output_format": "pcm_24000"}, json=body)
    wav = pcm_to_wav(r.content)
    _count("tts", len(r.content) / 48000)
    return wav


def voices() -> list[dict]:
    """ElevenLabs' ready-made voices (premade + her account's). [] without a key or when the list cannot be read."""
    if not ready():
        return []
    out, token = [], None
    try:
        for _ in range(5):
            params: dict[str, Any] = {"page_size": 100}
            if token:
                params["next_page_token"] = token
            d = _call("GET", "/v2/voices", params=params).json()
            for v in d.get("voices") or []:
                lab = v.get("labels") or {}
                langs = sorted({str(x.get("language") or "").split("-")[0] for x in v.get("verified_languages") or [] if x.get("language")})
                out.append({"id": v.get("voice_id"), "name": v.get("name") or "Voice", "gender": (lab.get("gender") or "").lower(),
                            "age": (lab.get("age") or "").lower(), "accent": lab.get("accent") or "",
                            "use": (lab.get("use_case") or lab.get("use case") or "").replace("_", " "),
                            "description": v.get("description") or lab.get("description") or "", "langs": langs})
            token = d.get("next_page_token")
            if not d.get("has_more") or not token:
                break
    except ElevenError as e:
        log.info("elevenlabs voices not read: %s", e)
    return out


# ---------------------------------------------------------------- sound tools
def change(audio: bytes, filename: str, voice_id: str, denoise: bool = True) -> bytes:
    r = _call("POST", f"/v1/voice-changer/{voice_id}", params={"output_format": "pcm_24000"},
              files={"audio": (filename or "audio", audio)},
              data={"model_id": "eleven_multilingual_sts_v2", "remove_background_noise": "true" if denoise else "false"})
    _count("change", len(r.content) / 48000)
    return pcm_to_wav(r.content)


def isolate(audio: bytes, filename: str, seconds: float) -> bytes:
    """The voice alone (noise, music, other people removed). The reply's sound format is not stated by the docs; the
    caller reads it by its bytes."""
    r = _call("POST", "/v1/audio-isolation", files={"audio": (filename or "audio", audio)})
    _count("isolate", seconds)
    return r.content


def sfx(text: str, seconds: float = 0.0, loop: bool = False, influence: float = 0.3) -> bytes:
    body: dict[str, Any] = {"text": text, "loop": bool(loop), "prompt_influence": influence, "model_id": "eleven_text_to_sound_v3"}
    if seconds:
        body["duration_seconds"] = max(0.5, min(30.0, float(seconds)))
    r = _call("POST", "/v1/sound-generation", params={"output_format": "mp3_44100_128"}, json=body)
    _count("sfx", seconds or 5.0)
    return r.content


# ---------------------------------------------------------------- dubbing in the speakers' own voices
def dub_start(video: bytes, filename: str, source_lang: str = "") -> dict:
    data = {"model_id": "dubbing_v2"}
    if source_lang:
        data["source_language"] = source_lang
    return _call("POST", "/v1/dubbing/project", files={"file": (filename or "video.mp4", video)}, data=data).json()


def dub_add_language(project_id: str, lang: str) -> dict:
    return _call("POST", f"/v1/dubbing/project/{project_id}/language", json={"target_language": lang}).json()


def dub_project(project_id: str) -> dict:
    return _call("GET", f"/v1/dubbing/project/{project_id}").json()


def dub_language(project_id: str, language_id: str) -> dict:
    return _call("GET", f"/v1/dubbing/project/{project_id}/language/{language_id}").json()


def fetch(url: str) -> bytes:
    """A signed output URL from ElevenLabs (no key sent: the URL carries its own signature)."""
    r = _http("GET", url)
    if r.status_code >= 400:
        raise ElevenError("The dubbed sound could not be downloaded; it will be read again.")
    return r.content
