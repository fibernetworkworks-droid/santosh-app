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
    status = 0          # the HTTP status ElevenLabs answered with (0 = not an HTTP refusal)


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
        raise ElevenError("Premium voices need an ElevenLabs key on the server, which is not connected yet.")
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
            err = ElevenError("ElevenLabs refused the key on the server. The server owner must check it.")
        elif r.status_code in (402, 429):
            err = ElevenError(f"ElevenLabs says the account is out of credit or busy ({msg}).")
        else:
            err = ElevenError(f"ElevenLabs said: {msg}")
        err.status = r.status_code
        raise err
    return r


def _count(kind: str, seconds: float, tenant: str | None = None) -> None:
    try:
        from .. import usage
        usage.record(f"elevenlabs-{kind}", sec_out=max(seconds, 1.0), feature="create", tenant=tenant)
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


def _stream(method: str, url: str, **kw):       # the streaming network seam (tests replace it): yields byte chunks
    import httpx
    with httpx.stream(method, url, timeout=kw.pop("timeout", 180), **kw) as r:
        if r.status_code >= 400:
            r.read()
            yield r
            return
        yield r


def tts_stream(text: str, voice_id: str, model_id: str = "eleven_v4", lang: str = "", stability: float = 0.5,
               similarity: float = 0.75, style: float = 0.0, speed: float = 1.0):
    """POST /v1/text-to-speech/{voice_id}/stream (mp3_44100_128, chunked): yields mp3 chunks as ElevenLabs makes them."""
    if not ready():
        raise ElevenError("Premium voices need an ElevenLabs key on the server, which is not connected yet.")
    body: dict[str, Any] = {"text": text, "model_id": model_id,
                            "voice_settings": {"stability": stability, "similarity_boost": similarity, "style": style,
                                               "use_speaker_boost": True, "speed": speed}}
    if lang and "-" not in lang and len(lang) == 2 and model_id != "eleven_multilingual_v2":
        body["language_code"] = lang
    gen = _stream("POST", f"{BASE}/v1/text-to-speech/{voice_id}/stream", params={"output_format": "mp3_44100_128"},
                  json=body, headers={"xi-api-key": key()})
    try:
        r = next(gen)
    except StopIteration:
        raise ElevenError("ElevenLabs sent nothing back.") from None
    if r.status_code >= 400:
        gen.close()
        err = ElevenError("ElevenLabs refused the key on the server. The server owner must check it." if r.status_code == 401
                          else f"ElevenLabs could not read it aloud ({r.status_code}).")
        err.status = r.status_code
        raise err
    try:
        for chunk in r.iter_bytes():
            if chunk:
                yield chunk
    finally:
        gen.close()


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
def change(audio: bytes, filename: str, voice_id: str, denoise: bool = True, settings: dict | None = None) -> bytes:
    """Her recording spoken again in another voice. `settings` = voice_settings for this one request (sent as a JSON
    string, as the API asks): stability (0-1, lower = more of her ups and downs) and similarity_boost (0-1, how close
    to the voice)."""
    data = {"model_id": "eleven_multilingual_sts_v2", "remove_background_noise": "true" if denoise else "false"}
    if settings:
        import json
        data["voice_settings"] = json.dumps({k: float(v) for k, v in settings.items()})
    r = _call("POST", f"/v1/voice-changer/{voice_id}", params={"output_format": "pcm_24000"},
              files={"audio": (filename or "audio", audio)}, data=data)
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


def dub_segments(project_id: str, language_id: str) -> dict:
    """One dubbed language's lines: GET /v1/dubbing/project/{id}/language/{lid}/transcript -> {revision, segments:[{id,
    speaker_id, start_s, end_s, source_text, translation}]}. Refused while the first dub is still running."""
    return _call("GET", f"/v1/dubbing/project/{project_id}/language/{language_id}/transcript").json()


def dub_segment_set(project_id: str, language_id: str, segment_id: str, translation: str) -> dict:
    """Her words for one line (PATCH .../transcript/segment/{sid} {translation}). The sound changes only after
    dub_regenerate. Enterprise accounts only (ElevenLabs' rule)."""
    return _call("PATCH", f"/v1/dubbing/project/{project_id}/language/{language_id}/transcript/segment/{segment_id}",
                 json={"translation": translation}).json()


def dub_regenerate(project_id: str, language_id: str) -> dict:
    """Make the edited parts of one language again (POST .../transcript/regenerate, 202): regenerated_segment_ids,
    regenerated_seconds, charged_seconds. GET dub_language follows it to status completed."""
    r = _call("POST", f"/v1/dubbing/project/{project_id}/language/{language_id}/transcript/regenerate")
    try:
        return r.json() or {}
    except Exception:   # noqa: BLE001
        return {}


def dub_transcript(project_id: str, lang: str, fmt: str = "srt") -> str:
    """The subtitles ElevenLabs made for one dubbed language (format_type srt | webvtt).
    NOT VERIFIED: the path is the dubbing API's transcript route; a refusal is passed on and the page says it."""
    r = _call("GET", f"/v1/dubbing/{project_id}/transcript/{lang}",
              params={"format_type": "webvtt" if fmt == "vtt" else "srt"})
    try:
        d = r.json()
        if isinstance(d, dict):
            return str(d.get("srt") or d.get("webvtt") or d.get("transcript") or d.get("content") or "")
    except Exception:   # noqa: BLE001
        pass
    return r.text


