"""v0.999.90 HOOLA VOCAL GLOBAL - Google's Gemini voice engine (gemini-3.8-flash-tts) beyond the 30 prebuilt voices.

Request shapes are from Google's own pages, read 21 Nov 2026:
- aistudio.google.com/docs/voice-design: POST v1beta/voices, type "prompted", prompted.input = the description.
- .../voice-replication: type "replicated", replicated.source_audio + consent_audio, inline base64. The consent recording
  must recite Google's exact statement (consent.py); both recordings must be real speech by the same adult.
- .../voice-remixing: type "prompted" with prompted.base_voice.
- .../speech-generation: POST v1beta/interactions. Custom voices are spoken here; prebuilt voices keep using
  create.service (generateContent, the path already proven live).

NOT VERIFIED: no call has been made from here. The exact response field names for replicated voices are read from the
page's prose, so `_voice_id` accepts every shape the page describes. Paid Tier 1+ is needed for replication and
remixing: a refusal is passed on in plain words.
"""
from __future__ import annotations

import base64
import logging
import re
from typing import Any

log = logging.getLogger("santosh.vocal.gemini")
BASE = "https://generativelanguage.googleapis.com/v1beta"
TOKENS_PER_S = 25          # audio tokens per second of speech (Google states 25/s for audio; used only for the estimate)

# Feelings she writes in square brackets -> Gemini's own forms. Point events become angle-bracket tags; a feeling at
# the start of a part becomes that part's delivery style. Nothing in brackets is ever spoken.
POINT = {"laughs": "<laugh>", "laugh": "<laugh>", "sighs": "<sigh>", "sigh": "<sigh>", "pause": "<short pause>",
         "long pause": "<long pause>", "gasps": "<gasp>", "gasp": "<gasp>", "coughs": "<cough>", "breath": "<breath>",
         "breathes": "<breath>"}
STYLE = {"warm": "warm and kind", "whispers": "whispering", "whisper": "whispering", "excited": "excited and energetic",
         "serious": "serious and steady", "slowly": "speaking slowly", "cheerful": "cheerful, smiling", "calm": "calm",
         "sad": "sad and quiet", "angry": "angry", "sarcastic": "sarcastic", "shouting": "loud, almost shouting"}


class GeminiVoiceError(Exception):
    pass


def _key() -> str:
    from ..config import get_settings
    k = getattr(get_settings(), "gemini_api_key", "") or ""
    if not k:
        raise GeminiVoiceError("The Gemini voice engine is not connected on this server yet.")
    return k


def model() -> str:
    from ..config import get_settings
    return getattr(get_settings(), "voice_ack_tts_model", "") or "gemini-3.8-flash-tts"


def _http(method: str, url: str, **kw):          # the one network seam (tests replace it)
    import httpx
    return httpx.request(method, url, timeout=kw.pop("timeout", 120), **kw)


def _call(method: str, path: str, body: dict | None = None, params: dict | None = None) -> dict:
    r = _http(method, BASE + path, headers={"x-goog-api-key": _key(), "content-type": "application/json"},
              json=body, params=params)
    if r.status_code >= 400:
        try:
            msg = (r.json().get("error") or {}).get("message") or r.text
        except Exception:   # noqa: BLE001
            msg = r.text
        msg = re.sub(r"\s+", " ", str(msg))[:200]
        if r.status_code in (401, 403):
            raise GeminiVoiceError(f"Google refused the voice request ({msg}). Voice design, cloning and remixing need a paid Gemini API project.")
        raise GeminiVoiceError(f"The voice engine said: {msg}")
    return r.json() if r.content else {}


# ---------------------------------------------------------------- feelings
def feelings(text: str) -> tuple[str, str]:
    """[laughs] -> <laugh> etc.; leading [warm] [whispers] ... -> a style. Returns (text for the engine, style)."""
    styles: list[str] = []
    t = text.strip()
    while True:
        m = re.match(r"^\[([a-z ]{2,20})\]\s*", t, re.I)
        if not m:
            break
        k = m.group(1).lower().strip()
        if k in STYLE:
            styles.append(STYLE[k])
        elif k in POINT:
            break
        t = t[m.end():]

    def point(m: re.Match) -> str:
        k = m.group(1).lower().strip()
        if k in POINT:
            return POINT[k]
        if k in STYLE:
            later.append(STYLE[k])
            return ""                          # a mood word mid-text: not spoken, not a sound - a style for the part
        return m.group(0)
    later: list[str] = []
    t = re.sub(r"\[([a-z ]{2,20})\]", point, t, flags=re.I)
    styles += [f"then {x}" for x in later]
    return re.sub(r"[ \t]{2,}", " ", t).strip(), ", ".join(dict.fromkeys(styles))


def strip_feelings(text: str) -> str:
    """The words alone, for titles and history (no [warm] or <laugh>)."""
    return re.sub(r"\s{2,}", " ", re.sub(r"\[[a-z ]{2,20}\]|<[a-z ]{3,12}>", "", text, flags=re.I)).strip()


# ---------------------------------------------------------------- speaking in a custom voice (Interactions API)
def speak_custom(text: str, voice_id: str, style: str = "") -> bytes:
    """A designed / cloned / remixed voice (voice_... or voicekey_...) reads `text`. Returns a WAV (24 kHz mono)."""
    content: dict[str, Any] = {"type": "text", "text": text}
    if style:
        content["annotations"] = [{"type": "speech_metadata", "style": style}]
    body = {"model": model(), "input": [{"type": "user_input", "content": [content]}],
            "response_format": {"type": "audio", "mime_type": "audio/wav"},
            "generation_config": {"speech_config": [{"voice": voice_id}]}}
    r = _call("POST", "/interactions", body)
    b64 = ((r.get("output_audio") or {}).get("data")
           or next((c.get("data") for st in r.get("steps") or [] for c in st.get("content") or [] if c.get("data")), ""))
    if not b64:
        raise GeminiVoiceError("The voice engine answered with no sound.")
    data = base64.b64decode(b64)
    _count(len(data))
    return data


