"""v0.457 HOOLA INTERACTIVE Phase 0: the Hoola server's one door to the Model Lab (docs/INTERACTIVE_AVATAR_PLAN.md).

The GPU lab (avatar_engine/modal_app.py) makes faces and voices. This module is the ONLY way Hoola talks to it:

    lab.voice("नमस्ते", lang="hi")            -> wav bytes
    lab.face_prepare(avatar_id, mp4, consent)  -> the face is ready
    lab.face_speak(avatar_id, wav)             -> mp4 bytes
    lab.face_forget(avatar_id)                 -> gone

Rules kept here, not in the GPU app, so they hold even if the lab is replaced:
  * the address + key live in the VPS .env only (AVATAR_ENGINE_URL / AVATAR_ENGINE_KEY); no key ever reaches the model,
    the chat or a log line;
  * a face is prepared only with a consent tag - 'ai_generated', or 'signed:<record id>' for a real person who recorded
    a consent clip; anything else is refused before a byte is uploaded;
  * sizes are capped and the lab is treated as slow: every call has a timeout and returns a plain Hoola error;
  * nothing is cached here: audio and video pass through.
"""
from __future__ import annotations

import base64
import logging
import re
from typing import Any

import httpx

from ..config import get_settings

log = logging.getLogger("santosh.interactive")

AVATAR_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")
CONSENT = re.compile(r"^(ai_generated|signed:[A-Za-z0-9_-]{4,64})$")
MAX_TEXT = 600
MAX_REF_AUDIO = 2 * 1024 * 1024
MAX_FACE_VIDEO = 30 * 1024 * 1024
MAX_SPEAK_AUDIO = 8 * 1024 * 1024
VOICE_MODELS = ("chatterbox", "indicf5", "indic_parler")


class LabError(Exception):
    """Something the owner should read: the lab is off, locked, slow, or refused the ask."""


def configured() -> bool:
    s = get_settings()
    return bool(getattr(s, "avatar_engine_url", "") and getattr(s, "avatar_engine_key", ""))


def _call(path: str, body: dict[str, Any] | None = None, *, method: str = "POST", timeout: float = 300.0) -> httpx.Response:
    s = get_settings()
    url, key = getattr(s, "avatar_engine_url", ""), getattr(s, "avatar_engine_key", "")
    if not url or not key:
        raise LabError("Interactive engine is not set up yet (AVATAR_ENGINE_URL / AVATAR_ENGINE_KEY on the server).")
    try:
        r = httpx.request(method, url.rstrip("/") + path, json=body, timeout=timeout,
                          headers={"Authorization": f"Bearer {key}"})
    except httpx.TimeoutException:
        raise LabError("The engine did not answer in time.") from None
    except httpx.HTTPError as e:
        raise LabError(f"Could not reach the engine: {type(e).__name__}") from None
    if r.status_code == 401:
        raise LabError("The engine refused our key.")
    if r.status_code >= 400:
        detail = ""
        try:
            detail = str(r.json().get("detail", ""))[:300]
        except Exception:
            detail = r.text[:300]
        raise LabError(f"The engine refused: {detail or r.status_code}")
    return r


def health() -> dict:
    """What the lab has: its GPU and every model row with its licence verdict."""
    return _call("/health", method="GET", timeout=60.0).json()


def voice(text: str, *, lang: str = "hi", model: str = "chatterbox", ref_audio: bytes | None = None,
          ref_text: str = "", description: str = "") -> bytes:
    """Speak `text` and return WAV bytes. `ref_audio` clones that voice - only ever the user's own, recorded live."""
    text = (text or "").strip()
    if not text:
        raise LabError("Nothing to say.")
    if len(text) > MAX_TEXT:
        raise LabError(f"Too long for one go ({len(text)} characters; limit {MAX_TEXT}).")
    if model not in VOICE_MODELS:
        raise LabError(f"Unknown voice model '{model}'.")
    if ref_audio and len(ref_audio) > MAX_REF_AUDIO:
        raise LabError("The voice sample is over 2 MB.")
    body: dict[str, Any] = {"text": text, "lang": lang, "model": model}
    if ref_audio:
        body["ref_audio_b64"] = base64.b64encode(ref_audio).decode()
        body["ref_text"] = ref_text
    if description:
        body["description"] = description
    return _call("/voice", body).content


def face_prepare(avatar_id: str, video: bytes, consent: str) -> dict:
    """Make a face ready. consent: 'ai_generated', or 'signed:<record id>' of a real person's consent clip."""
    if not AVATAR_ID.match(avatar_id or ""):
        raise LabError("The face's name may use small letters, numbers, - and _ (up to 40).")
    if not CONSENT.match(consent or ""):
        raise LabError("A face needs consent: an AI-made person, or a real person's signed consent record.")
    if not video:
        raise LabError("No reference video.")
    if len(video) > MAX_FACE_VIDEO:
        raise LabError("The reference video is over 30 MB.")
    out = _call("/face/prepare", {"avatar_id": avatar_id, "consent": consent,
                                  "video_b64": base64.b64encode(video).decode()}, timeout=1800.0).json()
    log.info("interactive: face %s prepared in %ss", avatar_id, out.get("prepare_s"))
    return out


def face_speak(avatar_id: str, audio: bytes) -> bytes:
    """The prepared face says this audio; returns MP4 bytes."""
    if not AVATAR_ID.match(avatar_id or ""):
        raise LabError("Unknown face.")
    if not audio:
        raise LabError("No audio to speak.")
    if len(audio) > MAX_SPEAK_AUDIO:
        raise LabError("That audio is over 8 MB; send it in parts.")
    return _call("/face/speak", {"avatar_id": avatar_id, "audio_b64": base64.b64encode(audio).decode()},
                 timeout=900.0).content


def face_forget(avatar_id: str) -> dict:
    """Delete a prepared face and its source video from the lab."""
    if not AVATAR_ID.match(avatar_id or ""):
        raise LabError("Unknown face.")
    return _call("/face/forget", {"avatar_id": avatar_id}, timeout=120.0).json()


# ---------------------------------------------------------------- v0.462.x live talk: a 2-minute ticket, never the key
def make_ticket(avatar_id: str, ttl: int = 120) -> str:
    """A signed pass for ONE live talk with ONE avatar: '<expires>.<avatar>.<hmac>'. The browser never sees the engine key;
    the engine checks the signature with its own copy of the key (avatar_engine/modal_app.py `_ticket_ok`, same maths)."""
    import hashlib
    import hmac
    import time
    s = get_settings()
    key = getattr(s, "avatar_engine_key", "")
    if not key:
        raise LabError("Interactive engine key is not on the server yet (run vps-ops > engine_attach).")
    if not AVATAR_ID.match(avatar_id or ""):
        raise LabError("avatar id: lowercase letters, digits, - or _ (1-40 characters)")
    exp = int(time.time()) + max(10, min(int(ttl), 300))
    sig = hmac.new(key.encode(), f"live|{exp}|{avatar_id}".encode(), hashlib.sha256).hexdigest()
    return f"{exp}.{avatar_id}.{sig}"


def live_address() -> str:
    """The engine's address as a websocket base (wss://...), for the browser. Not secret."""
    url = (getattr(get_settings(), "avatar_engine_url", "") or "").rstrip("/")
    if not url:
        raise LabError("Interactive engine address is not on the server yet (run vps-ops > engine_attach).")
    return re.sub(r"^http", "ws", url)