# ---------------------------------------------------------------- the shared voice library
SHARED_SORTS = {"trending": "trending", "popular": "usage_character_count_1y", "newest": "created_date",
                "most_added": "cloned_by_count", "usage_character_count_1y": "usage_character_count_1y",
                "created_date": "created_date", "cloned_by_count": "cloned_by_count"}


# her plain words -> ElevenLabs' use_case values
SHARED_USES = {"ads": "advertisement", "ad": "advertisement", "advertisement": "advertisement",
               "narration": "narrative_story", "stories": "narrative_story", "story": "narrative_story",
               "audiobooks": "narrative_story", "news": "informative_educational", "learning": "informative_educational",
               "education": "informative_educational", "explainers": "informative_educational",
               "support": "conversational", "conversation": "conversational", "podcasts": "conversational",
               "social": "social_media", "reels": "social_media", "characters": "characters_animation",
               "games": "characters_animation", "tv": "entertainment_tv"}


def shared_voices(q: str = "", lang: str = "", gender: str = "", age: str = "", accent: str = "", use: str = "",
                  sort: str = "", page: int = 0, page_size: int = 30) -> dict:
    """One page of ElevenLabs' public voice library (GET /v1/shared-voices). Returns {voices: [...], more}."""
    params: dict[str, Any] = {"page_size": max(1, min(int(page_size or 30), 100)), "page": max(0, int(page or 0))}
    for k, v in (("search", q), ("language", lang), ("gender", gender), ("age", age), ("accent", accent),
                 ("use_cases", SHARED_USES.get(str(use).strip().lower(), use))):
        if v:
            params[k] = v
    if sort in SHARED_SORTS:
        params["sort"] = SHARED_SORTS[sort]
    d = _call("GET", "/v1/shared-voices", params=params).json()
    out = []
    for v in d.get("voices") or []:
        vid, owner = v.get("voice_id"), v.get("public_owner_id")
        if not vid or not owner:
            continue
        langs = [str(x.get("language") or "").split("-")[0] for x in v.get("verified_languages") or [] if x.get("language")]
        if v.get("language"):
            langs.insert(0, str(v["language"]).split("-")[0])
        out.append({"id": vid, "owner": owner, "name": v.get("name") or "Voice",
                    "line": (v.get("description") or v.get("descriptive") or "")[:200],
                    "langs": list(dict.fromkeys(x for x in langs if x)), "gender": (v.get("gender") or "").lower(),
                    "age": (v.get("age") or "").replace("_", " ").lower(), "accent": v.get("accent") or "",
                    "use": (v.get("use_case") or "").replace("_", " "),
                    "uses": int(v.get("cloned_by_count") or v.get("usage_character_count_1y") or 0),
                    "preview_url": v.get("preview_url") or ""})
    return {"voices": out, "more": bool(d.get("has_more"))}


def add_shared(owner: str, voice_id: str, name: str) -> str:
    """Adds a public library voice to the account (POST /v1/voices/add/{public_user_id}/{voice_id}). Returns the new id."""
    d = _call("POST", f"/v1/voices/add/{owner}/{voice_id}", json={"new_name": name[:60]}).json()
    vid = d.get("voice_id") or d.get("id")
    if not vid:
        raise ElevenError("ElevenLabs added no voice.")
    return str(vid)


def delete_voice(voice_id: str) -> None:
    try:
        _call("DELETE", f"/v1/voices/{voice_id}")
    except ElevenError as e:
        log.warning("elevenlabs voice delete %s: %s", voice_id, e)


def preview_ok(url: str) -> bool:
    """Only ElevenLabs' own storage: https on *.elevenlabs.io, or Google storage under an eleven- bucket."""
    from urllib.parse import urlparse
    try:
        u = urlparse(url)
    except ValueError:
        return False
    host = (u.hostname or "").lower()
    if u.scheme != "https" or u.username or u.password or u.port not in (None, 443):
        return False
    return host == "elevenlabs.io" or host.endswith(".elevenlabs.io") or \
        (host == "storage.googleapis.com" and u.path.startswith("/eleven-"))


def fetch_preview(url: str, limit: int = 6 * 1024 * 1024) -> bytes:
    if not preview_ok(url):
        raise ElevenError("Only ElevenLabs voice previews can be played here.")
    r = _http("GET", url, timeout=30, follow_redirects=False)
    if r.status_code >= 400 or not r.content:
        raise ElevenError("That preview could not be read.")
    if len(r.content) > limit:
        raise ElevenError("That preview is too large.")
    return r.content


# ---------------------------------------------------------------- a natural dialogue in one take
def dialogue(inputs: list[dict], model_id: str = "eleven_v3") -> bytes:
    """Several voices in one take (POST /v1/text-to-dialogue, eleven_v3). inputs = [{text, voice_id}]. Returns a WAV."""
    r = _call("POST", "/v1/text-to-dialogue", params={"output_format": "pcm_24000"},
              json={"inputs": [{"text": x["text"], "voice_id": x["voice_id"]} for x in inputs], "model_id": model_id})
    _count("tts", len(r.content) / 48000)
    return pcm_to_wav(r.content)


def fetch(url: str) -> bytes:
    """A signed output URL from ElevenLabs (no key sent: the URL carries its own signature). A signed storage link may
    answer with a redirect first, so redirects are followed (v0.999.167)."""
    r = _http("GET", url, follow_redirects=True)
    if r.status_code >= 400:
        raise ElevenError("The dubbed sound could not be downloaded; it will be read again.")
    return r.content