def _count(wav_bytes: int) -> None:
    try:
        from .. import usage
        seconds = max(0.0, (wav_bytes - 44) / 48000)
        usage.record(model(), audio_out=int(seconds * TOKENS_PER_S), feature="create")
    except Exception:   # noqa: BLE001
        pass


# ---------------------------------------------------------------- making voices
def _voice_id(r: dict) -> tuple[str, str]:
    """(id, expire_time) from any shape the pages describe: id, voice.id, replicated_voice.id / .key."""
    for holder in (r, r.get("voice") or {}, r.get("replicated_voice") or {}):
        vid = holder.get("id") or holder.get("key") or holder.get("name")
        if vid:
            return str(vid).split("/")[-1], str(holder.get("expire_time") or "")
    raise GeminiVoiceError("The voice engine made no voice.")


def _sample(r: dict) -> bytes:
    s = r.get("sample_audio") or (r.get("voice") or {}).get("sample_audio") or {}
    return base64.b64decode(s["data"]) if s.get("data") else b""


def design(description: str, name: str, gender: str = "", lang_code: str = "") -> dict:
    """A new voice from words. Returns {id, sample (wav bytes)}."""
    v: dict[str, Any] = {"model": model(), "type": "prompted", "display_name": name[:60], "prompted": {"input": description}}
    if gender in ("female", "male"):
        v["gender"] = gender
    if lang_code:
        v["language_code"] = lang_code
    r = _call("POST", "/voices", {"store": True, "voice": v})
    vid, _ = _voice_id(r)
    return {"id": vid, "sample": _sample(r)}


def replicate(name: str, source_wav: bytes, consent_wav: bytes) -> dict:
    """Her voice from her recording + her spoken consent (both 24 kHz mono WAV). Returns {id, expire}."""
    v = {"model": model(), "type": "replicated", "display_name": name[:60],
         "replicated": {"source_audio": {"mime_type": "audio/wav", "data": base64.b64encode(source_wav).decode()},
                        "consent_audio": {"mime_type": "audio/wav", "data": base64.b64encode(consent_wav).decode()}}}
    r = _call("POST", "/voices", {"store": True, "voice": v})
    vid, exp = _voice_id(r)
    return {"id": vid, "expire": exp}


def remix(base_voice: str, change: str, name: str) -> dict:
    r = _call("POST", "/voices", {"store": True, "voice": {"model": model(), "type": "prompted", "display_name": name[:60],
                                                           "prompted": {"base_voice": base_voice, "input": change}}})
    vid, _ = _voice_id(r)
    return {"id": vid, "sample": _sample(r)}


def delete(voice_id: str) -> None:
    try:
        _call("DELETE", f"/voices/{voice_id}")
    except GeminiVoiceError as e:
        log.warning("gemini voice delete %s: %s", voice_id, e)


def catalog(page_size: int = 500) -> list[dict]:
    """Google's catalog voices (prebuilt + the Extended Voice Library). [] when the list cannot be read."""
    try:
        r = _call("GET", "/voices", params={"page_size": page_size, "type": "prebuilt"})
    except GeminiVoiceError as e:
        log.info("gemini voice catalog not read: %s", e)
        return []
    out = []
    for v in r.get("voices") or []:
        vid = str(v.get("id") or v.get("name") or "").split("/")[-1]
        if vid:
            out.append({"id": vid, "name": v.get("display_name") or vid, "gender": (v.get("gender") or "").lower(),
                        "lang": v.get("language_code") or "", "accent": v.get("accent") or "", "pitch": v.get("pitch") or "",
                        "description": v.get("description") or ""})
    return out


# ---------------------------------------------------------------- two speakers in one take (multi-speaker speech)
def _multi_call(contents: str, speakers: dict[str, str]) -> bytes:      # the seam (tests replace it)
    """Google's multi-speaker speech: speech_config.multi_speaker_voice_config with exactly two speakers. PCM 24 kHz."""
    from google.genai import Client, types
    cfg = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
            speaker_voice_configs=[types.SpeakerVoiceConfig(speaker=name, voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice))) for name, voice in speakers.items()])))
    resp = Client(api_key=_key()).models.generate_content(model=model(), config=cfg, contents=contents)
    pcm = next((p.inline_data.data for p in resp.candidates[0].content.parts if getattr(p, "inline_data", None)), b"")
    if not pcm:
        raise GeminiVoiceError("The voice engine answered with no sound.")
    return pcm


def speak_two(lines: list[tuple[str, str]], voices: dict[str, str], language: str = "", style: str = "") -> bytes:
    """A conversation between exactly two speakers, read in one take. `voices` = speaker -> prebuilt voice name.
    Feelings become instructions in the header (never read aloud). Returns a WAV (24 kHz mono)."""
    if len(voices) != 2:
        raise GeminiVoiceError("A natural take on the Gemini engine is for exactly two speakers.")
    notes, body = [], []
    for i, (who, text) in enumerate(lines, 1):
        spoken, mood = feelings(text)
        if mood:
            notes.append(f"line {i} ({who}): {mood}")
        body.append(f"{who}: {spoken}")
    head = f"Read this conversation between {' and '.join(voices)} naturally" + (f" in {language}" if language else "")
    head += (f", {style}" if style else "") + "."
    if notes:
        head += " Delivery: " + "; ".join(notes) + "."
    pcm = _multi_call(head + "\n" + "\n".join(body), voices)
    import io
    import wave
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)
    data = b.getvalue()
    _count(len(data))
    return data
